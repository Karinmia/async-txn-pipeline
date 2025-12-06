"""
Pytest configuration and shared fixtures for testing.

This module provides reusable fixtures for:
- Database connections and sessions
- FastAPI test client
- Mocked external services (RabbitMQ)
- Test data setup/teardown
"""

import asyncio
import os
from collections.abc import AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.config import Settings
from app.models import Base
from main import initialize_app


# Override settings for testing
@pytest.fixture(scope="session")
def test_settings() -> Settings:
    """
    Create test settings with test database configuration.
    """

    return Settings(
        postgres_url=os.getenv(
            "TEST_DB_URL",
            "postgresql+asyncpg://test_user:test_pwd@localhost:5433/txn_processor_test",
        ),
        db_echo=os.getenv("TEST_DB_ECHO", "false").lower() == "true",
    )


@pytest.fixture(scope="session")
def event_loop():
    """
    Create an event loop for the test session.
    This is needed for async fixtures and tests to work properly.
    """
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def test_db_engine(test_settings: Settings) -> AsyncGenerator[AsyncEngine, None]:
    """
    Create a test database engine.

    This fixture creates the database engine once per test session.
    The engine is used to create sessions for individual tests.

    Scope: session - created once, reused for all tests
    """

    # Get the database URL and ensure it's in asyncpg format
    db_url = test_settings.get_postgres_url()

    engine = create_async_engine(
        db_url,
        pool_size=5,
        max_overflow=10,
        echo=test_settings.db_echo,
    )

    yield engine

    # Cleanup: close the engine after all tests
    await engine.dispose()


@pytest.fixture(scope="function")
async def db_setup(test_db_engine: AsyncEngine) -> AsyncGenerator[None, None]:
    """
    Set up database schema before each test.

    Creates all tables defined in Base.metadata.
    After the test, drops all tables to ensure clean state.

    Scope: function - runs before/after each test
    """
    # Create all tables
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield

    # Cleanup: drop all tables after test
    async with test_db_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def test_db_session(
    test_db_engine: AsyncEngine, db_setup: None
) -> AsyncGenerator[AsyncSession, None]:
    """
    Provide a database session for a test.

    This fixture:
    1. Creates a new session for each test
    2. Yields the session for use in tests
    3. Rolls back any changes after the test (ensures test isolation)
    4. Closes the session

    Usage in tests:
        async def test_something(test_db_session: AsyncSession):
            # Use test_db_session here
            result = await test_db_session.execute(...)
    """
    # Create a session factory
    async_session_factory = async_sessionmaker(
        bind=test_db_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )

    async with async_session_factory() as session:
        # Start a transaction
        transaction = await session.begin()

        try:
            yield session
        finally:
            # Always rollback to ensure test isolation
            # This means each test starts with a clean database state
            await transaction.rollback()
            # Session is automatically closed by the context manager
            # No need to explicitly close it here


@pytest.fixture
def mock_rmq_client(monkeypatch):
    """
    Mock RabbitMQ client to avoid actual message queue calls during tests.

    This fixture replaces the real rmq_client with a mock that:
    - Has all the same methods (publish, initial_setup, close, etc.)
    - Returns immediately without actually connecting to RabbitMQ
    - Can be inspected in tests to verify calls were made

    Usage in tests:
        def test_something(mock_rmq_client):
            # The mock is automatically used
            # You can check if publish was called:
            # mock_rmq_client.publish.assert_called_once()
    """
    # Create a mock client with async methods
    mock_client = MagicMock()
    mock_client.publish = AsyncMock(return_value=None)
    mock_client.initial_setup = AsyncMock(return_value=None)
    mock_client.close = AsyncMock(return_value=None)
    mock_client.connect = AsyncMock(return_value=None)

    # Patch the rmq_client in the routers module
    # This ensures the router uses our mock instead of the real client
    from app.routers import transactions

    monkeypatch.setattr(transactions, "rmq_client", mock_client)

    return mock_client


@pytest.fixture
def app(mock_rmq_client, test_db_engine: AsyncEngine):
    """
    Create a FastAPI application instance for testing.

    This fixture:
    1. Creates a fresh app instance
    2. Uses the mocked RabbitMQ client (via mock_rmq_client fixture)
    3. Overrides the database dependency to use test database engine
    4. Can be customized per test if needed

    The mock_rmq_client fixture is automatically applied via dependency.
    """
    from app.database import make_session
    from app.dependencies import get_db

    app_instance = initialize_app()

    # Override the get_db dependency to use test database
    async def override_get_db():
        async with make_session(test_db_engine) as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise
            # Session is automatically closed by make_session context manager
            # No need to explicitly close it here

    app_instance.dependency_overrides[get_db] = override_get_db

    yield app_instance

    # Cleanup: Clear dependency overrides after test
    app_instance.dependency_overrides.clear()


@pytest.fixture
def test_client(app) -> TestClient:
    """
    Create a FastAPI TestClient for making HTTP requests in tests.

    TestClient is a synchronous wrapper around FastAPI that allows you to:
    - Make HTTP requests (GET, POST, etc.) to your endpoints
    - Check response status codes, headers, and body
    - Test your API without running a server

    Usage in tests:
        def test_endpoint(test_client: TestClient):
            response = test_client.post("/transactions", json={...})
            assert response.status_code == 201
            assert response.json()["id"] is not None

    Note: Use async_test_client for async tests to avoid event loop conflicts.
    """
    return TestClient(app)


@pytest.fixture
async def async_test_client(app) -> AsyncGenerator[AsyncClient, None]:
    """
    Create an async HTTP client for testing async endpoints.

    Use this fixture instead of test_client when:
    - Your test function is async
    - You need to test async endpoints with async database operations
    - You want to avoid event loop conflicts

    Usage in tests:
        @pytest.mark.asyncio
        async def test_endpoint(async_test_client: AsyncClient):
            response = await async_test_client.post("/transactions", json={...})
            assert response.status_code == 201
            assert response.json()["id"] is not None
    """
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client
