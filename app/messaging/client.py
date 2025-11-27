import asyncio
import json
import logging
from typing import Optional

import aio_pika
from aio_pika import DeliveryMode, ExchangeType, Message, RobustChannel, RobustConnection

from app.config import get_settings
from app.messaging.constants import *

logger = logging.getLogger(__name__)


class RabbitMQClient:
    def __init__(
        self,
        url: str,
        prefetch_count: int = 10,
        publisher_confirms: bool = False,
    ):
        self.url = url
        self.prefetch_count = prefetch_count
        self.publisher_confirms = publisher_confirms

        self._connection: Optional[RobustConnection] = None
        self._channel: Optional[RobustChannel] = None

        # Prevent concurrent connection attempts
        self._lock = asyncio.Lock()

    async def connect(self) -> RobustConnection:
        if self._connection and not self._connection.is_closed:
            return self._connection

        async with self._lock:
            if self._connection and not self._connection.is_closed:
                return self._connection

            logger.debug("Connecting to RabbitMQ...")
            self._connection = await aio_pika.connect_robust(self.url)

        logger.debug("Connected to RabbitMQ.")

        return self._connection

    async def get_channel(self) -> RobustChannel:
        if self._channel and not self._channel.is_closed:
            return self._channel

        conn = await self.connect()

        async with self._lock:
            if self._channel and not self._channel.is_closed:
                return self._channel

            # Enable publisher confirms (optional)
            self._channel = await conn.channel(publisher_confirms=self.publisher_confirms)

            # Set prefetch (consumer backpressure)
            await self._channel.set_qos(prefetch_count=self.prefetch_count)

        return self._channel

    async def declare_exchange(
        self,
        name: str,
        exchange_type: ExchangeType = ExchangeType.DIRECT,
        durable: bool = True,
    ):
        channel = await self.get_channel()
        return await channel.declare_exchange(name, exchange_type, durable=durable)

    async def declare_queue(
        self,
        name: str,
        durable: bool = True,
        dead_letter_exchange: Optional[str] = None,
    ):
        arguments = {}

        if dead_letter_exchange:
            arguments["x-dead-letter-exchange"] = dead_letter_exchange

        channel = await self.get_channel()
        return await channel.declare_queue(name, durable=durable, arguments=arguments)

    async def bind_queue(self, queue_name: str, exchange_name: str, routing_key: str):
        channel = await self.get_channel()
        exchange = await channel.get_exchange(exchange_name)
        queue = await channel.get_queue(queue_name)
        await queue.bind(exchange, routing_key=routing_key)

    async def publish(
        self,
        routing_key: str,
        payload: dict,
        exchange_name: str = DEFAULT_EXCHANGE_NAME,
        delivery_mode: DeliveryMode = DeliveryMode.PERSISTENT,
    ):
        channel = await self.get_channel()
        exchange = await channel.get_exchange(exchange_name)

        body = json.dumps(payload).encode("utf-8")

        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=delivery_mode,
        )

        await exchange.publish(message, routing_key=routing_key)

    async def close(self):
        """Graceful shutdown"""
        if self._channel and not self._channel.is_closed:
            await self._channel.close()

        if self._connection and not self._connection.is_closed:
            await self._connection.close()

    async def initial_setup(self):
        """
        This method should be called on FastAPI app startup.
        """

        await self.connect()

        # Declare pipeline exchange
        await self.declare_exchange(DEFAULT_EXCHANGE_NAME, ExchangeType.DIRECT, durable=True)

        # Declare queues for your stages
        await self.declare_queue(INJEST_QUEUE)
        await self.declare_queue(RULES_QUEUE)
        await self.declare_queue(RISK_QUEUE)

        await self.bind_queue(INJEST_QUEUE, DEFAULT_EXCHANGE_NAME, INJEST_ROUTING_KEY)
        await self.bind_queue(RULES_QUEUE, DEFAULT_EXCHANGE_NAME, RULES_ROUTING_KEY)
        await self.bind_queue(RISK_QUEUE, DEFAULT_EXCHANGE_NAME, RISK_ROUTING_KEY)


# Create a single RabbitMQClient instance to reuse across FastAPI app
settings = get_settings()

rmq_client = RabbitMQClient(
    url=settings.get_rabbitmq_url(), prefetch_count=50, publisher_confirms=True
)
