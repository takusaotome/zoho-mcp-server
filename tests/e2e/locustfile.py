"""Locust performance testing for MCP server."""

import json
import random
import time
from datetime import datetime
from locust import HttpUser, task, between, events


class MCPUser(HttpUser):
    """Simulated MCP client user."""
    
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts."""
        self.project_ids = [
            "test_project_001",
            "test_project_002", 
            "test_project_003"
        ]
        self.task_ids = []
        self.file_ids = [
            "test_file_001",
            "test_file_002"
        ]
        self.folder_ids = [
            "test_folder_001",
            "test_folder_002"
        ]
        
        # Verify server is healthy
        self.check_health()
    
    def check_health(self):
        """Check if server is healthy."""
        response = self.client.get("/health")
        if response.status_code != 200:
            print(f"Health check failed: {response.status_code}")
    
    @task(5)
    def list_tasks(self):
        """List tasks - most common operation."""
        project_id = random.choice(self.project_ids)
        status = random.choice(["open", "closed", "overdue", None])
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": project_id
                }
            },
            "id": f"perf_list_{int(time.time())}"
        }
        
        if status:
            request_data["params"]["arguments"]["status"] = status
        
        with self.client.post("/mcp", json=request_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    response.success()
                elif "error" in data:
                    response.failure(f"MCP Error: {data['error'].get('message', 'Unknown error')}")
                else:
                    response.failure("Invalid MCP response format")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(3)
    def create_task(self):
        """Create task - moderate frequency."""
        project_id = random.choice(self.project_ids)
        timestamp = int(time.time())
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": project_id,
                    "name": f"Load Test Task {timestamp}",
                    "owner": f"loadtest{random.randint(1,10)}@example.com",
                    "due_date": "2025-12-31"
                }
            },
            "id": f"perf_create_{timestamp}"
        }
        
        with self.client.post("/mcp", json=request_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    # Extract task ID if possible
                    try:
                        result_text = data["result"]["content"][0]["text"]
                        if "task_id" in result_text.lower():
                            # Store for later use in updates
                            self.task_ids.append(f"task_{timestamp}")
                    except (KeyError, IndexError):
                        pass
                    response.success()
                elif "error" in data:
                    response.failure(f"MCP Error: {data['error'].get('message', 'Unknown error')}")
                else:
                    response.failure("Invalid MCP response format")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def update_task(self):
        """Update task - lower frequency."""
        if not self.task_ids:
            # Create a dummy task ID for testing
            task_id = f"test_task_{random.randint(1, 1000)}"
        else:
            task_id = random.choice(self.task_ids)
        
        status = random.choice(["open", "closed"])
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "updateTask",
                "arguments": {
                    "task_id": task_id,
                    "status": status
                }
            },
            "id": f"perf_update_{int(time.time())}"
        }
        
        with self.client.post("/mcp", json=request_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    response.success()
                elif "error" in data:
                    # Task not found is acceptable in load testing
                    if "not found" in data['error'].get('message', '').lower():
                        response.success()
                    else:
                        response.failure(f"MCP Error: {data['error'].get('message', 'Unknown error')}")
                else:
                    response.failure("Invalid MCP response format")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(2)
    def get_project_summary(self):
        """Get project summary."""
        project_id = random.choice(self.project_ids)
        period = random.choice(["week", "month"])
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getProjectSummary",
                "arguments": {
                    "project_id": project_id,
                    "period": period
                }
            },
            "id": f"perf_summary_{int(time.time())}"
        }
        
        with self.client.post("/mcp", json=request_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    response.success()
                elif "error" in data:
                    response.failure(f"MCP Error: {data['error'].get('message', 'Unknown error')}")
                else:
                    response.failure("Invalid MCP response format")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def get_task_detail(self):
        """Get task detail - lower frequency."""
        if not self.task_ids:
            task_id = f"test_task_{random.randint(1, 1000)}"
        else:
            task_id = random.choice(self.task_ids)
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "getTaskDetail",
                "arguments": {
                    "task_id": task_id
                }
            },
            "id": f"perf_detail_{int(time.time())}"
        }
        
        with self.client.post("/mcp", json=request_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    response.success()
                elif "error" in data:
                    # Task not found is acceptable in load testing
                    if "not found" in data['error'].get('message', '').lower():
                        response.success()
                    else:
                        response.failure(f"MCP Error: {data['error'].get('message', 'Unknown error')}")
                else:
                    response.failure("Invalid MCP response format")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def search_files(self):
        """Search files."""
        query = random.choice(["test", "document", "review", "report"])
        folder_id = random.choice(self.folder_ids + [None])
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "searchFiles",
                "arguments": {
                    "query": query
                }
            },
            "id": f"perf_search_{int(time.time())}"
        }
        
        if folder_id:
            request_data["params"]["arguments"]["folder_id"] = folder_id
        
        with self.client.post("/mcp", json=request_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    response.success()
                elif "error" in data:
                    response.failure(f"MCP Error: {data['error'].get('message', 'Unknown error')}")
                else:
                    response.failure("Invalid MCP response format")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def download_file(self):
        """Download file - lowest frequency."""
        file_id = random.choice(self.file_ids)
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "downloadFile",
                "arguments": {
                    "file_id": file_id
                }
            },
            "id": f"perf_download_{int(time.time())}"
        }
        
        with self.client.post("/mcp", json=request_data, catch_response=True) as response:
            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    response.success()
                elif "error" in data:
                    # File not found is acceptable in load testing
                    if "not found" in data['error'].get('message', '').lower():
                        response.success()
                    else:
                        response.failure(f"MCP Error: {data['error'].get('message', 'Unknown error')}")
                else:
                    response.failure("Invalid MCP response format")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def test_manifest(self):
        """Test manifest endpoint."""
        with self.client.get("/manifest.json", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if "name" in data and "tools" in data:
                        response.success()
                    else:
                        response.failure("Invalid manifest format")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")
    
    @task(1)
    def test_health(self):
        """Test health endpoint."""
        with self.client.get("/health", catch_response=True) as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure(f"Unhealthy status: {data.get('status')}")
                except json.JSONDecodeError:
                    response.failure("Invalid JSON response")
            else:
                response.failure(f"HTTP {response.status_code}")


class HighLoadUser(MCPUser):
    """High-load user for stress testing."""
    
    wait_time = between(0.1, 0.5)  # Much faster requests
    
    @task(10)
    def rapid_list_tasks(self):
        """Rapid task listing for stress testing."""
        self.list_tasks()
    
    @task(1)
    def rapid_health_check(self):
        """Rapid health checks."""
        self.test_health()


class SpikeTestUser(MCPUser):
    """User for spike testing - sudden load increases."""
    
    wait_time = between(0, 0.1)  # Very fast requests
    
    @task
    def spike_requests(self):
        """Generate spike in requests."""
        # Randomly choose any task
        tasks = [
            self.list_tasks,
            self.create_task,
            self.get_project_summary,
            self.test_health
        ]
        task = random.choice(tasks)
        task()


# Event handlers for custom metrics
@events.request.add_listener
def on_request(request_type, name, response_time, response_length, exception, context, **kwargs):
    """Handle request events for custom metrics."""
    if exception:
        print(f"Request failed: {name} - {exception}")
    
    # Log slow requests (over 500ms as per SLA)
    if response_time > 500:
        print(f"Slow request detected: {name} took {response_time:.2f}ms")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    """Called when test starts."""
    print("Starting MCP Server performance test...")
    print(f"Target host: {environment.host}")


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Called when test stops."""
    print("Performance test completed.")
    
    # Print summary statistics
    stats = environment.stats
    total_requests = stats.total.num_requests
    total_failures = stats.total.num_failures
    
    if total_requests > 0:
        failure_rate = (total_failures / total_requests) * 100
        print(f"Total requests: {total_requests}")
        print(f"Total failures: {total_failures}")
        print(f"Failure rate: {failure_rate:.2f}%")
        print(f"Average response time: {stats.total.avg_response_time:.2f}ms")
        print(f"95th percentile: {stats.total.get_response_time_percentile(0.95):.2f}ms")
        
        # Check SLA compliance
        if stats.total.avg_response_time > 500:
            print("⚠️  WARNING: Average response time exceeds 500ms SLA")
        if failure_rate > 0.1:
            print("⚠️  WARNING: Failure rate exceeds 0.1% target")
        if stats.total.get_response_time_percentile(0.95) > 500:
            print("⚠️  WARNING: 95th percentile exceeds 500ms SLA")


# Custom test scenarios
def run_baseline_test():
    """Run baseline performance test."""
    # This would be called with:
    # locust -f locustfile.py --headless -u 10 -r 2 -t 5m --host http://localhost:8000
    pass


def run_stress_test():
    """Run stress test with high load."""
    # This would be called with:
    # locust -f locustfile.py HighLoadUser --headless -u 50 -r 10 -t 10m --host http://localhost:8000
    pass


def run_spike_test():
    """Run spike test."""
    # This would be called with:
    # locust -f locustfile.py SpikeTestUser --headless -u 100 -r 50 -t 2m --host http://localhost:8000
    pass


if __name__ == "__main__":
    """Direct execution for testing."""
    print("This is a Locust performance test file.")
    print("Run with: locust -f locustfile.py --host http://localhost:8000")
    print("")
    print("Available user classes:")
    print("- MCPUser (default): Normal load testing")
    print("- HighLoadUser: High load stress testing")
    print("- SpikeTestUser: Spike load testing")
    print("")
    print("Example commands:")
    print("1. Baseline test: locust -f locustfile.py --headless -u 10 -r 2 -t 5m")
    print("2. Stress test: locust -f locustfile.py HighLoadUser --headless -u 50 -r 10 -t 10m")
    print("3. Spike test: locust -f locustfile.py SpikeTestUser --headless -u 100 -r 50 -t 2m")