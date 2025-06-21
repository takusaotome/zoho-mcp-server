"""Pytest configuration and fixtures for Zoho MCP Server tests."""

import asyncio
import os
from collections.abc import AsyncGenerator, Generator
from unittest.mock import AsyncMock, Mock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient

from server.main import create_app

# Set test environment
os.environ["ENVIRONMENT"] = "test"
os.environ["REDIS_URL"] = "redis://localhost:6379/15"  # Use different DB for tests
os.environ["ALLOWED_IPS"] = "127.0.0.1,::1,testclient,unknown,0.0.0.0/0"  # Allow test client IPs


@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def app():
    """Create FastAPI test application."""
    return create_app()


@pytest.fixture
def client(app) -> TestClient:
    """Create test client."""
    return TestClient(app)


@pytest_asyncio.fixture
async def async_client(app) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def mock_redis():
    """Mock Redis client."""
    mock = Mock()
    mock.get = AsyncMock(return_value=None)
    mock.set = AsyncMock(return_value=True)
    mock.setex = AsyncMock(return_value=True)
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=0)
    mock.ttl = AsyncMock(return_value=-1)
    mock.expire = AsyncMock(return_value=True)
    mock.ping = AsyncMock(return_value=True)
    return mock


@pytest.fixture
def mock_zoho_oauth():
    """Mock Zoho OAuth client."""
    mock = Mock()
    mock.get_access_token = AsyncMock(return_value="test_access_token")
    mock.is_token_valid = AsyncMock(return_value=True)
    mock.get_token_info = AsyncMock(return_value={"valid": True})
    return mock


@pytest.fixture
def mock_zoho_api():
    """Mock Zoho API client."""
    mock = Mock()

    # Mock API responses
    mock.get = AsyncMock(return_value={
        "tasks": [
            {
                "id": "task_001",
                "name": "Test Task",
                "status": "open",
                "owner": {"name": "Test User"},
                "due_date": "2025-07-01",
                "created_time": "2025-06-21T10:00:00Z",
                "link": {"self": {"url": "https://test.com/task/001"}}
            }
        ]
    })

    mock.post = AsyncMock(return_value={
        "task": {
            "id": "new_task_123",
            "name": "New Test Task",
            "link": {"self": {"url": "https://test.com/task/123"}}
        }
    })

    mock.put = AsyncMock(return_value={"status": "updated"})
    mock.delete = AsyncMock(return_value={"status": "deleted"})
    mock.health_check = AsyncMock(return_value=True)

    return mock


@pytest.fixture
def sample_task_data():
    """Sample task data for tests."""
    return {
        "id": "task_001",
        "name": "Test Task",
        "status": "open",
        "owner": "test@example.com",
        "due_date": "2025-07-01",
        "created_time": "2025-06-21T10:00:00Z",
        "description": "Test task description",
        "link": {"self": {"url": "https://test.com/task/001"}}
    }


@pytest.fixture
def sample_file_data():
    """Sample file data for tests."""
    return {
        "id": "file_001",
        "attributes": {
            "name": "test_file.txt",
            "type": "file",
            "size_in_bytes": 1024,
            "created_time": "2025-06-21T10:00:00Z",
            "modified_time": "2025-06-21T11:00:00Z"
        }
    }


@pytest.fixture
def mcp_request_base():
    """Base MCP request structure."""
    return {
        "jsonrpc": "2.0",
        "method": "callTool",
        "id": "test_request_001"
    }


@pytest.fixture
def jwt_token():
    """Valid JWT token for testing."""
    from server.auth.jwt_handler import jwt_handler
    return jwt_handler.create_access_token("test_user")


@pytest.fixture
def auth_headers(jwt_token):
    """Authentication headers for tests."""
    return {"Authorization": f"Bearer {jwt_token}"}


# Test data factories
class TaskFactory:
    """Factory for creating test task data."""

    @staticmethod
    def create(
        task_id: str = "test_task_001",
        name: str = "Test Task",
        status: str = "open",
        **kwargs
    ) -> dict:
        """Create task data."""
        return {
            "id": task_id,
            "name": name,
            "status": status,
            "owner": kwargs.get("owner", "test@example.com"),
            "due_date": kwargs.get("due_date", "2025-07-01"),
            "created_time": kwargs.get("created_time", "2025-06-21T10:00:00Z"),
            "description": kwargs.get("description", "Test description"),
            **kwargs
        }


class FileFactory:
    """Factory for creating test file data."""

    @staticmethod
    def create(
        file_id: str = "test_file_001",
        name: str = "test_file.txt",
        **kwargs
    ) -> dict:
        """Create file data."""
        return {
            "id": file_id,
            "attributes": {
                "name": name,
                "type": kwargs.get("type", "file"),
                "size_in_bytes": kwargs.get("size", 1024),
                "created_time": kwargs.get("created_time", "2025-06-21T10:00:00Z"),
                "modified_time": kwargs.get("modified_time", "2025-06-21T11:00:00Z"),
                **kwargs
            }
        }


@pytest.fixture
def task_factory():
    """Task factory fixture."""
    return TaskFactory


@pytest.fixture
def file_factory():
    """File factory fixture."""
    return FileFactory


# Async test markers
pytestmark = pytest.mark.asyncio
