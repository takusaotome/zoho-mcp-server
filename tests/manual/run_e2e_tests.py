#!/usr/bin/env python3
"""
Simple E2E test runner without pytest dependency issues.
"""

import os
import sys
import time
from datetime import datetime
from typing import Any

import httpx


class E2ETestRunner:
    """Simple E2E test runner."""

    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.test_results = []
        self.passed = 0
        self.failed = 0

    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def assert_equal(self, actual, expected, message: str = ""):
        """Simple assertion."""
        if actual == expected:
            self.log(f"✅ PASS: {message}")
            self.passed += 1
            return True
        else:
            self.log(f"❌ FAIL: {message} - Expected: {expected}, Got: {actual}", "ERROR")
            self.failed += 1
            return False

    def assert_contains(self, container, item, message: str = ""):
        """Assert that container contains item."""
        if item in container:
            self.log(f"✅ PASS: {message}")
            self.passed += 1
            return True
        else:
            self.log(f"❌ FAIL: {message} - '{item}' not found in {container}", "ERROR")
            self.failed += 1
            return False

    def assert_status_code(self, response, expected_code: int, message: str = ""):
        """Assert HTTP status code."""
        return self.assert_equal(response.status_code, expected_code,
                                f"Status code check: {message}")

    def make_mcp_request(self, method: str, params: dict[str, Any] = None,
                        request_id: str = "test_001") -> dict[str, Any]:
        """Make MCP JSON-RPC request."""
        request_data = {
            "jsonrpc": "2.0",
            "method": method,
            "id": request_id
        }

        if params:
            request_data["params"] = params

        return request_data

    def test_health_endpoint(self):
        """Test health endpoint."""
        self.log("Testing health endpoint...")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/health")

                self.assert_status_code(response, 200, "Health endpoint")

                if response.status_code == 200:
                    data = response.json()
                    self.assert_equal(data.get("status"), "healthy", "Health status")
                    self.assert_contains(data, "version", "Version in health response")

        except Exception as e:
            self.log(f"❌ FAIL: Health endpoint test failed - {e}", "ERROR")
            self.failed += 1

    def test_manifest_endpoint(self):
        """Test manifest endpoint."""
        self.log("Testing manifest endpoint...")

        try:
            with httpx.Client(timeout=10.0) as client:
                response = client.get(f"{self.base_url}/manifest.json")

                self.assert_status_code(response, 200, "Manifest endpoint")

                if response.status_code == 200:
                    data = response.json()
                    self.assert_equal(data.get("name"), "zoho-mcp-server", "Manifest name")
                    self.assert_contains(data, "tools", "Tools in manifest")

                    if "tools" in data:
                        tools = data["tools"]
                        tool_names = [tool.get("name", "") for tool in tools]

                        expected_tools = ["listTasks", "createTask", "updateTask",
                                        "getProjectSummary", "getTaskDetail"]
                        for tool_name in expected_tools:
                            self.assert_contains(tool_names, tool_name,
                                               f"Tool '{tool_name}' in manifest")

        except Exception as e:
            self.log(f"❌ FAIL: Manifest endpoint test failed - {e}", "ERROR")
            self.failed += 1

    def test_mcp_ping(self):
        """Test MCP ping method."""
        self.log("Testing MCP ping method...")

        try:
            with httpx.Client(timeout=10.0) as client:
                request_data = self.make_mcp_request("ping", request_id="ping_test")

                response = client.post(f"{self.base_url}/mcp", json=request_data)

                self.assert_status_code(response, 200, "MCP ping")

                if response.status_code == 200:
                    data = response.json()
                    self.assert_equal(data.get("jsonrpc"), "2.0", "JSON-RPC version")
                    self.assert_equal(data.get("id"), "ping_test", "Request ID")

                    if "result" in data:
                        result = data["result"]
                        self.assert_equal(result.get("message"), "pong", "Ping response")

        except Exception as e:
            self.log(f"❌ FAIL: MCP ping test failed - {e}", "ERROR")
            self.failed += 1

    def test_mcp_list_tools(self):
        """Test MCP listTools method."""
        self.log("Testing MCP listTools method...")

        try:
            with httpx.Client(timeout=10.0) as client:
                request_data = self.make_mcp_request("listTools", request_id="list_tools_test")

                response = client.post(f"{self.base_url}/mcp", json=request_data)

                self.assert_status_code(response, 200, "MCP listTools")

                if response.status_code == 200:
                    data = response.json()
                    self.assert_equal(data.get("jsonrpc"), "2.0", "JSON-RPC version")
                    self.assert_equal(data.get("id"), "list_tools_test", "Request ID")
                    self.assert_contains(data, "result", "Result in listTools response")

                    if "result" in data:
                        result = data["result"]
                        self.assert_contains(result, "tools", "Tools in listTools result")

        except Exception as e:
            self.log(f"❌ FAIL: MCP listTools test failed - {e}", "ERROR")
            self.failed += 1

    def test_mcp_call_tool_list_tasks(self):
        """Test MCP callTool with listTasks."""
        self.log("Testing MCP callTool listTasks...")

        try:
            with httpx.Client(timeout=10.0) as client:
                params = {
                    "name": "listTasks",
                    "arguments": {
                        "project_id": "test_project_123",
                        "status": "open"
                    }
                }
                request_data = self.make_mcp_request("callTool", params, "list_tasks_test")

                response = client.post(f"{self.base_url}/mcp", json=request_data)

                self.assert_status_code(response, 200, "MCP callTool listTasks")

                if response.status_code == 200:
                    data = response.json()
                    self.assert_equal(data.get("jsonrpc"), "2.0", "JSON-RPC version")
                    self.assert_equal(data.get("id"), "list_tasks_test", "Request ID")

                    # Response should contain either result or error
                    has_result_or_error = "result" in data or "error" in data
                    if not has_result_or_error:
                        self.log("❌ FAIL: No result or error in response", "ERROR")
                        self.failed += 1
                    else:
                        self.log("✅ PASS: Response contains result or error")
                        self.passed += 1

        except Exception as e:
            self.log(f"❌ FAIL: MCP callTool listTasks test failed - {e}", "ERROR")
            self.failed += 1

    def test_mcp_invalid_method(self):
        """Test MCP with invalid method."""
        self.log("Testing MCP with invalid method...")

        try:
            with httpx.Client(timeout=10.0) as client:
                request_data = self.make_mcp_request("invalidMethod", request_id="invalid_test")

                response = client.post(f"{self.base_url}/mcp", json=request_data)

                self.assert_status_code(response, 200, "MCP invalid method (should return 200)")

                if response.status_code == 200:
                    data = response.json()
                    self.assert_equal(data.get("jsonrpc"), "2.0", "JSON-RPC version")
                    self.assert_contains(data, "error", "Error in invalid method response")

                    if "error" in data:
                        error = data["error"]
                        # Should return method not found error
                        expected_code = -32601
                        self.assert_equal(error.get("code"), expected_code,
                                        "Method not found error code")

        except Exception as e:
            self.log(f"❌ FAIL: MCP invalid method test failed - {e}", "ERROR")
            self.failed += 1

    def test_invalid_json_request(self):
        """Test invalid JSON request."""
        self.log("Testing invalid JSON request...")

        try:
            with httpx.Client(timeout=10.0) as client:
                # Send invalid JSON
                response = client.post(f"{self.base_url}/mcp",
                                     content="invalid json",
                                     headers={"Content-Type": "application/json"})

                # Should return 422 for validation error
                if response.status_code in [400, 422]:
                    self.log("✅ PASS: Invalid JSON properly rejected")
                    self.passed += 1
                else:
                    self.log(f"❌ FAIL: Expected 400/422, got {response.status_code}", "ERROR")
                    self.failed += 1

        except Exception as e:
            self.log(f"❌ FAIL: Invalid JSON test failed - {e}", "ERROR")
            self.failed += 1

    def run_workflow_test(self):
        """Test basic workflow scenario."""
        self.log("Testing basic workflow scenario...")

        try:
            with httpx.Client(timeout=30.0) as client:
                # Step 1: List existing tasks
                params1 = {
                    "name": "listTasks",
                    "arguments": {"project_id": "workflow_test_project"}
                }
                request1 = self.make_mcp_request("callTool", params1, "workflow_step_1")
                response1 = client.post(f"{self.base_url}/mcp", json=request1)

                self.assert_status_code(response1, 200, "Workflow step 1: List tasks")

                # Step 2: Create a new task
                params2 = {
                    "name": "createTask",
                    "arguments": {
                        "project_id": "workflow_test_project",
                        "name": f"E2E Test Task {datetime.now().isoformat()}",
                        "owner": "e2e.test@example.com",
                        "due_date": "2025-12-31"
                    }
                }
                request2 = self.make_mcp_request("callTool", params2, "workflow_step_2")
                response2 = client.post(f"{self.base_url}/mcp", json=request2)

                self.assert_status_code(response2, 200, "Workflow step 2: Create task")

                # Step 3: Get project summary
                params3 = {
                    "name": "getProjectSummary",
                    "arguments": {
                        "project_id": "workflow_test_project",
                        "period": "month"
                    }
                }
                request3 = self.make_mcp_request("callTool", params3, "workflow_step_3")
                response3 = client.post(f"{self.base_url}/mcp", json=request3)

                self.assert_status_code(response3, 200, "Workflow step 3: Get summary")

                self.log("✅ PASS: Basic workflow completed successfully")
                self.passed += 1

        except Exception as e:
            self.log(f"❌ FAIL: Workflow test failed - {e}", "ERROR")
            self.failed += 1

    def check_server_running(self) -> bool:
        """Check if server is running."""
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.get(f"{self.base_url}/health")
                return response.status_code == 200
        except Exception:
            return False

    def run_all_tests(self):
        """Run all E2E tests."""
        self.log("Starting E2E Test Suite...")
        self.log(f"Target server: {self.base_url}")

        # Check if server is running
        if not self.check_server_running():
            self.log("❌ Server is not running or not accessible", "ERROR")
            self.log("Please start the server with: uvicorn server.main:app --host 0.0.0.0 --port 8000")
            return False

        self.log("✅ Server is running and accessible")

        start_time = time.time()

        # Basic endpoint tests
        self.test_health_endpoint()
        self.test_manifest_endpoint()

        # MCP protocol tests
        self.test_mcp_ping()
        self.test_mcp_list_tools()
        self.test_mcp_call_tool_list_tasks()

        # Error handling tests
        self.test_mcp_invalid_method()
        self.test_invalid_json_request()

        # Workflow tests
        self.run_workflow_test()

        end_time = time.time()
        duration = end_time - start_time

        # Summary
        total_tests = self.passed + self.failed
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0

        self.log("=" * 60)
        self.log("E2E Test Suite Results")
        self.log("=" * 60)
        self.log(f"Total Tests: {total_tests}")
        self.log(f"Passed: {self.passed}")
        self.log(f"Failed: {self.failed}")
        self.log(f"Success Rate: {success_rate:.1f}%")
        self.log(f"Duration: {duration:.2f}s")

        if self.failed == 0:
            self.log("🎉 All tests passed!")
            return True
        else:
            self.log(f"💥 {self.failed} test(s) failed")
            return False


def main():
    """Main function."""
    # Set environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    os.environ["ZOHO_E2E_TESTS_ENABLED"] = "false"

    # Parse command line arguments
    base_url = "http://localhost:8001"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]

    # Run tests
    runner = E2ETestRunner(base_url)
    success = runner.run_all_tests()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
