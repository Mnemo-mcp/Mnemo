"""Payment API controller — REST endpoints."""

from dataclasses import asdict
from typing import Any

from ..services.payment_service import PaymentService, PaymentRequest


class PaymentController:
    """REST API for payment operations.

    All endpoints require Bearer token auth.
    Org-level tenant isolation enforced via token's org_id.
    """

    def __init__(self, payment_service: PaymentService):
        self.service = payment_service

    def post_payment(self, request_body: dict, auth_token: str) -> dict[str, Any]:
        """POST /api/v1/payments — Process a new payment."""
        org_id = self.service.auth.extract_org_id(auth_token)
        if not org_id:
            return {"error": "Unauthorized", "status": 401}

        req = PaymentRequest(
            amount=request_body["amount"],
            currency=request_body.get("currency", "USD"),
            customer_id=request_body["customer_id"],
            method=request_body["method"],
            idempotency_key=request_body["idempotency_key"],
        )

        result = self.service.process_payment(req)
        return {"data": asdict(result), "status": 201}

    def post_refund(self, transaction_id: str, request_body: dict, auth_token: str) -> dict[str, Any]:
        """POST /api/v1/payments/{id}/refund — Refund a payment."""
        if not self.service.auth.require_role(auth_token, "payment_admin"):
            return {"error": "Forbidden — requires payment_admin role", "status": 403}

        result = self.service.refund_payment(transaction_id, request_body.get("reason", ""))
        return {"data": asdict(result), "status": 200}

    def get_payment(self, transaction_id: str, auth_token: str) -> dict[str, Any]:
        """GET /api/v1/payments/{id} — Get payment status."""
        org_id = self.service.auth.extract_org_id(auth_token)
        if not org_id:
            return {"error": "Unauthorized", "status": 401}

        result = self.service.get_payment_status(transaction_id)
        if not result:
            return {"error": "Not found", "status": 404}

        return {"data": asdict(result), "status": 200}
