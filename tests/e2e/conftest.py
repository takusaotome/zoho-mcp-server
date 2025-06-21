"""Pytest configuration for E2E tests."""

import pytest
import os
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    """Create test client for the application."""
    # Import here to avoid circular imports
    from server.main import app
    
    # Configure test environment
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    return TestClient(app)


@pytest.fixture(scope="session")
def authenticated_client(client):
    """Create authenticated test client."""
    # In a real implementation, this would set up authentication
    # For now, we assume the client is properly configured
    return client


@pytest.fixture
def test_project_data():
    """Provide test project data."""
    return {
        "project_id": "test_project_e2e",
        "folder_id": "test_folder_e2e",
        "test_user": "e2e.test@example.com"
    }


@pytest.fixture
def test_task_data():
    """Provide test task data."""
    return {
        "name": "E2E Test Task",
        "owner": "e2e.tester@example.com",
        "due_date": "2025-12-31",
        "status": "open"
    }


@pytest.fixture
def test_file_data():
    """Provide test file data."""
    import base64
    
    mock_content = "# Test Document\n\nThis is a test document for E2E testing."
    return {
        "name": "test_document.md",
        "content_base64": base64.b64encode(mock_content.encode()).decode(),
        "mime_type": "text/markdown"
    }


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line(
        "markers", "e2e: marks tests as end-to-end tests"
    )
    config.addinivalue_line(
        "markers", "slow: marks tests as slow running"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "performance: marks tests as performance tests"
    )
    config.addinivalue_line(
        "markers", "stress: marks tests as stress tests"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers based on file location."""
    for item in items:
        # Add e2e marker to all tests in e2e directory
        if "e2e" in str(item.fspath):
            item.add_marker(pytest.mark.e2e)
        
        # Add slow marker to performance tests
        if "performance" in str(item.fspath) or "locust" in str(item.fspath):
            item.add_marker(pytest.mark.slow)
        
        # Add integration marker to integration tests
        if "integration" in str(item.fspath):
            item.add_marker(pytest.mark.integration)


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """Setup test environment before running tests."""
    # Set test environment variables
    test_env_vars = {
        "TESTING": "true",
        "LOG_LEVEL": "DEBUG",
        "ZOHO_TEST_PROJECT_ID": "test_project_123",
        "ZOHO_TEST_FOLDER_ID": "test_folder_123"
    }
    
    original_values = {}
    
    # Set test environment variables
    for key, value in test_env_vars.items():
        original_values[key] = os.environ.get(key)
        os.environ[key] = value
    
    yield
    
    # Restore original environment variables
    for key, original_value in original_values.items():
        if original_value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = original_value


@pytest.fixture
def mock_zoho_responses():
    """Provide mock Zoho API responses for testing."""
    return {
        "list_tasks_success": {
            "tasks": [
                {
                    "id": "task_001",
                    "name": "Test Task 1",
                    "status": "open",
                    "owner": "test@example.com",
                    "due_date": "2025-07-01"
                },
                {
                    "id": "task_002", 
                    "name": "Test Task 2",
                    "status": "closed",
                    "owner": "test2@example.com",
                    "due_date": "2025-06-15"
                }
            ],
            "total_count": 2
        },
        "create_task_success": {
            "task": {
                "id": "new_task_123",
                "name": "New Test Task",
                "status": "open",
                "created_time": "2025-06-21T10:00:00Z"
            }
        },
        "project_summary_success": {
            "project_id": "test_project_123",
            "completion_rate": 75.0,
            "total_tasks": 4,
            "completed_tasks": 3,
            "overdue_tasks": 0,
            "period": "month"
        },
        "search_files_success": {
            "files": [
                {
                    "id": "file_001",
                    "name": "test_document.md",
                    "path": "/projects/test/docs/",
                    "size": 1024,
                    "modified_time": "2025-06-21T09:00:00Z"
                }
            ],
            "total_count": 1
        },
        "upload_success": {
            "file": {
                "id": "uploaded_file_456",
                "name": "review_sheet.xlsx",
                "upload_time": "2025-06-21T11:00:00Z"
            }
        }
    }


@pytest.fixture
def performance_thresholds():
    """Provide performance testing thresholds."""
    return {
        "max_response_time_ms": 500,
        "max_error_rate_percent": 0.1,
        "min_success_rate_percent": 99.9,
        "max_concurrent_users": 100,
        "max_requests_per_second": 100
    }


# Custom test result reporting
def pytest_runtest_makereport(item, call):
    """Customize test result reporting."""
    if "e2e" in str(item.fspath) and call.when == "call":
        # Add custom reporting for E2E tests
        if call.excinfo is None:
            # Test passed
            print(f"\n✅ E2E Test PASSED: {item.name}")
        else:
            # Test failed
            print(f"\n❌ E2E Test FAILED: {item.name}")
            print(f"   Error: {call.excinfo.value}")


# Skip certain tests based on environment
def pytest_runtest_setup(item):
    """Setup individual test runs."""
    # Skip real API tests unless explicitly enabled
    if item.get_closest_marker("real_api"):
        if not os.getenv("ZOHO_E2E_TESTS_ENABLED", "false").lower() == "true":
            pytest.skip("Real API E2E tests disabled")
    
    # Skip slow tests in CI unless explicitly requested
    if item.get_closest_marker("slow"):
        if os.getenv("CI") and not os.getenv("RUN_SLOW_TESTS"):
            pytest.skip("Slow tests skipped in CI")
    
    # Skip stress tests unless explicitly requested
    if item.get_closest_marker("stress"):
        if not os.getenv("RUN_STRESS_TESTS"):
            pytest.skip("Stress tests skipped")


# Test data cleanup
@pytest.fixture(autouse=True)
def cleanup_test_data():
    """Cleanup test data after each test."""
    yield
    
    # In a real implementation, this would clean up:
    # - Created tasks
    # - Uploaded files
    # - Test projects
    # - Cache entries
    pass