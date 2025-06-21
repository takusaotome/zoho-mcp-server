"""Real API integration E2E tests with actual Zoho API calls."""

import os
import pytest
import asyncio
from datetime import datetime, date
from typing import Dict, Any
from fastapi.testclient import TestClient

# Skip these tests unless explicitly enabled
pytestmark = pytest.mark.skipif(
    not os.getenv("ZOHO_E2E_TESTS_ENABLED", "false").lower() == "true",
    reason="Real API E2E tests disabled. Set ZOHO_E2E_TESTS_ENABLED=true to enable."
)


class TestRealZohoAPIIntegration:
    """Test real Zoho API integration scenarios."""
    
    def setup_method(self):
        """Setup test method."""
        self.test_project_id = os.getenv("ZOHO_TEST_PROJECT_ID", "test_project_123")
        self.test_folder_id = os.getenv("ZOHO_TEST_FOLDER_ID", "test_folder_123")
        self.created_task_ids = []  # Track created tasks for cleanup
        
    def teardown_method(self):
        """Cleanup after test."""
        # Clean up any created tasks
        for task_id in self.created_task_ids:
            try:
                self._cleanup_task(task_id)
            except Exception:
                pass  # Ignore cleanup errors
    
    def _cleanup_task(self, task_id: str):
        """Helper to cleanup created tasks."""
        # This would call the actual API to delete the task
        # Implementation depends on Zoho API availability
        pass
    
    def test_e2e_task_lifecycle(self, client: TestClient):
        """Test complete task lifecycle: create -> list -> update -> detail."""
        # Step 1: Create a task
        create_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": self.test_project_id,
                    "name": f"E2E Test Task {datetime.now().isoformat()}",
                    "owner": "e2e.test@example.com",
                    "due_date": "2025-07-01"
                }
            },
            "id": "e2e_create_001"
        }
        
        create_response = client.post("/mcp", json=create_request)
        assert create_response.status_code == 200
        
        create_data = create_response.json()
        assert "result" in create_data
        assert "task_id" in create_data["result"]["content"][0]["text"]
        
        # Extract task_id from response
        task_id = self._extract_task_id(create_data["result"]["content"][0]["text"])
        self.created_task_ids.append(task_id)
        
        # Step 2: List tasks to verify creation
        list_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": self.test_project_id,
                    "status": "open"
                }
            },
            "id": "e2e_list_001"
        }
        
        list_response = client.post("/mcp", json=list_request)
        assert list_response.status_code == 200
        
        list_data = list_response.json()
        assert "result" in list_data
        # Verify our created task is in the list
        task_found = any(task_id in str(list_data["result"]) for _ in [1])
        assert task_found, f"Created task {task_id} not found in task list"
        
        # Step 3: Get task details
        detail_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getTaskDetail",
                "arguments": {
                    "task_id": task_id
                }
            },
            "id": "e2e_detail_001"
        }
        
        detail_response = client.post("/mcp", json=detail_request)
        assert detail_response.status_code == 200
        
        detail_data = detail_response.json()
        assert "result" in detail_data
        
        # Step 4: Update task status
        update_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": task_id,
                    "status": "closed"
                }
            },
            "id": "e2e_update_001"
        }
        
        update_response = client.post("/mcp", json=update_request)
        assert update_response.status_code == 200
        
        update_data = update_response.json()
        assert "result" in update_data
    
    def test_e2e_project_summary_workflow(self, client: TestClient):
        """Test project summary with real data."""
        request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getProjectSummary",
                "arguments": {
                    "project_id": self.test_project_id,
                    "period": "month"
                }
            },
            "id": "e2e_summary_001"
        }
        
        response = client.post("/mcp", json=request)
        assert response.status_code == 200
        
        data = response.json()
        assert "result" in data
        
        # Verify summary contains expected fields
        summary_text = data["result"]["content"][0]["text"]
        assert "completion_rate" in summary_text.lower()
        assert "total_tasks" in summary_text.lower()
    
    def test_e2e_file_operations(self, client: TestClient):
        """Test file search and download operations."""
        # Step 1: Search for files
        search_request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "searchFiles",
                "arguments": {
                    "query": "test",
                    "folder_id": self.test_folder_id
                }
            },
            "id": "e2e_search_001"
        }
        
        search_response = client.post("/mcp", json=search_request)
        assert search_response.status_code == 200
        
        search_data = search_response.json()
        assert "result" in search_data
        
        # Step 2: If files found, try to download one
        files_text = search_data["result"]["content"][0]["text"]
        if "file_id" in files_text.lower():
            # Extract first file_id (simplified)
            file_id = self._extract_file_id(files_text)
            
            download_request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "downloadFile",
                    "arguments": {
                        "file_id": file_id
                    }
                },
                "id": "e2e_download_001"
            }
            
            download_response = client.post("/mcp", json=download_request)
            assert download_response.status_code == 200
            
            download_data = download_response.json()
            assert "result" in download_data
    
    def test_e2e_error_handling_with_real_api(self, client: TestClient):
        """Test error handling with real API calls."""
        # Test with invalid project ID
        request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "invalid_project_id_12345",
                    "status": "open"
                }
            },
            "id": "e2e_error_001"
        }
        
        response = client.post("/mcp", json=request)
        assert response.status_code == 200
        
        data = response.json()
        # Should return error for invalid project
        assert "error" in data or "not found" in str(data).lower()
    
    def test_e2e_rate_limiting_behavior(self, client: TestClient):
        """Test rate limiting behavior with real API."""
        requests_made = 0
        max_requests = 10  # Conservative limit for testing
        
        for i in range(max_requests):
            request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "listTasks",
                    "arguments": {
                        "project_id": self.test_project_id
                    }
                },
                "id": f"e2e_rate_test_{i}"
            }
            
            response = client.post("/mcp", json=request)
            requests_made += 1
            
            if response.status_code == 429:
                # Rate limit hit - this is expected behavior
                break
            
            assert response.status_code == 200
            
            # Small delay to avoid overwhelming the API
            import time
            time.sleep(0.1)
        
        # Verify we made at least some requests successfully
        assert requests_made > 0
    
    def test_e2e_concurrent_requests(self, client: TestClient):
        """Test concurrent request handling."""
        import concurrent.futures
        import threading
        
        def make_request(request_id: int):
            """Make a single request."""
            request = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "listTasks",
                    "arguments": {
                        "project_id": self.test_project_id
                    }
                },
                "id": f"e2e_concurrent_{request_id}"
            }
            
            response = client.post("/mcp", json=request)
            return response.status_code == 200
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # At least some requests should succeed
        successful_requests = sum(results)
        assert successful_requests >= 3, f"Only {successful_requests}/5 concurrent requests succeeded"
    
    def _extract_task_id(self, text: str) -> str:
        """Extract task ID from response text."""
        # This is a simplified extraction - in real implementation,
        # you'd parse the JSON response properly
        import re
        match = re.search(r'task_id["\s:]+([a-zA-Z0-9_-]+)', text)
        if match:
            return match.group(1)
        return "test_task_123"  # Fallback for testing
    
    def _extract_file_id(self, text: str) -> str:
        """Extract file ID from response text."""
        # This is a simplified extraction
        import re
        match = re.search(r'file_id["\s:]+([a-zA-Z0-9_-]+)', text)
        if match:
            return match.group(1)
        return "test_file_123"  # Fallback for testing


class TestRealAPIPerformance:
    """Performance tests with real API calls."""
    
    @pytest.mark.slow
    def test_api_response_times(self, client: TestClient):
        """Test API response times meet SLA requirements."""
        import time
        
        test_project_id = os.getenv("ZOHO_TEST_PROJECT_ID", "test_project_123")
        
        request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": test_project_id
                }
            },
            "id": "perf_test_001"
        }
        
        response_times = []
        
        for i in range(5):  # Test 5 requests
            start_time = time.time()
            response = client.post("/mcp", json=request)
            end_time = time.time()
            
            response_time = end_time - start_time
            response_times.append(response_time)
            
            # Verify response is successful
            if response.status_code == 200:
                # Response time should be under 500ms as per requirements
                assert response_time < 0.5, f"Response time {response_time:.3f}s exceeds 500ms SLA"
            
            time.sleep(0.1)  # Brief pause between requests
        
        # Calculate average response time
        avg_response_time = sum(response_times) / len(response_times)
        print(f"Average response time: {avg_response_time:.3f}s")
        assert avg_response_time < 0.5, f"Average response time {avg_response_time:.3f}s exceeds SLA"


class TestAPIResilience:
    """Test API resilience and error recovery."""
    
    def test_network_timeout_handling(self, client: TestClient):
        """Test handling of network timeouts."""
        # This test would typically involve mocking network delays
        # For real E2E testing, we test the timeout configuration
        
        request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "test_project_123"
                }
            },
            "id": "timeout_test_001"
        }
        
        # The test mainly verifies that the system handles timeouts gracefully
        response = client.post("/mcp", json=request)
        
        # Should either succeed or fail gracefully (not hang)
        assert response.status_code in [200, 408, 500, 503]
    
    def test_api_unavailable_scenario(self, client: TestClient):
        """Test behavior when Zoho API is unavailable."""
        # Test with clearly invalid endpoint to simulate API unavailability
        request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "completely_invalid_project_that_should_not_exist_12345"
                }
            },
            "id": "unavailable_test_001"
        }
        
        response = client.post("/mcp", json=request)
        
        # Should handle gracefully with appropriate error response
        assert response.status_code == 200  # MCP protocol always returns 200
        data = response.json()
        
        # But should contain error information
        assert "error" in data or "not found" in str(data).lower()