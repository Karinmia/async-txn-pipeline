import uuid
from datetime import datetime
from enum import Enum

from sqlalchemy import Float, String, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.sql import func

# from app.database import Base

class Base(AsyncAttrs, DeclarativeBase):
    pass


class TransactionStatus(str, Enum):
    """Processing status of transaction in the system."""
    
    RECEIVED = "RECEIVED"
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    FAILED = "FAILED"


class TransactionStage(str, Enum):
    """Business stage in the processing pipeline."""
    
    INGESTING = "INGESTING"
    RULES_CHECKING = "RULES_CHECKING"
    RISK_SCORING = "RISK_SCORING"
    DONE = "DONE"


class Transaction(Base):
    """
    Transaction database model.
    
    Stores transaction data with separate status and stage fields
    to track processing status and business pipeline stage independently.
    """
    
    __tablename__ = "transactions"
    
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        String,
        default=TransactionStatus.RECEIVED,
        nullable=False,
        index=True,
    )
    stage: Mapped[TransactionStage | None] = mapped_column(
        String,
        default=TransactionStage.INGESTING,
        nullable=True,
        index=True,
    )
    data: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )
    risk_score: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
