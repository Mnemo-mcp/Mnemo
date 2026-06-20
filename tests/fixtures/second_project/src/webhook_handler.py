"""Webhook handler for payment events from sample_project's event bus."""


class WebhookHandler:
    """Processes incoming payment webhooks."""

    def handle_payment_completed(self, event: dict) -> None:
        """Handle payment.completed event from payment service."""
        payment_id = event.get("payment_id")
        self._update_order_status(payment_id, "paid")

    def handle_payment_failed(self, event: dict) -> None:
        """Handle payment.failed event."""
        payment_id = event.get("payment_id")
        self._update_order_status(payment_id, "failed")

    def _update_order_status(self, payment_id: str, status: str) -> None:
        """Update the order with payment status."""
        pass
