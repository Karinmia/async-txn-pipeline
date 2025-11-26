from functools import lru_cache
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "Transaction Processor"

    # Database settings
    db_user: str = "transaction_user"
    db_password: str = "transaction_pwd"
    db_name: str = "transaction_processor"
    db_host: str = "localhost"
    db_port: int = 5432
    postgres_url: str | None = None

    # Database pool settings
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # RabbitMQ settings
    rabbitmq_user: str = "transaction_user"
    rabbitmq_password: str = "transaction_pwd"
    rabbitmq_host: str = "localhost"
    rabbitmq_port: int = 5672
    rabbitmq_url: str | None = None

    class Config:
        env_file = ".env"
        extra = "ignore"

    def get_postgres_url(self) -> str:
        """Get PostgreSQL URL, constructing from components if not provided."""
        if self.postgres_url:
            # Convert to async format if needed
            if self.postgres_url.startswith("postgresql://"):
                return self.postgres_url.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif self.postgres_url.startswith("postgresql+asyncpg://"):
                return self.postgres_url
            else:
                return f"postgresql+asyncpg://{self.postgres_url}"

        # Construct from components
        password = quote_plus(self.db_password)
        return (
            f"postgresql+asyncpg://{self.db_user}:{password}@"
            f"{self.db_host}:{self.db_port}/{self.db_name}"
        )

    def get_rabbitmq_url(self) -> str:
        """Get RabbitMQ AMQP URL, constructing from components if not provided."""
        if self.rabbitmq_url:
            return self.rabbitmq_url

        # Construct from components
        password = quote_plus(self.rabbitmq_password)
        return (
            f"amqp://{self.rabbitmq_user}:{password}@" f"{self.rabbitmq_host}:{self.rabbitmq_port}/"
        )


@lru_cache
def get_settings():
    return Settings()
