"""Ingest worker for the first stage of the transaction pipeline."""

import asyncio
import json
import logging

from aio_pika import IncomingMessage

from app.config import get_settings
from app.messaging.client import RabbitMQClient
from app.messaging.constants import INJEST_QUEUE

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")
# logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(message)s")
logger = logging.getLogger(__name__)

settings = get_settings()

# Dedicated RabbitMQ client for the ingest worker so we can tune consumer settings
ingest_rmq_client = RabbitMQClient(
    url=settings.get_rabbitmq_url(),
    prefetch_count=50,
    publisher_confirms=True,
)


async def handle(msg: IncomingMessage) -> None:
    """
    Handle messages from the ingest queue.

    Expects a JSON body with at least:
        { "transaction_id": "<uuid>" }
    """
    async with msg.process():
        try:
            payload = json.loads(msg.body.decode("utf-8"))
            transaction_id = payload.get("transaction_id")

            logger.info(
                "Ingest worker received message",
                extra={"transaction_id": transaction_id, "raw_payload": payload},
            )
            # TODO: Add ingest-stage logic here (e.g. basic validations, enrichment, etc.)

        except json.JSONDecodeError:
            logger.exception("Failed to decode message body as JSON")
            # Message is still acked due to context manager; consider DLQ in future.
        except Exception:
            logger.exception("Unexpected error while processing ingest message")
            # For now we still ack; DLQ / retries can be added later.


async def main() -> None:
    """
    Entry point for the ingest worker.

    Connects to RabbitMQ and starts consuming messages from the ingest queue.
    """

    # Ensure connection and channel are ready for this worker
    connection = await ingest_rmq_client.connect()
    logger.debug("Ingest worker :: connected to RabbitMQ")

    async with connection:
        channel = await ingest_rmq_client.get_channel()

        queue = await channel.get_queue(INJEST_QUEUE)
        await queue.consume(handle)

        logger.info("Ingest worker :: waiting for messages")

        # Keep the worker running forever
        await asyncio.Future()


if __name__ == "__main__":
    asyncio.run(main())
