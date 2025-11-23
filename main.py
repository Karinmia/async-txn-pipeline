from fastapi import FastAPI

from app.routers import transactions


def initialize_app() -> FastAPI:
    """Initialize the FastAPI application."""
    
    _app = FastAPI(title="Transaction Processor")
    
    _app.include_router(transactions.router)
    
    return _app


app = initialize_app()


@app.get("/", tags=['general'])
@app.get("/healthcheck", tags=['general'])
def health_check():
    return {"status": "alive"}
