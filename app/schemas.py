from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ISO 4217 currency codes (common ones for validation)
COMMON_CURRENCIES = {
    "USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "CNY", "INR", "BRL",
    "MXN", "SGD", "HKD", "NZD", "SEK", "NOK", "DKK", "PLN", "ZAR", "KRW"
}


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
        ...,
        description="Transaction amount (must be positive)",
        gt=0,
        decimal_places=2
    )
    currency: str = Field(
        ...,
        description="ISO 4217 currency code (e.g., USD, EUR)",
        min_length=3,
        max_length=3
    )
    created_at: datetime = Field(
        ...,
        description="Transaction timestamp (cannot be in the future)"
    )
    user_id: str = Field(
        ...,
        description="User identifier (UUID or string)",
        min_length=1
    )

    # Merchant Information
    merchant_id: str = Field(
        ...,
        description="Merchant identifier",
        min_length=1
    )
    merchant_name: str = Field(
        ...,
        description="Merchant business name",
        min_length=1
    )
    merchant_country: Optional[str] = Field(
        None,
        description="Merchant location country code (ISO 3166-1 alpha-2). "
                    "Used in Risk Scoring for cross-border detection.",
        min_length=2,
        max_length=2
    )

    # Payment Details
    payment_method: Optional[str] = Field(
        None,
        description="Payment method (e.g., card, bank_transfer, wallet). "
                    "Used in Business Rules and Risk Scoring stages."
    )
    card_last_4: Optional[str] = Field(
        None,
        description="Last 4 digits of payment card. "
                    "Used in Risk Scoring for payment method analysis.",
        min_length=4,
        max_length=4
    )
    card_brand: Optional[str] = Field(
        None,
        description="Card brand (e.g., visa, mastercard, amex). "
                    "Used in Risk Scoring stage."
    )

    # Location
    ip_address: Optional[str] = Field(
        None,
        description="Client IP address (IPv4 or IPv6). "
                    "Used in Ingest (format validation) and Risk Scoring "
                    "(geographic risk)."
    )
    country: Optional[str] = Field(
        None,
        description="Transaction country code (ISO 3166-1 alpha-2). "
                    "Used in Risk Scoring for geographic risk analysis.",
        min_length=2,
        max_length=2
    )
    city: Optional[str] = Field(
        None,
        description="Transaction city. "
                    "Used in Risk Scoring for location pattern analysis."
    )

    # User Context (for risk scoring)
    user_account_age_days: Optional[int] = Field(
        None,
        description="User account age in days. "
                    "Used in Risk Scoring (new accounts = higher risk).",
        ge=0
    )

    # Metadata
    description: Optional[str] = Field(
        None,
        description="Transaction description or memo"
    )
    metadata: Optional[dict] = Field(
        None,
        description="Additional flexible metadata for extensibility"
    )

    class Config:
        """Pydantic model configuration."""
        json_schema_extra = {
            "example": {
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
                "metadata": {
                    "order_id": "ORD-12345",
                    "referral_source": "web"
                }
            }
        }


# Example transaction data for testing and documentation
EXAMPLE_TRANSACTION = Transaction(
    amount=Decimal("99.99"),
    currency="USD",
    created_at=datetime(2024, 1, 15, 14, 30, 0),
    user_id="550e8400-e29b-41d4-a716-446655440000",
    merchant_id="merchant_12345",
    merchant_name="eBooks Store",
    merchant_country="US",
    payment_method="card",
    card_last_4="4242",
    card_brand="visa",
    ip_address="192.168.1.100",
    country="US",
    city="San Francisco",
    user_account_age_days=365,
    description="Online purchase - books",
    metadata={
        "order_id": "ORD-12345",
        "referral_source": "web"
    }
)

# Minimal example (only required fields)
EXAMPLE_TRANSACTION_MINIMAL = Transaction(
    amount=Decimal("50.00"),
    currency="EUR",
    created_at=datetime(2024, 1, 15, 10, 0, 0),
    user_id="user_123",
    merchant_id="merchant_abc",
    merchant_name="Simple Store"
)

