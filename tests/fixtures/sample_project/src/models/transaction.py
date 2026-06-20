"""Data models for payment service."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Transaction:
    """Payment transaction record."""
    id: str
    customer_id: str
    org_id: str
    amount: float
    currency: str
    status: str
    method: str
    idempotency_key: str
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    refund_reason: Optional[str] = None
    gateway_reference: Optional[str] = None


@dataclass
class AuditEntry:
    """Audit log entry — who accessed what, without PHI."""
    action: str
    user_id: str
    org_id: str
    resource_type: str
    resource_id: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    ip_address: Optional[str] = None
