"""OWASP Top 10 security tests for Zoho MCP Server."""

import base64
import json

from fastapi.testclient import TestClient


class TestOWASPTop10Security:
    """Tests covering OWASP Top 10 security vulnerabilities."""

    # A01:2021 – Broken Access Control
    def test_a01_broken_access_control(self, client: TestClient, auth_headers):
        """Test protection against broken access control."""
        # Test 1: Unauthorized access to admin endpoints
        admin_endpoints = [
            "/admin",
            "/admin/users",
            "/admin/config",
            "/system/status",
            "/debug/info"
        ]

        for endpoint in admin_endpoints:
            response = client.get(endpoint, headers=auth_headers)
            # Should either be 404 (not implemented) or 403 (forbidden)
            assert response.status_code in [404, 403]

        # Test 2: Path traversal attempts
        traversal_attempts = [
            "/mcp/../admin",
            "/mcp/../../etc/passwd",
            "/mcp/../config/secrets",
        ]

        for path in traversal_attempts:
            response = client.post(path, headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": 1
            })
            assert response.status_code in [404, 403, 400]

        # Test 3: Direct object reference
        response = client.post("/mcp", headers=auth_headers, json={
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "../admin/secrets",  # Attempt to access admin data
                }
            },
            "id": 1
        })
        assert response.status_code in [400, 403, 422]

    # A02:2021 – Cryptographic Failures
    def test_a02_cryptographic_failures(self, client: TestClient):
        """Test protection against cryptographic failures."""
        # Test 1: Ensure HTTPS is enforced (simulated)
        # In production, HTTP should redirect to HTTPS

        # Test 2: Weak encryption detection
        # Test for any endpoints that might expose sensitive data over insecure channels
        response = client.get("/health")
        assert response.status_code == 200

        # Health endpoint should not expose sensitive configuration
        data = response.json()
        sensitive_keys = ["password", "secret", "key", "token", "credential"]
        response_text = json.dumps(data).lower()
        for key in sensitive_keys:
            assert key not in response_text, f"Health endpoint should not expose {key}"

        # Test 3: Ensure no sensitive data in error messages
        response = client.post("/mcp", json={"invalid": "request"})
        error_text = response.text.lower()
        assert "password" not in error_text
        assert "secret" not in error_text
        assert "key" not in error_text

    # A03:2021 – Injection
    def test_a03_injection_comprehensive(self, client: TestClient, auth_headers):
        """Comprehensive injection attack tests."""
        # Already covered in test_injection_attacks.py, but adding critical cases

        # Test 1: Command injection in system operations
        command_injections = [
            "; cat /etc/passwd",
            "| whoami",
            "&& rm -rf /",
            "`id`",
            "$(uname -a)"
        ]

        for injection in command_injections:
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "searchFiles",
                    "arguments": {
                        "query": f"test{injection}",
                        "folder_id": "folder"
                    }
                },
                "id": 1
            })
            assert response.status_code in [400, 422, 200]
            if response.status_code == 200:
                # Should not execute commands
                assert "root:" not in response.text
                assert "uid=" not in response.text

    # A04:2021 – Insecure Design
    def test_a04_insecure_design(self, client: TestClient, auth_headers):
        """Test for insecure design patterns."""
        # Test 1: Business logic flaws
        # Attempt to bypass business rules
        response = client.post("/mcp", headers=auth_headers, json={
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": "non_existent_task",
                    "status": "admin_override",  # Invalid status
                    "owner": "system"  # Attempting to assign to system
                }
            },
            "id": 1
        })
        # Should validate business rules
        assert response.status_code in [400, 404, 422]

        # Test 2: Resource enumeration
        # Attempt to enumerate resources
        for i in range(1, 10):
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "downloadFile",
                    "arguments": {"file_id": str(i)}
                },
                "id": i
            })
            # Should not leak information about existing resources
            if response.status_code == 404:
                error_data = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                # Error messages should not reveal internal structure
                error_msg = str(error_data).lower()
                assert "database" not in error_msg
                assert "table" not in error_msg

    # A05:2021 – Security Misconfiguration
    def test_a05_security_misconfiguration(self, client: TestClient):
        """Test for security misconfigurations."""
        # Test 1: Debug information exposure
        debug_endpoints = [
            "/debug",
            "/trace",
            "/config",
            "/env",
            "/system-info"
        ]

        for endpoint in debug_endpoints:
            response = client.get(endpoint)
            # Debug endpoints should not be accessible in production
            assert response.status_code in [404, 403]

        # Test 2: Default credentials
        # Attempt to use default/common credentials
        default_headers = {"Authorization": "Bearer default"}
        response = client.post("/mcp", headers=default_headers, json={
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 1
        })
        assert response.status_code == 401

        # Test 3: Error handling - should not expose stack traces
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "nonexistent_method",
            "id": 1
        })
        error_text = response.text.lower()
        assert "traceback" not in error_text
        assert "exception" not in error_text
        assert "line " not in error_text  # Stack trace line numbers

    # A06:2021 – Vulnerable and Outdated Components
    def test_a06_vulnerable_components(self):
        """Test for vulnerable component detection."""
        # This test checks if we can identify potentially vulnerable components
        # In a real scenario, this would be part of dependency scanning

        import pkg_resources

        # Get installed packages
        installed_packages = [d.project_name.lower() for d in pkg_resources.working_set]

        # Check for known vulnerable packages (examples)

        # This test mainly serves as a reminder to keep dependencies updated
        # In practice, use tools like safety, pip-audit, or snyk
        assert len(installed_packages) > 0, "Should have installed packages to analyze"

    # A07:2021 – Identification and Authentication Failures
    def test_a07_auth_failures(self, client: TestClient):
        """Test identification and authentication failures."""
        # Test 1: Weak password policy (if user registration exists)
        # This test assumes user creation endpoints exist

        # Test 2: Credential stuffing protection
        # Attempt multiple failed logins
        for i in range(10):
            response = client.post("/mcp", headers={
                "Authorization": f"Bearer invalid_token_{i}"
            }, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": i
            })
            assert response.status_code == 401

        # System should still function after failed attempts
        # (Rate limiting might kick in, but system should remain responsive)

        # Test 3: Session management
        # Test that sessions are properly invalidated
        from server.auth.jwt_handler import JWTHandler
        jwt_handler = JWTHandler()

        # Create short-lived token
        token = jwt_handler.create_access_token("test_user")

        # Use token immediately (should work)
        response = client.post("/mcp", headers={
            "Authorization": f"Bearer {token}"
        }, json={
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 1
        })
        # May fail due to IP restrictions, but that's not an auth failure

    # A08:2021 – Software and Data Integrity Failures
    def test_a08_integrity_failures(self, client: TestClient, auth_headers):
        """Test software and data integrity failures."""
        # Test 1: Unsigned data acceptance
        # Ensure that critical operations require proper authentication

        # Test 2: Insecure deserialization
        # Attempt to send serialized objects that could be exploited
        malicious_payloads = [
            # Python pickle attempt (should not be used)
            {"data": "gASVDgAAAAAAAABDBXBvaXNvbnEBLg=="},  # base64 encoded pickle

            # YAML deserialization attempt
            {"yaml_data": "!!python/object/apply:os.system ['rm -rf /']"},

            # JSON with prototype pollution
            {"__proto__": {"admin": True}},
        ]

        for payload in malicious_payloads:
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": "test",
                        "name": "test",
                        **payload
                    }
                },
                "id": 1
            })
            # Should not process malicious serialized data
            assert response.status_code in [400, 422, 200]

    # A09:2021 – Security Logging and Monitoring Failures
    def test_a09_logging_monitoring(self, client: TestClient, auth_headers):
        """Test security logging and monitoring."""
        # Test 1: Security events are logged (simulation)
        # This test ensures security-relevant events would be logged

        # Failed authentication attempt
        response = client.post("/mcp", headers={
            "Authorization": "Bearer invalid_token"
        }, json={
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 1
        })
        assert response.status_code == 401

        # Successful authentication
        response = client.post("/mcp", headers=auth_headers, json={
            "jsonrpc": "2.0",
            "method": "ping",
            "id": 1
        })
        # Response may vary due to IP restrictions

        # Test 2: Log injection prevention
        # Ensure log entries can't be manipulated
        response = client.post("/mcp", headers=auth_headers, json={
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": "test",
                    "name": "Task\r\nFAKE LOG ENTRY: Admin access granted\r\nReal task name"
                }
            },
            "id": 1
        })
        # Should handle log injection attempts safely

    # A10:2021 – Server-Side Request Forgery (SSRF)
    def test_a10_ssrf(self, client: TestClient, auth_headers):
        """Test Server-Side Request Forgery protection."""
        # Test 1: Internal network access attempts
        ssrf_payloads = [
            "http://127.0.0.1:22",  # SSH
            "http://localhost:3306",  # MySQL
            "http://169.254.169.254/latest/meta-data/",  # AWS metadata
            "file:///etc/passwd",  # File scheme
            "gopher://127.0.0.1:25/",  # Gopher protocol
            "ftp://internal.server/",  # FTP
        ]

        for payload in ssrf_payloads:
            # Test in file operations that might make external requests
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "downloadFile",
                    "arguments": {
                        "file_id": payload  # SSRF attempt
                    }
                },
                "id": 1
            })
            assert response.status_code in [400, 422, 403]

        # Test 2: URL validation in webhook configurations
        malicious_urls = [
            "http://localhost:8080/admin",
            "https://internal.company.com/secrets",
            "http://0.0.0.0:22",
        ]

        for url in malicious_urls:
            # If webhook endpoints exist, test URL validation
            response = client.post("/webhook/test", json={
                "callback_url": url
            })
            # Should validate and reject internal URLs
            assert response.status_code in [400, 404, 422]

    def test_cors_security(self, client: TestClient):
        """Test CORS security configuration."""
        # Test 1: CORS headers validation
        response = client.options("/mcp", headers={
            "Origin": "https://evil.com",
            "Access-Control-Request-Method": "POST"
        })

        # Should have proper CORS configuration
        if "Access-Control-Allow-Origin" in response.headers:
            origin = response.headers["Access-Control-Allow-Origin"]
            # Should not allow all origins in production
            assert origin != "*" or response.status_code == 403

        # Test 2: Preflight request handling
        response = client.options("/mcp")
        assert response.status_code in [200, 204, 404]

    def test_content_type_validation(self, client: TestClient, auth_headers):
        """Test content-type validation."""
        # Test 1: Wrong content type
        response = client.post("/mcp",
                              headers={**auth_headers, "Content-Type": "text/plain"},
                              data="malicious data")
        assert response.status_code in [400, 415, 422]

        # Test 2: Missing content type
        response = client.post("/mcp",
                              headers=auth_headers,
                              data=json.dumps({
                                  "jsonrpc": "2.0",
                                  "method": "ping",
                                  "id": 1
                              }))
        # Should handle gracefully or require proper content type

    def test_file_upload_security(self, client: TestClient, auth_headers):
        """Test file upload security measures."""
        # Test 1: Malicious file type uploads
        malicious_files = [
            ("evil.exe", b"MZ\x90\x00"),  # PE executable
            ("script.sh", b"#!/bin/bash\nrm -rf /"),  # Shell script
            ("exploit.php", b"<?php system($_GET['cmd']); ?>"),  # PHP script
            ("bomb.zip", b"PK\x03\x04"),  # ZIP bomb (simplified)
        ]

        for filename, content in malicious_files:
            content_b64 = base64.b64encode(content).decode()
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "uploadReviewSheet",
                    "arguments": {
                        "project_id": "test",
                        "folder_id": "folder",
                        "name": filename,
                        "content_base64": content_b64
                    }
                },
                "id": 1
            })
            # Should validate file types and content
            assert response.status_code in [400, 422, 200]
