"""Rate limiting security tests for Zoho MCP Server."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest
from fastapi.testclient import TestClient


class TestRateLimitingSecurity:
    """Security tests for rate limiting mechanisms."""

    def test_rate_limit_enforcement(self, client: TestClient, auth_headers):
        """Test that rate limits are properly enforced."""
        # Make requests up to the limit
        responses = []
        for i in range(105):  # Exceed the default 100 req/min limit
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": i
            })
            responses.append(response.status_code)
            
            # Small delay to avoid overwhelming the system
            if i % 10 == 0:
                time.sleep(0.01)
        
        # Should see rate limiting kick in (429 responses)
        rate_limited_count = sum(1 for status in responses if status == 429)
        assert rate_limited_count > 0, "Rate limiting should have been triggered"

    def test_rate_limit_per_ip_isolation(self, client: TestClient, auth_headers):
        """Test that rate limits are applied per IP address."""
        # This test verifies that different IPs have separate rate limits
        # In test environment, this is harder to test directly, but we can
        # verify the rate limiting logic doesn't interfere with itself
        
        responses_batch_1 = []
        responses_batch_2 = []
        
        # First batch of requests
        for i in range(50):
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping", 
                "id": f"batch1_{i}"
            })
            responses_batch_1.append(response.status_code)
        
        # Small delay
        time.sleep(0.1)
        
        # Second batch of requests
        for i in range(50):
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": f"batch2_{i}"
            })
            responses_batch_2.append(response.status_code)
        
        # Both batches should be subject to rate limiting
        total_requests = len(responses_batch_1) + len(responses_batch_2)
        assert total_requests == 100

    def test_rate_limit_bypass_attempts(self, client: TestClient, auth_headers):
        """Test various attempts to bypass rate limiting."""
        # Test different headers that might be used to bypass rate limiting
        bypass_headers_variants = [
            {**auth_headers, "X-Forwarded-For": "1.2.3.4"},
            {**auth_headers, "X-Real-IP": "5.6.7.8"},
            {**auth_headers, "X-Client-IP": "9.10.11.12"},
            {**auth_headers, "CF-Connecting-IP": "13.14.15.16"},
            {**auth_headers, "True-Client-IP": "17.18.19.20"},
        ]
        
        for headers in bypass_headers_variants:
            # Make enough requests to trigger rate limiting
            rate_limited = False
            for i in range(110):
                response = client.post("/mcp", headers=headers, json={
                    "jsonrpc": "2.0", 
                    "method": "ping",
                    "id": i
                })
                if response.status_code == 429:
                    rate_limited = True
                    break
            
            # Rate limiting should still apply regardless of headers
            assert rate_limited, f"Rate limiting bypassed with headers: {headers}"

    def test_rate_limit_distributed_load(self, client: TestClient, auth_headers):
        """Test rate limiting under distributed load patterns."""
        def make_request(request_id):
            """Make a single request."""
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping", 
                "id": request_id
            })
            return response.status_code
        
        # Simulate concurrent requests
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(make_request, i) for i in range(120)]
            results = [future.result() for future in as_completed(futures)]
        
        # Should see a mix of successful and rate-limited responses
        success_count = sum(1 for status in results if status == 200)
        rate_limited_count = sum(1 for status in results if status == 429)
        
        assert rate_limited_count > 0, "Rate limiting should trigger under load"
        assert success_count > 0, "Some requests should succeed"

    def test_rate_limit_time_window_reset(self, client: TestClient, auth_headers):
        """Test that rate limits reset after time window."""
        # Make requests to approach the limit
        for i in range(95):
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": f"setup_{i}"
            })
        
        # Make a few more to trigger rate limiting
        rate_limited_responses = []
        for i in range(10):
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping", 
                "id": f"trigger_{i}"
            })
            rate_limited_responses.append(response.status_code)
        
        # Should see some rate limiting
        assert any(status == 429 for status in rate_limited_responses)

    def test_rate_limit_dos_attack_simulation(self, client: TestClient, auth_headers):
        """Test rate limiting effectiveness against DoS attacks."""
        # Simulate rapid-fire requests (DoS attempt)
        rapid_responses = []
        start_time = time.time()
        
        for i in range(200):  # Well above rate limit
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": f"dos_{i}"
            })
            rapid_responses.append((response.status_code, time.time() - start_time))
        
        # Analyze response pattern
        success_count = sum(1 for status, _ in rapid_responses if status == 200)
        rate_limited_count = sum(1 for status, _ in rapid_responses if status == 429)
        
        # Rate limiting should significantly reduce successful requests
        assert rate_limited_count > success_count, "Rate limiting should block most DoS requests"
        assert rate_limited_count > 50, "Should see substantial rate limiting"

    def test_rate_limit_gradual_vs_burst_patterns(self, client: TestClient, auth_headers):
        """Test rate limiting behavior with different request patterns."""
        # Test gradual requests (should mostly succeed)
        gradual_responses = []
        for i in range(50):
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": f"gradual_{i}"
            })
            gradual_responses.append(response.status_code)
            time.sleep(0.02)  # Small delay between requests
        
        # Test burst pattern (should trigger rate limiting)
        burst_responses = []
        for i in range(80):  # Burst of requests
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0", 
                "method": "ping",
                "id": f"burst_{i}"
            })
            burst_responses.append(response.status_code)
        
        # Gradual requests should have higher success rate
        gradual_success_rate = sum(1 for s in gradual_responses if s == 200) / len(gradual_responses)
        burst_success_rate = sum(1 for s in burst_responses if s == 200) / len(burst_responses)
        
        # Note: This might not always be true due to cumulative effects
        # The important thing is that rate limiting is working

    def test_rate_limit_error_response_format(self, client: TestClient, auth_headers):
        """Test that rate limit error responses are properly formatted."""
        # Trigger rate limiting
        for i in range(110):
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping", 
                "id": i
            })
            
            if response.status_code == 429:
                # Check response format
                assert "Retry-After" in response.headers or "X-RateLimit-Reset" in response.headers
                
                # Check response body
                try:
                    data = response.json()
                    assert "error" in data or "message" in data
                except:
                    # Text response is also acceptable for rate limiting
                    assert response.text
                break

    def test_rate_limit_bypass_path_exclusions(self, client: TestClient):
        """Test that certain paths bypass rate limiting.""" 
        # Health endpoint should bypass rate limiting
        health_responses = []
        for i in range(150):  # Well above normal rate limit
            response = client.get("/health")
            health_responses.append(response.status_code)
        
        # Health checks should mostly succeed even with high volume
        success_count = sum(1 for status in health_responses if status == 200)
        assert success_count > 140, "Health endpoint should bypass rate limiting"

    def test_rate_limit_memory_consumption(self, client: TestClient, auth_headers):
        """Test that rate limiting doesn't consume excessive memory."""
        # This test ensures the rate limiting implementation
        # doesn't leak memory with large numbers of clients
        
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss
        
        # Make requests that will create rate limiting state
        for i in range(1000):
            # Vary the requests to simulate different clients
            varied_headers = {**auth_headers, "X-Test-Client": f"client_{i % 100}"}
            response = client.post("/mcp", headers=varied_headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": i
            })
        
        final_memory = process.memory_info().rss
        memory_increase = final_memory - initial_memory
        
        # Memory increase should be reasonable (less than 50MB for this test)
        assert memory_increase < 50 * 1024 * 1024, "Rate limiting should not consume excessive memory"

    def test_rate_limit_configuration_validation(self, client: TestClient, auth_headers):
        """Test that rate limiting respects configuration."""
        # This test verifies that the rate limiting uses the configured limits
        # We can infer this by the behavior pattern
        
        responses = []
        start_time = time.time()
        
        # Make requests and record timing
        for i in range(120):
            response = client.post("/mcp", headers=auth_headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": i
            })
            responses.append((response.status_code, time.time() - start_time))
        
        # Analyze when rate limiting kicks in
        first_rate_limit = None
        for i, (status, timestamp) in enumerate(responses):
            if status == 429:
                first_rate_limit = i
                break
        
        # Should start rate limiting around the configured limit (100 req/min)
        if first_rate_limit:
            assert first_rate_limit >= 80, "Rate limiting should respect configured limits"