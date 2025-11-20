import logging

from fastapi import FastAPI


logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')

logger = logging.getLogger(__name__)


def initialize_app() -> FastAPI:
    _app = FastAPI(title="Transaction Processor")
    
    return _app


app = initialize_app()


@app.get("/", tags=['general'])
@app.get("/healthcheck", tags=['general'])
def health_check():
    return {"status": "alive"}

