"""
Pytest configuration and fixtures.
"""
import asyncio
import os
import tempfile
from pathlib import Path

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.database import Base
from app.config import get_settings

# Test database URL (can be overridden by environment variable)
# Use SQLite for testing when Docker is not available
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "sqlite+aiosqlite:///./test.db?mode=memory&cache=shared")


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def engine():
    """Create a test database engine."""
    # Adjust engine parameters based on database type
    engine_kwargs = {
        "echo": False,
    }

    # For SQLite, don't use connection pool parameters
    if "sqlite" in TEST_DATABASE_URL:
        engine_kwargs["poolclass"] = NullPool
    else:
        # For MySQL/other databases, use connection pool
        engine_kwargs["poolclass"] = NullPool

    engine = create_async_engine(TEST_DATABASE_URL, **engine_kwargs)

    # Create tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    # Drop tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    """Create a test database session."""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        # Rollback after each test
        await session.rollback()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def sample_pdf_content():
    """Sample text content for testing PDF parsing."""
    return """
    合同编号：HT-2024-001
    甲方：ABC科技有限公司
    乙方：XYZ服务有限公司
    签订日期：2024年3月15日
    合同金额：¥100,000.00
    项目名称：软件开发项目
    """


@pytest.fixture
def sample_field_mapping():
    """Sample field mapping for testing."""
    return {
        "合同编号": "B2",
        "甲方": "B3",
        "乙方": "B4",
        "签订日期": "B5",
        "合同金额": "B6",
        "项目名称": "B7",
    }


@pytest.fixture
def mock_deepseek_api_key():
    """Mock DeepSeek API key for testing (can be overridden by environment variable)."""
    return os.getenv("TEST_DEEPSEEK_API_KEY", "sk-test-key-for-testing-only")


# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]