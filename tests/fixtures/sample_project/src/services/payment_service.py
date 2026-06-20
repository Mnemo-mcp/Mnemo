"""Payment Service - Handles payment processing with circuit breaker pattern."""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .middleware.auth import AuthMiddleware
from .middleware.circuit_breaker import CircuitBreaker


class PaymentStatus(Enum):
    PENDING = "pending"
    COMPLETED = "completed"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class PaymentRequest:
    amount: float
    currency: str
    customer_id: str
    method: str
    idempotency_key: str


@dataclass
class PaymentResponse:
    transaction_id: str
    status: PaymentStatus
    amount: float
    currency: str


class PaymentService:
    """Core payment processing service with resilience patterns."""

    def __init__(self, db, event_bus, auth: AuthMiddleware):
        self.db = db
        self.event_bus = event_bus
        self.auth = auth
        self.circuit_breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=30,
            half_open_max_calls=3
        )

    def process_payment(self, request: PaymentRequest) -> PaymentResponse:
        """Process a payment with idempotency and circuit breaker protection."""
        # Check idempotency
        existing = self.db.find_by_idempotency_key(request.idempotency_key)
        if existing:
            return existing

        # Circuit breaker wraps the external payment gateway call
        result = self.circuit_breaker.execute(
            lambda: self._call_gateway(request)
        )

        # Persist and publish event
        self.db.save_transaction(result)
        self.event_bus.publish("payment.completed", {
            "transaction_id": result.transaction_id,
            "amount": result.amount
        })

        return result

    def refund_payment(self, transaction_id: str, reason: str) -> PaymentResponse:
        """Issue a refund for a completed payment."""
        original = self.db.get_transaction(transaction_id)
        if not original:
            raise ValueError(f"Transaction {transaction_id} not found")

        if original.status != PaymentStatus.COMPLETED:
            raise ValueError(f"Cannot refund {original.status.value} transaction")

        refund = self.circuit_breaker.execute(
            lambda: self._call_gateway_refund(original, reason)
        )

        self.event_bus.publish("payment.refunded", {
            "transaction_id": transaction_id,
            "refund_id": refund.transaction_id
        })

        return refund

    def get_payment_status(self, transaction_id: str) -> Optional[PaymentResponse]:
        """Get current status of a payment."""
        return self.db.get_transaction(transaction_id)

    def _call_gateway(self, request: PaymentRequest) -> PaymentResponse:
        """External payment gateway call (wrapped by circuit breaker)."""
        # Gateway integration here
        pass

    def _call_gateway_refund(self, original, reason: str) -> PaymentResponse:
        """External refund call to payment gateway."""
        pass
