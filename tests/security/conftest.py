"""Security tests configuration and fixtures."""

import os
import pytest
from unittest.mock import Mock, AsyncMock

# Set security test environment
os.environ["ENVIRONMENT"] = "security_test"
os.environ["ALLOWED_IPS"] = "127.0.0.1,::1,testclient,unknown,0.0.0.0/0"
os.environ["JWT_SECRET"] = "security_test_jwt_secret_key_32_chars_long_for_testing"


@pytest.fixture
def security_client():
    """Create test client with security-specific configuration."""
    from fastapi.testclient import TestClient
    from server.main import create_app
    
    app = create_app()
    return TestClient(app)


@pytest.fixture
def malicious_payloads():
    """Common malicious payloads for security testing."""
    return {
        "sql_injection": [
            "'; DROP TABLE users; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM admin",
            "; DELETE FROM projects WHERE 1=1; --"
        ],
        "xss": [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert('XSS')",
            "<svg onload=alert('XSS')>"
        ],
        "command_injection": [
            "; cat /etc/passwd",
            "| whoami",
            "&& rm -rf /",
            "`id`",
            "$(uname -a)"
        ],
        "path_traversal": [
            "../../etc/passwd",
            "../../../root/.ssh/id_rsa",
            "..\\..\\windows\\system32\\drivers\\etc\\hosts",
            "....//....//etc/passwd"
        ],
        "nosql_injection": [
            {"$ne": ""},
            {"$gt": ""},
            {"$where": "this.password"},
            {"$regex": ".*"}
        ]
    }


@pytest.fixture
def mock_security_zoho_api():
    """Mock Zoho API for security testing."""
    mock = Mock()
    
    # Mock secure responses
    mock.get = AsyncMock(return_value={
        "tasks": [
            {
                "id": "secure_task_001",
                "name": "Security Test Task",
                "status": "open",
                "owner": {"name": "Security Tester"},
                "due_date": "2025-07-01"
            }
        ]
    })
    
    mock.post = AsyncMock(return_value={
        "task": {
            "id": "new_secure_task",
            "name": "New Security Test Task"
        }
    })
    
    mock.put = AsyncMock(return_value={"status": "updated"})
    mock.delete = AsyncMock(return_value={"status": "deleted"})
    
    return mock


@pytest.fixture
def attack_vectors():
    """Common attack vectors for security testing."""
    return {
        "buffer_overflow": "A" * 10000,
        "format_string": "%s%s%s%s%s%s%s%s%s%s%s%s",
        "null_byte": "test\x00admin",
        "unicode_bypass": "test\u202e\u202dadmin",
        "ldap_injection": "admin)(&(password=*))",
        "xml_bomb": """<?xml version="1.0"?>
<!DOCTYPE lolz [
  <!ENTITY lol "lol">
  <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
]>
<lolz>&lol2;</lolz>""",
        "jwt_none_alg": {
            "alg": "none",
            "typ": "JWT"
        }
    }


@pytest.fixture
def security_headers():
    """Security-related HTTP headers for testing."""
    return {
        "content_security_policy": "default-src 'self'",
        "x_frame_options": "DENY",
        "x_content_type_options": "nosniff",
        "x_xss_protection": "1; mode=block",
        "strict_transport_security": "max-age=31536000; includeSubDomains",
        "referrer_policy": "strict-origin-when-cross-origin"
    }


@pytest.fixture
def penetration_test_data():
    """Data for penetration testing scenarios."""
    return {
        "users": [
            {"id": "admin", "role": "admin", "password": "admin123"},
            {"id": "user", "role": "user", "password": "user123"},
            {"id": "guest", "role": "guest", "password": "guest123"}
        ],
        "projects": [
            {"id": "public_project", "access": "public"},
            {"id": "private_project", "access": "private"},
            {"id": "admin_project", "access": "admin_only"}
        ],
        "sensitive_files": [
            {"id": "config.json", "sensitive": True},
            {"id": "secrets.env", "sensitive": True},
            {"id": "public_readme.txt", "sensitive": False}
        ]
    }


@pytest.fixture
def timing_attack_detector():
    """Utility for detecting timing attack vulnerabilities."""
    import time
    import statistics
    
    class TimingDetector:
        def __init__(self):
            self.measurements = []
        
        def measure(self, func, *args, **kwargs):
            """Measure execution time of a function."""
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                return result
            except Exception as e:
                return e
            finally:
                end = time.perf_counter()
                self.measurements.append(end - start)
        
        def has_timing_difference(self, threshold=0.01):
            """Check if there's a significant timing difference."""
            if len(self.measurements) < 2:
                return False
            
            mean_time = statistics.mean(self.measurements)
            std_dev = statistics.stdev(self.measurements) if len(self.measurements) > 1 else 0
            
            # Check if any measurement is significantly different
            for measurement in self.measurements:
                if abs(measurement - mean_time) > threshold:
                    return True
            return False
        
        def reset(self):
            """Reset measurements."""
            self.measurements = []
    
    return TimingDetector()


@pytest.fixture
def security_test_config():
    """Configuration for security tests."""
    return {
        "max_request_size": 1024 * 1024,  # 1MB
        "rate_limit": 100,  # requests per minute
        "jwt_expiry": 3600,  # 1 hour
        "allowed_file_types": [".txt", ".json", ".md", ".csv"],
        "blocked_file_types": [".exe", ".sh", ".php", ".asp", ".jsp"],
        "max_file_size": 10 * 1024 * 1024,  # 10MB
        "sensitive_headers": ["authorization", "x-api-key", "cookie"],
        "security_headers_required": [
            "x-content-type-options",
            "x-frame-options", 
            "x-xss-protection"
        ]
    }


# Security test markers
def pytest_configure(config):
    """Configure pytest with security test markers."""
    config.addinivalue_line(
        "markers", "security: mark test as a security test"
    )
    config.addinivalue_line(
        "markers", "slow_security: mark test as a slow security test"
    )
    config.addinivalue_line(
        "markers", "penetration: mark test as a penetration test"
    )
    config.addinivalue_line(
        "markers", "vulnerability: mark test as checking for specific vulnerability"
    )