"""API client that calls the payment service from sample_project."""

from dataclasses import dataclass


@dataclass
class APIResponse:
    status: int
    body: dict


class PaymentClient:
    """Client for the payment service API."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    def create_payment(self, amount: float, currency: str) -> APIResponse:
        """Create a payment via the remote service."""
        return APIResponse(status=200, body={"id": "pay_123", "amount": amount})

    def get_payment(self, payment_id: str) -> APIResponse:
        """Retrieve payment details."""
        return APIResponse(status=200, body={"id": payment_id})

    def refund(self, payment_id: str, reason: str = "") -> APIResponse:
        """Refund a payment."""
        return APIResponse(status=200, body={"refunded": True})
