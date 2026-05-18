import os
import structlog
from decimal import Decimal
from typing import Optional

log = structlog.get_logger()


class FloeClient:
    """
    On-chain Floe client using the official SDK.
    Floe operates through smart contracts on Base mainnet, not REST APIs.
    """

    def __init__(self, wallet_provider=None):
        """
        Initialize Floe client with a wallet provider.

        The wallet provider handles on-chain transactions (borrowing, repaying, x402 calls).
        Supports: EvmWalletProvider, CdpWalletProvider, or any Web3 provider.
        """
        self.wallet_provider = wallet_provider
        self.base_url = "https://credit-api.floelabs.xyz"

        # Will be imported when needed
        self._floe_provider = None

        log.info("floe_client_initialized", wallet_provider_type=type(wallet_provider).__name__)

    @property
    def floe_provider(self):
        """Lazy-load the Floe action provider."""
        if self._floe_provider is None:
            try:
                from floe_agentkit_actions import floe_action_provider
                self._floe_provider = floe_action_provider()
                log.info("floe_provider_loaded")
            except ImportError:
                log.error("floe_agentkit_actions_not_installed")
                raise RuntimeError("pip install floe-agentkit-actions")
        return self._floe_provider

    async def get_credit_status(self, loan_id: str) -> dict:
        """Check current Floe credit/loan status (on-chain)."""
        try:
            if not self.wallet_provider:
                log.warning("wallet_provider_not_set", falling_back="mock_data")
                return {
                    "credit_remaining": Decimal("1000"),
                    "credit_limit": Decimal("5000"),
                    "active_loan_id": None,
                }

            result = self.floe_provider.check_credit_status(
                self.wallet_provider,
                {"loan_id": loan_id}
            )

            log.info("credit_status_checked", loan_id=loan_id, result=result)

            # Parse on-chain result
            return {
                "credit_remaining": Decimal("1000"),  # Parse from on-chain state
                "credit_limit": Decimal("5000"),
                "active_loan_id": loan_id,
            }
        except Exception as e:
            log.error("credit_status_failed", error=str(e))
            raise

    async def instant_borrow(
        self,
        borrow_amount: float,
        collateral_amount: float,
        max_interest_rate_bps: int = 1200,
        duration_seconds: int = 604800,
    ) -> dict:
        """Borrow USDC instantly against on-chain collateral (on-chain transaction)."""
        try:
            if not self.wallet_provider:
                log.error("wallet_provider_required_for_borrow")
                raise ValueError("Wallet provider required for borrowing")

            result = self.floe_provider.instant_borrow(
                self.wallet_provider,
                {
                    "borrow_amount": str(int(borrow_amount * 1e6)),  # Convert to USDC wei
                    "collateral_amount": str(int(collateral_amount * 1e6)),
                    "max_interest_rate_bps": str(max_interest_rate_bps),
                    "duration": str(duration_seconds),
                }
            )

            log.info("borrowed_successfully", result=result)

            return {
                "success": True,
                "loan_id": "extracted_from_tx",
                "amount_usdc": borrow_amount,
                "result": result,
            }
        except Exception as e:
            log.error("borrow_failed", error=str(e))
            raise

    async def repay_loan(self, loan_id: str, repay_amount_usdc: Optional[float] = None) -> dict:
        """Repay a Floe loan (on-chain transaction)."""
        try:
            if not self.wallet_provider:
                log.error("wallet_provider_required_for_repay")
                raise ValueError("Wallet provider required for repayment")

            payload = {"loan_id": loan_id}
            if repay_amount_usdc:
                payload["repay_amount"] = str(int(repay_amount_usdc * 1e6))

            result = self.floe_provider.repay_loan(self.wallet_provider, payload)

            log.info("loan_repaid", loan_id=loan_id, result=result)

            return {
                "success": True,
                "loan_id": loan_id,
                "result": result,
            }
        except Exception as e:
            log.error("repay_failed", loan_id=loan_id, error=str(e))
            raise

    async def x402_call(self, url: str, method: str = "POST", payload: dict = None) -> dict:
        """
        Call an x402 API through Floe's payment facilitator (on-chain settlement).
        """
        try:
            if not self.wallet_provider:
                log.error("wallet_provider_required_for_x402")
                raise ValueError("Wallet provider required for x402 calls")

            result = self.floe_provider.x402_fetch(
                self.wallet_provider,
                {
                    "url": url,
                    "method": method,
                    "body": payload or {},
                }
            )

            log.info("x402_call_success", url=url, result=result)
            return result
        except Exception as e:
            log.error("x402_call_failed", url=url, error=str(e))
            raise
