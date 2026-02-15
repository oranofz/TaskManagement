"""Event outbox pattern for reliable event publishing."""
from datetime import datetime
from uuid import UUID, uuid4
from sqlalchemy import Column, String, DateTime, Boolean, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID, JSONB
from app.shared.database import Base


class EventOutbox(Base):
    """Event outbox table for reliable event publishing."""

    __tablename__ = "event_outbox"

    id = Column(PGUUID(as_uuid=True), primary_key=True, default=uuid4)
    event_id = Column(PGUUID(as_uuid=True), nullable=False, unique=True)
    event_type = Column(String(255), nullable=False)
    aggregate_id = Column(PGUUID(as_uuid=True), nullable=False)
    tenant_id = Column(PGUUID(as_uuid=True), nullable=False)
    payload = Column(JSONB, nullable=False)
    version = Column(String(50), nullable=False, default="1")
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    processed_at = Column(DateTime, nullable=True)
    is_processed = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text, nullable=True)

