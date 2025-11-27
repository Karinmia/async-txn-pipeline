"""Module containing constants relevant for RabbitMQ messaging"""

# a custom exchange that will be used as default
DEFAULT_EXCHANGE_NAME = "txn-pipeline"

INJEST_QUEUE = "ingest_queue"
INJEST_ROUTING_KEY = "ingest"

RULES_QUEUE = "rules_queue"
RULES_ROUTING_KEY = "rules"

RISK_QUEUE = "risk_queue"
RISK_ROUTING_KEY = "risk"
