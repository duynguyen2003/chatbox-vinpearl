from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.backend.main import app
from src.backend.services.db import get_engine


@pytest.fixture(scope="session")
def loaded_database():
    """Require the seeded PostgreSQL dataset for integration tests."""
    engine = get_engine()
    try:
        with Session(engine) as session:
            loaded = session.scalar(text("SELECT count(*) FROM core.property"))
    except Exception as exc:
        pytest.skip(f"PostgreSQL test data is unavailable: {exc}")
    if not loaded:
        pytest.skip("PostgreSQL is not seeded; run python -m scripts.load_core")
    return engine


@pytest_asyncio.fixture
async def client():
    """Async HTTP client for testing API endpoints."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_llm():
    """Mock LLM to avoid calling OpenAI during tests.

    Usage in test:
        def test_something(mock_llm):
            # LLM calls will return mock response instead of hitting OpenAI
            ...
    """
    mock = AsyncMock()
    mock.ainvoke.return_value = AsyncMock(content="Mocked LLM response")
    return mock
