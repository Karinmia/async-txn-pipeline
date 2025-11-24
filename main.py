from contextlib import asynccontextmanager

from aio_pika import ExchangeType
from fastapi import FastAPI

from app.routers import transactions
from app.messaging.client import rmq_client


async def setup_rabbitmq():
    await rmq_client.connect()
        
    # Declare pipeline exchange
    await rmq_client.declare_exchange("pipeline", ExchangeType.DIRECT, durable=True)

    # Declare queues for your stages
    await rmq_client.declare_queue("ingest_queue")
    await rmq_client.declare_queue("rules_queue")
    await rmq_client.declare_queue("risk_queue")

    await rmq_client.bind_queue("ingest_queue", "pipeline", "ingest")
    await rmq_client.bind_queue("rules_queue", "pipeline", "rules")
    await rmq_client.bind_queue("risk_queue", "pipeline", "risk")


def initialize_app() -> FastAPI:
    """Initialize the FastAPI application."""
    
    @asynccontextmanager
    def lifespan():
        await setup_rabbitmq()
        yield
        await rmq_client.close()
    
    _app = FastAPI(title="Transaction Processor")
    
    _app.include_router(transactions.router)
    
    return _app


app = initialize_app()


@app.get("/", tags=['general'])
@app.get("/healthcheck", tags=['general'])
def health_check():
    return {"status": "alive"}
