from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, JSON, String, UniqueConstraint

from app.core.database import Base


class IdempotencyRecord(Base):
    __tablename__ = "idempotency_records"
    __table_args__ = (
        UniqueConstraint("family_id", "operation", "key", name="uq_idempotency_scope"),
    )

    id = Column(Integer, primary_key=True, index=True)
    family_id = Column(Integer, nullable=False, index=True)
    operation = Column(String, nullable=False, index=True)
    key = Column(String, nullable=False, index=True)
    status_code = Column(Integer, nullable=False)
    response_body = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
