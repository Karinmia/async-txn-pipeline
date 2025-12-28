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

from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas import PaymentMethod, Transaction


@pytest.fixture
def make_transaction_data():
    """Fixture to create transaction data with overrides."""

    def _make(**overrides):
        base = {
            "amount": "100.00",
            "currency": "USD",
            "created_at": datetime.now(timezone.utc),
            "user_id": "user_123",
            "merchant_id": "merchant_123",
            "merchant_name": "Test Store",
            "payment_method": "card",
        }
        return {**base, **overrides}

    return _make


def assert_validation_error_on_field(exc_info, field_name: str):
    """Helper to assert validation error occurred on a specific field."""
    errors = exc_info.value.errors()
    assert any(
        field_name in str(e.get("loc", "")) for e in errors
    ), f"Expected validation error on '{field_name}', got: {[e.get('loc') for e in errors]}"


@pytest.mark.unit
class TestTransactionSchema:
    """Test suite for Transaction Pydantic schema validation."""

    def test_valid_transaction_with_all_fields(self):
        """
        Test that a transaction with all fields validates successfully.
        """

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

        transaction = Transaction(**transaction_data)

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
            "payment_method": "card",
        }

        transaction = Transaction(**transaction_data)

        assert transaction.amount == Decimal("50.00")
        assert transaction.currency == "EUR"
        assert transaction.merchant_country is None  # Optional field should be None
        assert transaction.payment_method == PaymentMethod.CARD

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


@pytest.mark.unit
class TestTransactionFieldValidators:
    """Test suite for Transaction Pydantic field validators."""

    @pytest.mark.parametrize(
        "valid_currency,expected",
        [
            ("usd", "USD"),  # Lowercase should be uppercased
            ("USD", "USD"),  # Already uppercase
            ("eur", "EUR"),
            ("GBP", "GBP"),
            ("ZZZ", "ZZZ"),  # Uncommon but valid format
        ],
    )
    def test_currency_validator_valid(self, make_transaction_data, valid_currency, expected):
        """Test that valid currency codes pass and are uppercased."""
        transaction = Transaction(**make_transaction_data(currency=valid_currency))
        assert transaction.currency == expected

    @pytest.mark.parametrize(
        "invalid_currency",
        [
            "US",  # Too short
            "USDD",  # Too long
            "12D",  # Contains digits
            "US$",  # Contains special char
            "",  # Empty
        ],
    )
    def test_currency_validator_invalid(self, make_transaction_data, invalid_currency):
        """Test that invalid currency codes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Transaction(**make_transaction_data(currency=invalid_currency))

        assert_validation_error_on_field(exc_info, "currency")

    def test_card_last_4_valid(self, make_transaction_data):
        """Test that valid 4-digit card numbers pass."""
        transaction = Transaction(**make_transaction_data(card_last_4="4242"))
        assert transaction.card_last_4 == "4242"

    def test_card_last_4_none(self, make_transaction_data):
        """Test that None/omitted card_last_4 is allowed."""
        transaction = Transaction(**make_transaction_data())
        assert transaction.card_last_4 is None

    @pytest.mark.parametrize(
        "invalid_card",
        [
            "123",  # Too short
            "12345",  # Too long
            "abcd",  # Not digits
            "12a4",  # Mixed
            "",  # Empty
        ],
    )
    def test_card_last_4_invalid(self, make_transaction_data, invalid_card):
        """Test that invalid card_last_4 values are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Transaction(**make_transaction_data(card_last_4=invalid_card))
        assert_validation_error_on_field(exc_info, "card_last_4")

    def test_created_at_past_valid(self, make_transaction_data):
        """Test that past timestamps are valid."""
        past_time = datetime.now(timezone.utc) - timedelta(hours=1)
        transaction = Transaction(**make_transaction_data(created_at=past_time))
        assert transaction.created_at == past_time

    def test_created_at_now_valid(self, make_transaction_data):
        """Test that current timestamp is valid."""
        now = datetime.now(timezone.utc)
        transaction = Transaction(**make_transaction_data(created_at=now))
        assert transaction.created_at == now

    def test_created_at_future_invalid(self, make_transaction_data):
        """Test that future timestamps are rejected."""
        future_time = datetime.now(timezone.utc) + timedelta(hours=1)
        with pytest.raises(ValidationError) as exc_info:
            Transaction(**make_transaction_data(created_at=future_time))
        assert_validation_error_on_field(exc_info, "created_at")

    @pytest.mark.parametrize(
        "country_field,valid_code,expected",
        [
            ("country", "us", "US"),
            ("country", "US", "US"),
            ("merchant_country", "gb", "GB"),
            ("merchant_country", "GB", "GB"),
        ],
    )
    def test_country_code_valid(self, make_transaction_data, country_field, valid_code, expected):
        """Test that valid country codes pass and are uppercased."""
        transaction = Transaction(**make_transaction_data(**{country_field: valid_code}))
        assert getattr(transaction, country_field) == expected

    @pytest.mark.parametrize(
        "country_field,invalid_code",
        [
            ("country", "U"),  # Too short
            ("country", "USA"),  # Too long
            ("country", "U1"),  # Contains digit
            ("merchant_country", ""),  # Empty
        ],
    )
    def test_country_code_invalid(self, make_transaction_data, country_field, invalid_code):
        """Test that invalid country codes are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Transaction(**make_transaction_data(**{country_field: invalid_code}))
        assert_validation_error_on_field(exc_info, country_field)

    @pytest.mark.parametrize(
        "valid_ip",
        [
            "192.168.1.1",  # IPv4 private
            "8.8.8.8",  # IPv4 public
            "2001:0db8:85a3::8a2e:0370:7334",  # IPv6
            "::1",  # IPv6 loopback
            "fe80::1",  # IPv6 link-local
        ],
    )
    def test_ip_address_valid(self, make_transaction_data, valid_ip):
        """Test that valid IP addresses pass."""
        transaction = Transaction(**make_transaction_data(ip_address=valid_ip))
        assert transaction.ip_address == valid_ip

    def test_ip_address_none(self, make_transaction_data):
        """Test that None/omitted ip_address is allowed."""
        transaction = Transaction(**make_transaction_data())
        assert transaction.ip_address is None

    @pytest.mark.parametrize(
        "invalid_ip",
        [
            "256.1.1.1",  # Invalid octet
            "192.168.1",  # Incomplete IPv4
            "192.168.1.1.1",  # Too many octets
            "not-an-ip",  # Not an IP
            "google.com",  # Hostname not IP
        ],
    )
    def test_ip_address_invalid(self, make_transaction_data, invalid_ip):
        """Test that invalid IP addresses are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Transaction(**make_transaction_data(ip_address=invalid_ip))
        assert_validation_error_on_field(exc_info, "ip_address")

    @pytest.mark.parametrize(
        "payment_method",
        [
            PaymentMethod.CARD,
            PaymentMethod.PAYPAL,
            PaymentMethod.BANK_TRANSFER,
        ],
    )
    def test_payment_method_valid(self, make_transaction_data, payment_method):
        """Test that valid payment methods pass."""
        transaction = Transaction(**make_transaction_data(payment_method=payment_method.value))
        assert transaction.payment_method == payment_method

    def test_payment_method_missing_raises_error(self):
        """Test that omitted payment_method raises ValidationError."""
        data = {
            "amount": "100.00",
            "currency": "USD",
            "created_at": datetime.now(timezone.utc),
            "user_id": "user_123",
            "merchant_id": "merchant_123",
            "merchant_name": "Test Store",
            # payment_method is intentionally omitted
        }
        with pytest.raises(ValidationError) as exc_info:
            Transaction(**data)
        assert_validation_error_on_field(exc_info, "payment_method")

    @pytest.mark.parametrize(
        "invalid_method",
        [
            "bitcoin",  # Not in allowed list
            "crypto",  # Not in allowed list
            "check",  # Not in allowed list
            "",  # Empty string
        ],
    )
    def test_payment_method_invalid(self, make_transaction_data, invalid_method):
        """Test that invalid or empty payment methods are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Transaction(**make_transaction_data(payment_method=invalid_method))
        assert_validation_error_on_field(exc_info, "payment_method")

    @pytest.mark.parametrize(
        "card_brand,expected",
        [
            ("visa", "visa"),
            ("VISA", "visa"),  # Lowercase normalization
            ("mastercard", "mastercard"),
            ("amex", "amex"),
            ("discover", "discover"),
            ("jcb", "jcb"),
            ("diners", "diners"),
        ],
    )
    def test_card_brand_valid(self, make_transaction_data, card_brand, expected):
        """Test that valid card brands pass and are normalized."""
        transaction = Transaction(**make_transaction_data(card_brand=card_brand))
        assert transaction.card_brand == expected

    def test_card_brand_none(self, make_transaction_data):
        """Test that None/omitted card_brand is allowed."""
        transaction = Transaction(**make_transaction_data())
        assert transaction.card_brand is None

    @pytest.mark.parametrize(
        "invalid_brand",
        [
            "unknown",
            "fake_card",
            "not_a_brand",
        ],
    )
    def test_card_brand_invalid(self, make_transaction_data, invalid_brand):
        """Test that invalid card brands are rejected."""
        with pytest.raises(ValidationError) as exc_info:
            Transaction(**make_transaction_data(card_brand=invalid_brand))
        assert_validation_error_on_field(exc_info, "card_brand")
