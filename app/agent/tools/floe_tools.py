import os
from decimal import Decimal
from typing import Optional
from langchain_core.tools import tool
from app.services.floe_client import FloeClient
from app.agent.budget_engine import BudgetEngine, CreditState
import structlog

log = structlog.get_logger()
budget = BudgetEngine()

# Global state for Floe client and wallet provider
_floe_client: Optional[FloeClient] = None
_current_loan_id: Optional[str] = None


def set_floe_wallet(wallet_provider):
    """
    Initialize Floe client with a wallet provider.
    Call this before running the agent to enable on-chain operations.
    """
    global _floe_client
    _floe_client = FloeClient(wallet_provider=wallet_provider)
    log.info("floe_wallet_set", wallet_type=type(wallet_provider).__name__)


def get_floe() -> FloeClient:
    """Get or create the Floe client."""
    global _floe_client
    if _floe_client is None:
        # Fallback: create without wallet provider (will fail at borrow/repay time)
        _floe_client = FloeClient(wallet_provider=None)
        log.warning("floe_client_created_without_wallet_provider")
    return _floe_client


def set_current_loan(loan_id: str):
    """Track the current active loan for repayment."""
    global _current_loan_id
    _current_loan_id = loan_id
    log.info("loan_tracked", loan_id=loan_id)


@tool
async def check_credit_status(loan_id: str = None) -> dict:
    """Check current Floe credit/loan status on-chain. Provide the loan_id to check.

    Returns: remaining credit, limit, loan status, health indicator.
    """
    try:
        if not loan_id:
            loan_id = _current_loan_id or "default"

        floe = get_floe()
        state = await floe.get_credit_status(loan_id=loan_id)

        log.info("credit_checked", remaining=state.get("credit_remaining"), loan_id=loan_id)
        return {
            "remaining_usdc": float(state.get("credit_remaining", 0)),
            "limit_usdc": float(state.get("credit_limit", 0)),
            "active_loan_id": state.get("active_loan_id"),
            "is_healthy": float(state.get("credit_remaining", 0)) > float(os.getenv("CREDIT_MIN_RESERVE_USDC", "5")),
        }
    except Exception as e:
        log.error("credit_check_failed", error=str(e))
        return {"error": str(e), "remaining_usdc": 0, "is_healthy": False}


@tool
async def estimate_x402_cost(endpoint_url: str) -> dict:
    """
    Estimate the USDC cost for an x402 API call.

    Args:
        endpoint_url: Full URL of the x402 endpoint to call

    Returns: Estimated cost in USDC
    """
    try:
        # For now, return a mock estimate
        # In production, this would call Floe's cost estimation
        # Real implementation: floe.estimate_costs([endpoint_url])

        log.info("cost_estimated", endpoint=endpoint_url)
        return {
            "endpoint": endpoint_url,
            "estimated_usdc": 0.05,  # Mock: 5 cents per API call
            "currency": "USDC",
        }
    except Exception as e:
        log.error("cost_estimation_failed", error=str(e))
        return {"estimated_usdc": 0.10, "error": str(e)}


@tool
async def post_borrow_intent(borrow_amount_usdc: float, collateral_amount_usdc: float = None, max_apr_bps: int = 1200) -> dict:
    """
    Borrow USDC from Floe against on-chain collateral.
    This is an on-chain transaction executed by the agent's wallet.

    Args:
        borrow_amount_usdc: Amount to borrow (e.g., 100.50)
        collateral_amount_usdc: Amount of collateral to lock (e.g., 110.55)
        max_apr_bps: Maximum acceptable interest rate in basis points (default 1200 = 12%)

    Returns: Loan details with loan_id for future repayment
    """
    try:
        floe = get_floe()

        # Use budget engine to validate the borrow
        credit = CreditState(
            remaining_usdc=Decimal("0"),
            limit_usdc=Decimal(str(borrow_amount_usdc)),
            active_loan_id=None,
            current_apr=Decimal(str(max_apr_bps / 10000)),
        )
        decision = budget.evaluate_borrow(
            credit=credit,
            estimated_cost=Decimal(str(borrow_amount_usdc)),
            offered_apr=Decimal(str(max_apr_bps / 10000)),
        )

        if not decision.should_borrow:
            log.info("borrow_rejected", reason=decision.reason)
            return {"success": False, "reason": decision.reason}

        # Use collateral amount or default to 110% of borrow
        if collateral_amount_usdc is None:
            collateral_amount_usdc = borrow_amount_usdc * 1.10

        result = await floe.instant_borrow(
            borrow_amount=decision.amount_usdc,
            collateral_amount=collateral_amount_usdc,
            max_interest_rate_bps=max_apr_bps,
            duration_seconds=7 * 24 * 3600,  # 7 days
        )

        loan_id = result.get("loan_id", "unknown")
        set_current_loan(loan_id)

        log.info(
            "borrowed",
            loan_id=loan_id,
            amount_usdc=decision.amount_usdc,
            collateral=collateral_amount_usdc,
        )

        return {
            "success": True,
            "loan_id": loan_id,
            "amount_usdc": float(decision.amount_usdc),
            "collateral_usdc": collateral_amount_usdc,
            "apr_bps": max_apr_bps,
            "reason": decision.reason,
        }
    except Exception as e:
        log.error("borrow_failed", error=str(e))
        return {"success": False, "error": str(e)}


@tool
async def repay_credit(loan_id: str = None, repay_amount_usdc: float = None) -> dict:
    """
    Repay a Floe loan (fully or partially).
    This is an on-chain transaction executed by the agent's wallet.
    Collateral is returned atomically in the same transaction.

    Args:
        loan_id: The loan ID to repay (uses tracked loan if not provided)
        repay_amount_usdc: Amount to repay (full repayment if not specified)

    Returns: Repayment confirmation
    """
    try:
        if not loan_id:
            loan_id = _current_loan_id

        if not loan_id:
            return {"success": False, "error": "No active loan to repay"}

        floe = get_floe()
        result = await floe.repay_loan(loan_id=loan_id, repay_amount_usdc=repay_amount_usdc)

        log.info("repaid", loan_id=loan_id, amount=repay_amount_usdc)

        return {
            "success": True,
            "loan_id": loan_id,
            "repaid_usdc": repay_amount_usdc or "full",
            "result": result,
        }
    except Exception as e:
        log.error("repay_failed", loan_id=loan_id, error=str(e))
        return {"success": False, "error": str(e)}
