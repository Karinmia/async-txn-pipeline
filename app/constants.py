# ISO 4217 currency codes (common ones for validation)
COMMON_CURRENCIES = (
    "USD",
    "EUR",
    "GBP",
    "JPY",
    "AUD",
    "CAD",
    "CHF",
    "CNY",
    "INR",
    "BRL",
    "MXN",
    "SGD",
    "HKD",
    "NZD",
    "SEK",
    "NOK",
    "DKK",
    "PLN",
    "ZAR",
    "KRW",
)

# Payment methods allowed in the system
ALLOWED_PAYMENT_METHODS = {"card", "bank_transfer", "wallet", "cash"}

# Known card brands for validation
KNOWN_CARD_BRANDS = {"visa", "mastercard", "amex", "discover", "jcb", "diners"}
