#!/usr/bin/env python3
"""
Performance test runner that simulates load testing.
"""

import asyncio
import json
import os
import sys
import time
import statistics
import concurrent.futures
from datetime import datetime
from typing import Dict, Any, List, Tuple

import httpx


class PerformanceTestRunner:
    """Performance test runner."""
    
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.test_results = []
        self.passed = 0
        self.failed = 0
        self.response_times = []
        
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")
    
    def assert_true(self, condition: bool, message: str = ""):
        """Simple assertion."""
        if condition:
            self.log(f"✅ PASS: {message}")
            self.passed += 1
            return True
        else:
            self.log(f"❌ FAIL: {message}", "ERROR")
            self.failed += 1
            return False
    
    def make_request(self, endpoint: str = "/health", method: str = "GET", 
                    data: Dict[str, Any] = None) -> Tuple[int, float, Dict[str, Any]]:
        """Make HTTP request and measure response time."""
        start_time = time.time()
        
        try:
            with httpx.Client(timeout=10.0) as client:
                if method.upper() == "GET":
                    response = client.get(f"{self.base_url}{endpoint}")
                elif method.upper() == "POST":
                    response = client.post(f"{self.base_url}{endpoint}", json=data)
                else:
                    raise ValueError(f"Unsupported method: {method}")
                
                end_time = time.time()
                response_time = (end_time - start_time) * 1000  # Convert to ms
                
                try:
                    response_data = response.json()
                except:
                    response_data = {"text": response.text}
                
                return response.status_code, response_time, response_data
                
        except Exception as e:
            end_time = time.time()
            response_time = (end_time - start_time) * 1000
            self.log(f"Request failed: {e}", "ERROR")
            return 0, response_time, {"error": str(e)}
    
    def test_response_time_sla(self):
        """Test that response times meet SLA requirements (95% < 500ms)."""
        self.log("🕒 Performance Test: Response Time SLA Compliance")
        
        endpoint = "/health"
        num_requests = 20
        response_times = []
        
        for i in range(num_requests):
            status_code, response_time, _ = self.make_request(endpoint)
            response_times.append(response_time)
            
            if status_code == 200:
                self.log(f"Request {i+1}: {response_time:.2f}ms")
            else:
                self.log(f"Request {i+1} failed: HTTP {status_code}", "ERROR")
            
            time.sleep(0.05)  # Small delay between requests
        
        # Calculate statistics
        avg_response_time = statistics.mean(response_times)
        p95_response_time = statistics.quantiles(response_times, n=20)[18]  # 95th percentile
        max_response_time = max(response_times)
        min_response_time = min(response_times)
        
        self.log(f"📊 Response Time Statistics:")
        self.log(f"   Average: {avg_response_time:.2f}ms")
        self.log(f"   95th percentile: {p95_response_time:.2f}ms") 
        self.log(f"   Min: {min_response_time:.2f}ms")
        self.log(f"   Max: {max_response_time:.2f}ms")
        
        # SLA assertions
        self.assert_true(avg_response_time < 500, f"Average response time {avg_response_time:.2f}ms < 500ms SLA")
        self.assert_true(p95_response_time < 500, f"95th percentile {p95_response_time:.2f}ms < 500ms SLA")
        
        return response_times
    
    def test_concurrent_requests(self):
        """Test server handles concurrent requests properly."""
        self.log("🔄 Performance Test: Concurrent Request Handling")
        
        def make_concurrent_request(request_id: int) -> Dict[str, Any]:
            """Make a single concurrent request."""
            status_code, response_time, data = self.make_request("/health")
            return {
                "request_id": request_id,
                "status_code": status_code, 
                "response_time_ms": response_time,
                "success": status_code == 200
            }
        
        # Test with 10 concurrent requests
        max_workers = 10
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(make_concurrent_request, i) for i in range(max_workers)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # Analyze results
        successful_requests = sum(1 for r in results if r["success"])
        response_times = [r["response_time_ms"] for r in results if r["success"]]
        
        if response_times:
            avg_concurrent_time = statistics.mean(response_times)
            max_concurrent_time = max(response_times)
            
            self.log(f"📊 Concurrent Request Statistics:")
            self.log(f"   Successful requests: {successful_requests}/{max_workers}")
            self.log(f"   Average response time: {avg_concurrent_time:.2f}ms")
            self.log(f"   Max response time: {max_concurrent_time:.2f}ms")
            
            # Assertions
            self.assert_true(successful_requests >= max_workers * 0.8, 
                           f"Success rate: {successful_requests}/{max_workers} >= 80%")
            self.assert_true(avg_concurrent_time < 1000, 
                           f"Average concurrent response time {avg_concurrent_time:.2f}ms < 1000ms")
        else:
            self.assert_true(False, "No successful concurrent requests")
    
    def test_sustained_load(self):
        """Test server under sustained load."""
        self.log("⏱️ Performance Test: Sustained Load (30 seconds)")
        
        duration_seconds = 30
        request_interval = 0.5  # 2 requests per second
        start_time = time.time()
        
        request_count = 0
        error_count = 0
        response_times = []
        
        while time.time() - start_time < duration_seconds:
            status_code, response_time, _ = self.make_request("/health")
            response_times.append(response_time)
            request_count += 1
            
            if status_code != 200:
                error_count += 1
            
            time.sleep(request_interval)
        
        total_duration = time.time() - start_time
        avg_response_time = statistics.mean(response_times) if response_times else 0
        error_rate = (error_count / request_count) * 100 if request_count > 0 else 0
        
        self.log(f"📊 Sustained Load Statistics:")
        self.log(f"   Duration: {total_duration:.1f}s")
        self.log(f"   Total requests: {request_count}")
        self.log(f"   Error count: {error_count}")
        self.log(f"   Error rate: {error_rate:.2f}%")
        self.log(f"   Average response time: {avg_response_time:.2f}ms")
        
        # Assertions
        self.assert_true(error_rate < 5.0, f"Error rate {error_rate:.2f}% < 5%")
        self.assert_true(avg_response_time < 1000, f"Average response time {avg_response_time:.2f}ms < 1000ms")
    
    def test_different_endpoints_performance(self):
        """Test performance of different endpoints."""
        self.log("🎯 Performance Test: Different Endpoints")
        
        endpoints = [
            ("/health", "GET"),
            ("/manifest.json", "GET")
        ]
        
        endpoint_performance = {}
        
        for endpoint, method in endpoints:
            self.log(f"Testing {method} {endpoint}")
            response_times = []
            
            # Test each endpoint 5 times
            for i in range(5):
                status_code, response_time, _ = self.make_request(endpoint, method)
                if status_code in [200, 403]:  # 403 is expected for some endpoints
                    response_times.append(response_time)
                
                time.sleep(0.1)
            
            if response_times:
                avg_time = statistics.mean(response_times)
                min_time = min(response_times)
                max_time = max(response_times)
                
                endpoint_performance[endpoint] = {
                    "avg_response_time": avg_time,
                    "min_response_time": min_time,
                    "max_response_time": max_time
                }
                
                self.log(f"   {endpoint}: avg={avg_time:.2f}ms, min={min_time:.2f}ms, max={max_time:.2f}ms")
                
                # Assertions
                self.assert_true(avg_time < 1000, f"{endpoint} average response time {avg_time:.2f}ms < 1000ms")
                self.assert_true(max_time < 2000, f"{endpoint} max response time {max_time:.2f}ms < 2000ms")
            else:
                self.log(f"   No successful responses for {endpoint}", "WARNING")
        
        return endpoint_performance
    
    def test_memory_efficiency(self):
        """Test memory efficiency with bulk operations."""
        self.log("💾 Performance Test: Memory Efficiency")
        
        # Simulate bulk operations by making many requests
        num_requests = 20
        response_times = []
        
        self.log(f"Making {num_requests} sequential requests...")
        
        for i in range(num_requests):
            status_code, response_time, _ = self.make_request("/health")
            response_times.append(response_time)
            
            if i % 5 == 0:
                self.log(f"   Completed {i+1}/{num_requests} requests")
        
        # Check for performance degradation
        first_half = response_times[:num_requests//2]
        second_half = response_times[num_requests//2:]
        
        first_half_avg = statistics.mean(first_half)
        second_half_avg = statistics.mean(second_half)
        
        self.log(f"📊 Memory Efficiency Statistics:")
        self.log(f"   First half average: {first_half_avg:.2f}ms")
        self.log(f"   Second half average: {second_half_avg:.2f}ms")
        
        # Performance should not degrade significantly
        degradation_factor = second_half_avg / first_half_avg if first_half_avg > 0 else 1
        
        self.log(f"   Performance degradation factor: {degradation_factor:.2f}x")
        
        self.assert_true(degradation_factor < 1.5, 
                        f"Performance degradation {degradation_factor:.2f}x < 1.5x threshold")
    
    def test_error_rate_under_load(self):
        """Test error rate under moderate load."""
        self.log("📈 Performance Test: Error Rate Under Load")
        
        total_requests = 50
        request_interval = 0.1  # 10 requests per second
        
        successful_requests = 0
        error_responses = 0
        
        self.log(f"Making {total_requests} requests at 10 req/sec...")
        
        for i in range(total_requests):
            status_code, response_time, _ = self.make_request("/health")
            
            if status_code == 200:
                successful_requests += 1
            else:
                error_responses += 1
            
            if i % 10 == 0:
                self.log(f"   Progress: {i+1}/{total_requests}")
            
            time.sleep(request_interval)
        
        success_rate = (successful_requests / total_requests) * 100
        error_rate = (error_responses / total_requests) * 100
        
        self.log(f"📊 Error Rate Statistics:")
        self.log(f"   Total requests: {total_requests}")
        self.log(f"   Successful: {successful_requests} ({success_rate:.1f}%)")
        self.log(f"   Errors: {error_responses} ({error_rate:.1f}%)")
        
        # Assertions
        self.assert_true(error_rate < 1.0, f"Error rate {error_rate:.1f}% < 1%")
        self.assert_true(success_rate > 99.0, f"Success rate {success_rate:.1f}% > 99%")
    
    def test_simple_load_simulation(self):
        """Simulate simple load testing with basic scenarios."""
        self.log("🔥 Performance Test: Simple Load Simulation")
        
        # Simulate different user behaviors
        scenarios = [
            {"name": "Health Check", "endpoint": "/health", "weight": 5},
            {"name": "Manifest", "endpoint": "/manifest.json", "weight": 2}
        ]
        
        total_requests = 30
        scenario_results = {}
        
        for scenario in scenarios:
            name = scenario["name"]
            endpoint = scenario["endpoint"]
            weight = scenario["weight"]
            num_requests = int(total_requests * weight / 10)  # Normalize weights
            
            self.log(f"Scenario '{name}': {num_requests} requests to {endpoint}")
            
            response_times = []
            success_count = 0
            
            for i in range(num_requests):
                status_code, response_time, _ = self.make_request(endpoint)
                response_times.append(response_time)
                
                if status_code in [200, 403]:  # 403 might be expected
                    success_count += 1
                
                time.sleep(0.1)  # Simulate user think time
            
            if response_times:
                avg_time = statistics.mean(response_times)
                success_rate = (success_count / num_requests) * 100
                
                scenario_results[name] = {
                    "requests": num_requests,
                    "avg_response_time": avg_time,
                    "success_rate": success_rate
                }
                
                self.log(f"   Results: {avg_time:.2f}ms avg, {success_rate:.1f}% success")
                
                # Assertions for each scenario
                self.assert_true(avg_time < 1000, f"Scenario '{name}' response time {avg_time:.2f}ms < 1000ms")
                self.assert_true(success_rate > 50, f"Scenario '{name}' success rate {success_rate:.1f}% > 50%")
        
        return scenario_results
    
    def run_all_performance_tests(self):
        """Run all performance tests."""
        self.log("Starting Performance Test Suite...")
        self.log("=" * 60)
        
        start_time = time.time()
        
        # Execute performance tests
        try:
            # Basic performance tests
            self.test_response_time_sla()
            self.test_concurrent_requests() 
            self.test_different_endpoints_performance()
            self.test_memory_efficiency()
            self.test_error_rate_under_load()
            
            # Load simulation
            self.test_simple_load_simulation()
            
            # Sustained load test (optional - takes time)
            if os.getenv("RUN_SUSTAINED_LOAD", "false").lower() == "true":
                self.test_sustained_load()
            else:
                self.log("⏭️ Skipping sustained load test (set RUN_SUSTAINED_LOAD=true to enable)")
                
        except KeyboardInterrupt:
            self.log("Performance tests interrupted by user", "WARNING")
        except Exception as e:
            self.log(f"Performance tests failed: {e}", "ERROR")
            self.failed += 1
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Summary
        total_tests = self.passed + self.failed
        success_rate = (self.passed / total_tests * 100) if total_tests > 0 else 0
        
        self.log("=" * 60)
        self.log("Performance Test Suite Results")
        self.log("=" * 60)
        self.log(f"Total Performance Tests: {total_tests}")
        self.log(f"Passed: {self.passed}")
        self.log(f"Failed: {self.failed}")
        self.log(f"Success Rate: {success_rate:.1f}%")
        self.log(f"Duration: {duration:.2f}s")
        
        # Performance summary
        if self.response_times:
            overall_avg = statistics.mean(self.response_times)
            self.log(f"Overall Average Response Time: {overall_avg:.2f}ms")
        
        if self.failed == 0:
            self.log("🎉 All performance tests passed!")
            return True
        else:
            self.log(f"💥 {self.failed} performance test(s) failed")
            return False


def main():
    """Main function."""
    # Set environment variables
    os.environ["TESTING"] = "true"
    os.environ["LOG_LEVEL"] = "DEBUG"
    
    # Parse command line arguments
    base_url = "http://localhost:8001"
    if len(sys.argv) > 1:
        base_url = sys.argv[1]
    
    # Check for sustained load flag
    if "--sustained" in sys.argv:
        os.environ["RUN_SUSTAINED_LOAD"] = "true"
    
    # Run performance tests
    runner = PerformanceTestRunner(base_url)
    success = runner.run_all_performance_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()