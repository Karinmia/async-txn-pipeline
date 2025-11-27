import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.dependencies import get_db
from app.messaging.client import rmq_client
from app.messaging.constants import INJEST_ROUTING_KEY
from app.models import Transaction as TransactionModel
from app.models import TransactionStage, TransactionStatus
from app.schemas import Transaction

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_transaction(
    transaction: Transaction,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict:
    """
    Create a new transaction.

    Accepts transaction JSON, validates it using Pydantic schema,
    and stores it in the database with status=RECEIVED and stage=INGESTING.

    Args:
        transaction: Transaction data validated by Pydantic schema
        db: Database session dependency

    Returns:
        dict: Created transaction with id, status, and stage

    Raises:
        HTTPException: If database operation fails
    """

    try:
        transaction_id = uuid.uuid4()
        logger.info(f"Generate uuid {transaction_id = }")

        # Convert Pydantic model to dict for JSONB storage
        transaction_data = transaction.model_dump(mode="json")

        logger.info(f"Received data {transaction_data = }, {transaction_id = }")

        # Create database model
        db_transaction = TransactionModel(
            id=transaction_id,
            status=TransactionStatus.RECEIVED,
            stage=TransactionStage.INGESTING,
            data=transaction_data,
        )

        logger.info("After building TransactionModel")

        # Store in database
        db.add(db_transaction)
        await db.commit()
        logger.info(f"Transaction created {transaction_id = }")

        await db.flush()  # Flush to get any database-generated values

        # Publish message to ingest queue with only the transaction id
        try:
            await rmq_client.publish(
                routing_key=INJEST_ROUTING_KEY,
                payload={"transaction_id": str(db_transaction.id)},
            )
            logger.info(
                "Published transaction to ingest queue",
                extra={"transaction_id": str(db_transaction.id)},
            )
        except Exception:
            # For now we log the error but still return 201 so DB write is not rolled back
            logger.exception(
                "Failed to publish transaction to ingest queue",
                extra={"transaction_id": str(db_transaction.id)},
            )

        return {
            "id": str(db_transaction.id),
            "status": db_transaction.status.value,
            "created_at": db_transaction.created_at.isoformat(),
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create transaction: {str(e)}",
        ) from e
