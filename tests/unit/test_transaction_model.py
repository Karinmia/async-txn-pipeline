"""
Unit tests for Transaction schema validation.

These tests verify that the Pydantic Transaction schema correctly validates
transaction data.

Key concepts demonstrated:
- Testing Pydantic model validation
- Testing valid data
- Testing invalid data (validation errors)
- Using pytest.mark.parametrize for multiple test cases
"""

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import Transaction


@pytest.mark.unit
class TestTransactionSchema:
    """Test suite for Transaction Pydantic schema validation."""

    def test_valid_transaction_with_all_fields(self):
        """
        Test that a transaction with all fields validates successfully.

        This demonstrates testing a "happy path" - valid input should
        create a valid Transaction instance.
        """
        # Arrange: Prepare valid transaction data
        transaction_data = {
            "amount": "99.99",
            "currency": "USD",
            "created_at": "2024-01-15T14:30:00Z",
            "user_id": "550e8400-e29b-41d4-a716-446655440000",
            "merchant_id": "merchant_12345",
            "merchant_name": "eBooks Store",
            "merchant_country": "US",
            "payment_method": "card",
            "card_last_4": "4242",
            "card_brand": "visa",
            "ip_address": "192.168.1.100",
            "country": "US",
            "city": "San Francisco",
            "user_account_age_days": 365,
            "description": "Online purchase - books",
            "metadata": {"order_id": "ORD-12345"},
        }

        # Act: Create Transaction instance (Pydantic validates here)
        transaction = Transaction(**transaction_data)

        # Assert: Verify the transaction was created correctly
        assert transaction.amount == Decimal("99.99")
        assert transaction.currency == "USD"
        assert transaction.user_id == "550e8400-e29b-41d4-a716-446655440000"
        assert transaction.merchant_name == "eBooks Store"
        assert transaction.card_last_4 == "4242"
        assert transaction.metadata == {"order_id": "ORD-12345"}

    def test_valid_transaction_with_minimal_fields(self):
        """
        Test that a transaction with only required fields validates successfully.
        This demonstrates that optional fields are truly optional.
        """

        transaction_data = {
            "amount": "50.00",
            "currency": "EUR",
            "created_at": "2024-01-15T10:00:00Z",
            "user_id": "user_123",
            "merchant_id": "merchant_abc",
            "merchant_name": "Simple Store",
        }

        transaction = Transaction(**transaction_data)

        assert transaction.amount == Decimal("50.00")
        assert transaction.currency == "EUR"
        assert transaction.merchant_country is None  # Optional field should be None
        assert transaction.payment_method is None

    def test_invalid_transaction_missing_required_field(self):
        """
        Test that missing required fields raise ValidationError.

        This demonstrates testing validation errors - invalid input should
        raise ValidationError with helpful error messages.
        """

        # Missing required 'amount' field
        transaction_data = {
            "currency": "USD",
            "created_at": "2024-01-15T14:30:00Z",
            "user_id": "user_123",
            "merchant_id": "merchant_abc",
            "merchant_name": "Store",
        }

        with pytest.raises(ValidationError) as exc_info:
            Transaction(**transaction_data)

        # Verify the error message contains information about the missing field
        errors = exc_info.value.errors()
        assert len(errors) > 0
        # Check that one of the errors is about missing 'amount'
        assert any(error["loc"] == ("amount",) for error in errors)

    def test_invalid_transaction_negative_amount(self):
        """
        Test that negative amounts are rejected.

        The schema has a constraint: amount > 0 (gt=0)
        """

        transaction_data = {
            "amount": "-10.00",  # Negative amount should fail
            "currency": "USD",
            "created_at": "2024-01-15T14:30:00Z",
            "user_id": "user_123",
            "merchant_id": "merchant_abc",
            "merchant_name": "Store",
        }

        with pytest.raises(ValidationError) as exc_info:
            Transaction(**transaction_data)

        errors = exc_info.value.errors()
        # Find the error about amount
        amount_error = next((e for e in errors if e["loc"] == ("amount",)), None)
        assert amount_error is not None
        assert "greater than 0" in str(amount_error["msg"]).lower()

    @pytest.mark.parametrize(
        "invalid_currency",
        [
            "US",  # Too short (must be 3 characters)
            "USDD",  # Too long (must be 3 characters)
            "",  # Empty string
        ],
    )
    def test_invalid_currency_length(self, invalid_currency):
        """
        Test that invalid currency codes are rejected.

        This demonstrates using @pytest.mark.parametrize to test multiple
        similar cases without writing separate test functions.

        The parametrize decorator runs this test once for each value in the list.
        """
        transaction_data = {
            "amount": "100.00",
            "currency": invalid_currency,  # Invalid currency
            "created_at": "2024-01-15T14:30:00Z",
            "user_id": "user_123",
            "merchant_id": "merchant_abc",
            "merchant_name": "Store",
        }

        with pytest.raises(ValidationError) as exc_info:
            Transaction(**transaction_data)

        errors = exc_info.value.errors()
        currency_error = next((e for e in errors if e["loc"] == ("currency",)), None)
        assert currency_error is not None
