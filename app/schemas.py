import ipaddress
from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.constants import COMMON_CURRENCIES, KNOWN_CARD_BRANDS


class PaymentMethod(str, Enum):
    """Allowed payment methods in the system."""

    CARD = "card"
    PAYPAL = "paypal"
    BANK_TRANSFER = "bank_transfer"


class Transaction(BaseModel):
    """
    Transaction data model for the 3-stage processing pipeline.

    This model represents a financial transaction that flows through:
    1. Ingest Stage: Field validation and format checking
    2. Business Rules Stage: Business logic validation (limits, permissions)
    3. Risk Scoring Stage: Risk computation and fraud detection

    For detailed field usage by stage, see: docs/TRANSACTION_SCHEMA.md
    """

    # Core Required Fields
    amount: Decimal = Field(
        ..., description="Transaction amount (must be positive)", gt=0, decimal_places=2
    )
    currency: str = Field(
        ..., description="ISO 4217 currency code (e.g., USD, EUR)", min_length=3, max_length=3
    )
    created_at: datetime = Field(..., description="Transaction timestamp")
    user_id: str = Field(..., description="User identifier (UUID or string)", min_length=1)

    # Merchant Information
    merchant_id: str = Field(..., description="Merchant identifier", min_length=1)
    merchant_name: str = Field(..., description="Merchant business name", min_length=1)
    merchant_country: Optional[str] = Field(
        None,
        description="Merchant location country code (ISO 3166-1 alpha-2).",
        min_length=2,
        max_length=2,
    )

    # Payment Details
    payment_method: PaymentMethod = Field(
        ...,
        description="Payment method (card, paypal, or bank_transfer).",
    )
    card_last_4: Optional[str] = Field(
        None,
        description="Last 4 digits of payment card.",
        min_length=4,
        max_length=4,
    )
    card_brand: Optional[str] = Field(
        None,
        description="Card brand (e.g., visa, mastercard, amex).",
    )

    # Location
    ip_address: Optional[str] = Field(None, description="Client IP address (IPv4 or IPv6)")
    country: Optional[str] = Field(
        None,
        description="Transaction country code (ISO 3166-1 alpha-2)",
        min_length=2,
        max_length=2,
    )
    city: Optional[str] = Field(None, description="Transaction city")

    # User Context (for risk scoring)
    user_account_age_days: Optional[int] = Field(
        None,
        description="User account age in days",
        ge=0,
    )

    # Metadata
    description: Optional[str] = Field(None, description="Transaction description or memo")
    metadata: Optional[dict] = Field(
        None, description="Additional flexible metadata for extensibility"
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "amount": "99.99",
                "currency": "USD",
                "created_at": "2024-01-15T14:30:00Z",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "merchant_id": "merchant_12345",
                "merchant_name": "eBooks Store",
                "merchant_country": "US",
                "payment_method": PaymentMethod.CARD.value,
                "card_last_4": "4242",
                "card_brand": "visa",
                "ip_address": "192.168.1.100",
                "country": "US",
                "city": "San Francisco",
                "user_account_age_days": 365,
                "description": "Online purchase - books",
                "metadata": {"order_id": "ORD-12345", "referral_source": "web"},
            }
        }
    )

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        """
        Validate currency is a valid ISO 4217 code.
        Used in: INGEST STAGE
        """
        currency_upper = v.upper()
        if currency_upper not in COMMON_CURRENCIES:
            # Allow any 3-letter uppercase code as ISO 4217 has many codes
            if not (len(currency_upper) == 3 and currency_upper.isalpha()):
                raise ValueError(
                    f"Currency must be a valid ISO 4217 code (3 letters), " f"got: {v}"
                )
        return currency_upper

    @field_validator("card_last_4")
    @classmethod
    def validate_card_last_4(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate card_last_4 is exactly 4 digits.
        Used in: INGEST STAGE
        """
        if v is not None:
            if not v.isdigit() or len(v) != 4:
                raise ValueError(f"card_last_4 must be exactly 4 digits, got: {v}")
        return v

    @field_validator("created_at")
    @classmethod
    def validate_created_at(cls, v: datetime) -> datetime:
        """
        Validate created_at is not in the future.
        Used in: INGEST STAGE
        """
        now = datetime.now(timezone.utc)
        if v > now:
            raise ValueError(
                f"created_at cannot be in the future. " f"Got: {v}, Current time: {now}"
            )
        return v

    @field_validator("country", "merchant_country")
    @classmethod
    def validate_country_code(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate country code is 2-letter uppercase.
        Used in: INGEST STAGE
        """
        if v is not None:
            country_upper = v.upper()
            if not (len(country_upper) == 2 and country_upper.isalpha()):
                raise ValueError(
                    f"Country code must be ISO 3166-1 alpha-2 (2 letters), " f"got: {v}"
                )
            return country_upper
        return v

    @field_validator("ip_address")
    @classmethod
    def validate_ip_address(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate IP address format (IPv4 or IPv6).
        Used in: INGEST STAGE
        """
        if v is None:
            return v

        try:
            # This validates both IPv4 and IPv6
            ipaddress.ip_address(v)
            return v
        except ValueError:
            raise ValueError(f"ip_address must be a valid IPv4 or IPv6 address, got: {v}")

    @field_validator("card_brand")
    @classmethod
    def validate_card_brand(cls, v: Optional[str]) -> Optional[str]:
        """
        Validate and normalize card brand.
        Used in: INGEST STAGE
        """
        if v is None:
            return v

        brand_lower = v.lower()
        if brand_lower not in KNOWN_CARD_BRANDS:
            raise ValueError(f"card_brand must be one of {KNOWN_CARD_BRANDS}, got: {v}")
        return brand_lower


# Example transaction data for testing and documentation
EXAMPLE_TRANSACTION = Transaction(
    amount=Decimal("99.99"),
    currency="USD",
    created_at=datetime(2024, 1, 15, 14, 30, 0, tzinfo=timezone.utc),
    user_id="550e8400-e29b-41d4-a716-446655440000",
    merchant_id="merchant_12345",
    merchant_name="eBooks Store",
    merchant_country="US",
    payment_method=PaymentMethod.CARD,
    card_last_4="4242",
    card_brand="visa",
    ip_address="192.168.1.100",
    country="US",
    city="San Francisco",
    user_account_age_days=365,
    description="Online purchase - books",
    metadata={"order_id": "ORD-12345", "referral_source": "web"},
)

# Minimal example (only required fields)
EXAMPLE_TRANSACTION_MINIMAL = Transaction(
    amount=Decimal("50.00"),
    currency="EUR",
    created_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc),
    user_id="user_123",
    merchant_id="merchant_abc",
    merchant_name="Simple Store",
    payment_method=PaymentMethod.BANK_TRANSFER,
)
