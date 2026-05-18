import os
from dataclasses import dataclass
from decimal import Decimal
from typing import Optional
import structlog

log = structlog.get_logger()


@dataclass
class CreditState:
    remaining_usdc: Decimal
    limit_usdc: Decimal
    active_loan_id: Optional[str]
    current_apr: Optional[Decimal]

    @property
    def utilization_pct(self) -> float:
        if self.limit_usdc == 0:
            return 1.0
        return float(1 - self.remaining_usdc / self.limit_usdc)

    @property
    def is_healthy(self) -> bool:
        min_reserve = Decimal(os.getenv("CREDIT_MIN_RESERVE_USDC", "5"))
        return self.remaining_usdc > min_reserve


@dataclass
class BorrowDecision:
    should_borrow: bool
    amount_usdc: Optional[Decimal]
    reason: str


class BudgetEngine:
    """
    Deterministic financial decision layer.
    The LLM reasons about WHAT to do.
    This engine decides WHETHER to borrow and HOW MUCH.
    No hallucination risk on financial decisions.
    """

    def __init__(self):
        self.warning_threshold = Decimal(os.getenv("CREDIT_WARNING_THRESHOLD", "0.20"))
        self.min_reserve = Decimal(os.getenv("CREDIT_MIN_RESERVE_USDC", "5.0"))
        self.max_borrow = Decimal(os.getenv("MAX_SINGLE_BORROW_USDC", "500.0"))
        self.max_apr = Decimal(os.getenv("MAX_APR_ACCEPTABLE", "0.15"))

    def evaluate_borrow(
        self,
        credit: CreditState,
        estimated_cost: Decimal,
        offered_apr: Optional[Decimal] = None,
    ) -> BorrowDecision:

        # Reject if APR too high
        if offered_apr and offered_apr > self.max_apr:
            return BorrowDecision(
                should_borrow=False,
                amount_usdc=None,
                reason=f"APR {offered_apr:.2%} exceeds max acceptable {self.max_apr:.2%}"
            )

        # Sufficient credit — no need to borrow
        if credit.remaining_usdc >= estimated_cost + self.min_reserve:
            return BorrowDecision(
                should_borrow=False,
                amount_usdc=None,
                reason="Sufficient credit available"
            )

        # Calculate shortfall + 25% buffer
        shortfall = estimated_cost + self.min_reserve - credit.remaining_usdc
        borrow_amount = min(shortfall * Decimal("1.25"), self.max_borrow)

        log.info("borrow_decision", shortfall=float(shortfall),
                 borrow_amount=float(borrow_amount))

        return BorrowDecision(
            should_borrow=True,
            amount_usdc=borrow_amount,
            reason=f"Shortfall ${shortfall:.2f}. Borrowing ${borrow_amount:.2f} with 25% buffer."
        )

    def should_repay_now(self, credit: CreditState, task_complete: bool) -> bool:
        """Always repay immediately after task completion to minimize interest."""
        return task_complete and credit.active_loan_id is not None