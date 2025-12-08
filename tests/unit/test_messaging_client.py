import json
from unittest.mock import AsyncMock, patch

import pytest

from app.messaging.client import RabbitMQClient


@pytest.mark.unit
class TestRabbitMQClient:
    """Unit tests for RabbitMQ client message handling."""

    @pytest.mark.anyio
    async def test_publish_serializes_payload(self):
        """
        Test that publish() correctly serializes JSON payload to bytes.

        This unit test verifies:
        1. The payload dict is JSON-serialized
        2. The serialized JSON is encoded as UTF-8 bytes
        3. The Message object is created with correct content_type
        4. The exchange.publish is called with the message

        We mock get_channel() to avoid actually connecting to RabbitMQ.
        """

        client = RabbitMQClient(url="amqp://test")

        # Create mock channel and exchange
        mock_exchange = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel.get_exchange.return_value = mock_exchange

        # Mock get_channel to return our mock instead of connecting to RabbitMQ
        with patch.object(client, "get_channel", return_value=mock_channel):
            await client.publish(routing_key="test.key", payload={"id": "123"})

        assert mock_exchange.publish.called

        call_args = mock_exchange.publish.call_args
        assert call_args is not None

        # Verify the message body contains correctly serialized JSON
        message = call_args[0][0]
        message_body = json.loads(message.body.decode())
        assert message_body == {"id": "123"}

        # Verify the message has correct content type
        assert message.content_type == "application/json"

    @pytest.mark.anyio
    async def test_publish_with_custom_exchange(self):
        """
        Test that publish() uses the specified exchange name.

        This verifies that the exchange_name parameter is properly passed
        to get_exchange().
        """
        client = RabbitMQClient(url="amqp://test")

        # Create mock channel and exchange
        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_channel.get_exchange.return_value = mock_exchange

        # Mock get_channel to return our mock
        with patch.object(client, "get_channel", return_value=mock_channel):
            await client.publish(
                routing_key="test.key",
                payload={"data": "value"},
                exchange_name="custom.exchange",
            )

        # Verify get_exchange was called with custom exchange name
        mock_channel.get_exchange.assert_called_once_with("custom.exchange")

    @pytest.mark.anyio
    async def test_publish_with_routing_key(self):
        """
        Test that publish() passes the routing key to exchange.publish().

        This verifies routing_key is correctly forwarded to the exchange.
        """
        client = RabbitMQClient(url="amqp://test")

        mock_channel = AsyncMock()
        mock_exchange = AsyncMock()
        mock_channel.get_exchange.return_value = mock_exchange

        with patch.object(client, "get_channel", return_value=mock_channel):
            await client.publish(
                routing_key="ingest.transaction", payload={"transaction_id": "abc123"}
            )

        # Verify publish was called with correct routing key
        call_args = mock_exchange.publish.call_args
        # routing_key should be the second positional arg or in kwargs
        if len(call_args[0]) > 1:
            assert call_args[0][1] == "ingest.transaction"
        else:
            assert call_args.kwargs["routing_key"] == "ingest.transaction"
