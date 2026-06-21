"""Event bus for publishing domain events to SQS."""

import json
from typing import Any


class EventBus:
    """Publishes domain events to SQS for downstream consumers.

    Events:
      - payment.completed → triggers notification service
      - payment.refunded → triggers accounting reconciliation
      - payment.failed   → triggers retry queue
    """

    def __init__(self, sqs_queue_url: str):
        self.sqs_queue_url = sqs_queue_url

    def publish(self, event_type: str, payload: dict[str, Any]) -> str:
        """Publish event to SQS. Returns message ID."""
        message = {
            "event_type": event_type,
            "payload": payload,
            "version": "1.0",
        }
        # SQS send_message call here
        return self._send_to_sqs(json.dumps(message))

    def _send_to_sqs(self, body: str) -> str:
        """Send message to SQS queue."""
        pass
