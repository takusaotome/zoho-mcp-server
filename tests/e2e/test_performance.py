"""Performance tests using pytest for MCP server."""

import concurrent.futures
import statistics
import time
from typing import Any

import pytest
from fastapi.testclient import TestClient


class TestPerformance:
    """Performance tests for MCP server."""

    @pytest.mark.slow
    def test_response_time_sla_compliance(self, client: TestClient):
        """Test that response times meet SLA requirements (95% < 500ms)."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "test_project_123"
                }
            },
            "id": "perf_sla_test"
        }

        response_times = []
        num_requests = 20

        for _i in range(num_requests):
            start_time = time.time()
            response = client.post("/mcp", json=request_data)
            end_time = time.time()

            response_time_ms = (end_time - start_time) * 1000
            response_times.append(response_time_ms)

            # Verify response is valid
            assert response.status_code == 200

            # Small delay between requests
            time.sleep(0.05)

        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        max_response_time = max(response_times)

        print(f"Average response time: {avg_response_time:.2f}ms")
        print(f"95th percentile: {p95_response_time:.2f}ms")
        print(f"Max response time: {max_response_time:.2f}ms")

        # SLA requirements
        assert avg_response_time < 500, f"Average response time {avg_response_time:.2f}ms exceeds 500ms SLA"
        assert p95_response_time < 500, f"95th percentile {p95_response_time:.2f}ms exceeds 500ms SLA"

    @pytest.mark.slow
    def test_concurrent_request_handling(self, client: TestClient):
        """Test server handles concurrent requests properly."""

        def make_request(request_id: int) -> dict[str, Any]:
            """Make a single request and return performance metrics."""
            request_data = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "listTasks",
                    "arguments": {
                        "project_id": "test_project_123"
                    }
                },
                "id": f"concurrent_test_{request_id}"
            }

            start_time = time.time()
            response = client.post("/mcp", json=request_data)
            end_time = time.time()

            return {
                "request_id": request_id,
                "status_code": response.status_code,
                "response_time_ms": (end_time - start_time) * 1000,
                "success": response.status_code == 200
            }

        # Test with 10 concurrent requests
        max_workers = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(make_request, i) for i in range(max_workers)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        response_times = [r["response_time_ms"] for r in results if r["success"]]

        print(f"Successful requests: {successful_requests}/{max_workers}")
        if response_times:
            print(f"Average concurrent response time: {statistics.mean(response_times):.2f}ms")
            print(f"Max concurrent response time: {max(response_times):.2f}ms")

        # Assertions
        assert successful_requests >= max_workers * 0.8, f"Only {successful_requests}/{max_workers} requests succeeded"

        if response_times:
            avg_time = statistics.mean(response_times)
            # Concurrent requests may take longer, but shouldn't exceed 1 second
            assert avg_time < 1000, f"Average concurrent response time {avg_time:.2f}ms too high"

    @pytest.mark.slow
    def test_memory_efficiency_bulk_operations(self, client: TestClient):
        """Test memory efficiency with bulk operations."""

        # Test creating multiple tasks in sequence
        task_ids = []
        response_times = []

        for i in range(10):  # Create 10 tasks
            request_data = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "createTask",
                    "arguments": {
                        "project_id": "test_project_123",
                        "name": f"Bulk Test Task {i}",
                        "owner": "performance.test@example.com"
                    }
                },
                "id": f"bulk_create_{i}"
            }

            start_time = time.time()
            response = client.post("/mcp", json=request_data)
            end_time = time.time()

            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)

            assert response.status_code == 200

            # Extract task ID (simplified)
            task_ids.append(f"bulk_task_{i}")

        # Verify response times don't degrade significantly
        first_half_avg = statistics.mean(response_times[:5])
        second_half_avg = statistics.mean(response_times[5:])

        print(f"First half average: {first_half_avg:.2f}ms")
        print(f"Second half average: {second_half_avg:.2f}ms")

        # Response times shouldn't degrade more than 50%
        degradation_factor = second_half_avg / first_half_avg if first_half_avg > 0 else 1
        assert degradation_factor < 1.5, f"Response time degraded by {degradation_factor:.2f}x"

    @pytest.mark.slow
    def test_rate_limiting_behavior(self, client: TestClient):
        """Test rate limiting behavior under load."""

        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "test_project_123"
                }
            },
            "id": "rate_limit_test"
        }

        # Send requests rapidly
        responses = []
        start_time = time.time()

        for _i in range(50):  # Send 50 requests rapidly
            response = client.post("/mcp", json=request_data)
            responses.append({
                "status_code": response.status_code,
                "time": time.time() - start_time
            })

            # No delay - test rate limiting

        # Analyze rate limiting behavior
        success_count = sum(1 for r in responses if r["status_code"] == 200)
        rate_limited_count = sum(1 for r in responses if r["status_code"] == 429)

        total_time = time.time() - start_time
        request_rate = len(responses) / total_time

        print(f"Total requests: {len(responses)}")
        print(f"Successful: {success_count}")
        print(f"Rate limited: {rate_limited_count}")
        print(f"Request rate: {request_rate:.2f} req/sec")

        # Verify rate limiting is working
        if request_rate > 100:  # If we exceeded 100 req/sec
            assert rate_limited_count > 0, "Expected rate limiting to kick in at high request rates"

        # At least some requests should succeed
        assert success_count > 0, "No requests succeeded"

    @pytest.mark.slow
    def test_different_tool_performance(self, client: TestClient):
        """Test performance of different MCP tools."""

        tools_to_test = [
            {
                "name": "listTasks",
                "arguments": {"project_id": "test_project_123"}
            },
            {
                "name": "getProjectSummary",
                "arguments": {"project_id": "test_project_123", "period": "week"}
            },
            {
                "name": "createTask",
                "arguments": {
                    "project_id": "test_project_123",
                    "name": "Performance Test Task",
                    "owner": "perf.test@example.com"
                }
            },
            {
                "name": "searchFiles",
                "arguments": {"query": "test"}
            }
        ]

        tool_performance = {}

        for tool in tools_to_test:
            response_times = []

            # Test each tool 5 times
            for i in range(5):
                request_data = {
                    "jsonrpc": "2.0",
                    "method": "callTool",
                    "params": tool,
                    "id": f"tool_perf_{tool['name']}_{i}"
                }

                start_time = time.time()
                response = client.post("/mcp", json=request_data)
                end_time = time.time()

                response_time = (end_time - start_time) * 1000
                response_times.append(response_time)

                # Verify response
                assert response.status_code == 200

                time.sleep(0.1)  # Small delay between requests

            avg_response_time = statistics.mean(response_times)
            tool_performance[tool["name"]] = {
                "avg_response_time": avg_response_time,
                "min_response_time": min(response_times),
                "max_response_time": max(response_times)
            }

            print(f"{tool['name']}: avg={avg_response_time:.2f}ms")

        # Verify all tools meet performance requirements
        for tool_name, perf in tool_performance.items():
            assert perf["avg_response_time"] < 1000, f"{tool_name} average response time too high: {perf['avg_response_time']:.2f}ms"
            assert perf["max_response_time"] < 2000, f"{tool_name} max response time too high: {perf['max_response_time']:.2f}ms"

    @pytest.mark.slow
    def test_error_rate_under_load(self, client: TestClient):
        """Test error rate under sustained load."""

        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "test_project_123"
                }
            },
            "id": "error_rate_test"
        }

        total_requests = 30
        successful_requests = 0
        error_responses = 0

        for _i in range(total_requests):
            response = client.post("/mcp", json=request_data)

            if response.status_code == 200:
                data = response.json()
                if "result" in data:
                    successful_requests += 1
                elif "error" in data:
                    error_responses += 1
            else:
                error_responses += 1

            # Small delay to simulate realistic load
            time.sleep(0.1)

        success_rate = (successful_requests / total_requests) * 100
        error_rate = (error_responses / total_requests) * 100

        print(f"Total requests: {total_requests}")
        print(f"Successful: {successful_requests} ({success_rate:.1f}%)")
        print(f"Errors: {error_responses} ({error_rate:.1f}%)")

        # Error rate should be very low
        assert error_rate < 1.0, f"Error rate {error_rate:.1f}% exceeds 1% threshold"
        assert success_rate > 99.0, f"Success rate {success_rate:.1f}% below 99% threshold"

    def test_health_endpoint_performance(self, client: TestClient):
        """Test health endpoint performance - should be very fast."""

        response_times = []

        for _i in range(10):
            start_time = time.time()
            response = client.get("/health")
            end_time = time.time()

            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)

            assert response.status_code == 200
            assert response.json()["status"] == "healthy"

        avg_response_time = statistics.mean(response_times)
        max_response_time = max(response_times)

        print(f"Health endpoint avg response time: {avg_response_time:.2f}ms")
        print(f"Health endpoint max response time: {max_response_time:.2f}ms")

        # Health endpoint should be very fast
        assert avg_response_time < 50, f"Health endpoint too slow: {avg_response_time:.2f}ms"
        assert max_response_time < 100, f"Health endpoint max time too high: {max_response_time:.2f}ms"

    def test_manifest_endpoint_performance(self, client: TestClient):
        """Test manifest endpoint performance."""

        response_times = []

        for _i in range(5):
            start_time = time.time()
            response = client.get("/manifest.json")
            end_time = time.time()

            response_time = (end_time - start_time) * 1000
            response_times.append(response_time)

            assert response.status_code == 200
            data = response.json()
            assert "name" in data
            assert "tools" in data

        avg_response_time = statistics.mean(response_times)

        print(f"Manifest endpoint avg response time: {avg_response_time:.2f}ms")

        # Manifest should be fast (it's mostly static data)
        assert avg_response_time < 100, f"Manifest endpoint too slow: {avg_response_time:.2f}ms"


class TestStressConditions:
    """Test server behavior under stress conditions."""

    @pytest.mark.slow
    @pytest.mark.stress
    def test_sustained_load(self, client: TestClient):
        """Test server under sustained load for extended period."""

        duration_seconds = 60  # 1 minute sustained load
        start_time = time.time()

        request_count = 0
        error_count = 0
        response_times = []

        while time.time() - start_time < duration_seconds:
            request_data = {
                "jsonrpc": "2.0",
                "method": "callTool",
                "params": {
                    "name": "listTasks",
                    "arguments": {"project_id": "test_project_123"}
                },
                "id": f"sustained_load_{request_count}"
            }

            req_start = time.time()
            response = client.post("/mcp", json=request_data)
            req_end = time.time()

            response_time = (req_end - req_start) * 1000
            response_times.append(response_time)
            request_count += 1

            if response.status_code != 200:
                error_count += 1

            # Maintain steady load - 2 requests per second
            time.sleep(0.5)

        total_duration = time.time() - start_time
        avg_response_time = statistics.mean(response_times)
        error_rate = (error_count / request_count) * 100

        print(f"Sustained load test duration: {total_duration:.1f}s")
        print(f"Total requests: {request_count}")
        print(f"Average response time: {avg_response_time:.2f}ms")
        print(f"Error rate: {error_rate:.2f}%")

        # Verify server maintained performance
        assert avg_response_time < 1000, f"Performance degraded: {avg_response_time:.2f}ms"
        assert error_rate < 5.0, f"High error rate under load: {error_rate:.2f}%"
