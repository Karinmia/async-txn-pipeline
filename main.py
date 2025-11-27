from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.messaging.client import rmq_client
from app.routers import transactions


@asynccontextmanager
async def lifespan(app: FastAPI):
    await rmq_client.initial_setup()
    yield
    await rmq_client.close()


def initialize_app() -> FastAPI:
    """Initialize the FastAPI application."""

    _app = FastAPI(title="Transaction Processor", lifespan=lifespan)

    _app.include_router(transactions.router)

    return _app


app = initialize_app()


@app.get("/", tags=["general"])
@app.get("/healthcheck", tags=["general"])
def health_check():
    return {"status": "alive"}
