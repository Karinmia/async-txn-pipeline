from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Transaction Processor"
    postgres_url: str = "postgresql://localhost:5432/txn_processor"
    # rabbitmq_url: str = "amqp://localhost:5672"

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache
def get_settings():
    return Settings()
