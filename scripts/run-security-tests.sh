#!/bin/bash

# Security Testing Script for Zoho MCP Server
# This script runs comprehensive security tests locally

set -e

echo "🔒 Starting Security Testing Suite"
echo "================================="

# Set security test environment
export ENVIRONMENT=security_test
export ALLOWED_IPS="127.0.0.1,::1,testclient,unknown,0.0.0.0/0"
export JWT_SECRET="security_test_jwt_secret_key_32_chars_long_for_testing"
export REDIS_URL="redis://localhost:6379/15"
export ZOHO_CLIENT_ID="test_client_id"
export ZOHO_CLIENT_SECRET="test_client_secret"
export ZOHO_REFRESH_TOKEN="test_refresh_token"
export PORTAL_ID="test_portal_id"

# Function to check if Redis is running
check_redis() {
    echo "📡 Checking Redis connection..."
    if ! redis-cli ping > /dev/null 2>&1; then
        echo "❌ Redis is not running. Please start Redis first."
        echo "   macOS: brew services start redis"
        echo "   Ubuntu: sudo systemctl start redis"
        echo "   Docker: docker run -d -p 6379:6379 redis:7-alpine"
        exit 1
    fi
    echo "✅ Redis is running"
}

# Function to install security dependencies
install_deps() {
    echo "📦 Installing security testing dependencies..."
    pip install -r requirements-security.txt
    echo "✅ Dependencies installed"
}

# Function to run static security analysis
run_static_analysis() {
    echo "🔍 Running static security analysis..."
    
    echo "  Running bandit..."
    bandit -r server/ -f json -o reports/bandit-report.json || true
    bandit -r server/ -f txt || true
    
    echo "  Running safety check..."
    safety check --json --output reports/safety-report.json || true
    safety check --short-report || true
    
    echo "  Running pip-audit..."
    pip-audit --format=json --output=reports/pip-audit-report.json || true
    pip-audit --format=cyclonedx-json --output=reports/pip-audit-cyclonedx.json || true
    
    echo "✅ Static analysis complete"
}

# Function to run security tests
run_security_tests() {
    echo "🧪 Running security tests..."
    
    # Create reports directory
    mkdir -p reports
    
    # Run all security tests with detailed reporting
    pytest tests/security/ -v --tb=short \
        --html=reports/security-test-report.html --self-contained-html \
        --json-report --json-report-file=reports/security-test-results.json \
        --maxfail=10 \
        || true
    
    echo "✅ Security tests complete"
}

# Function to run performance security tests
run_performance_tests() {
    echo "⚡ Running performance security tests..."
    
    # Run rate limiting and DoS simulation tests
    pytest tests/security/test_rate_limiting_security.py -v \
        --benchmark-only --benchmark-json=reports/security-benchmark.json \
        || true
    
    echo "✅ Performance security tests complete"
}

# Function to generate security report
generate_report() {
    echo "📊 Generating security report..."
    
    cat > reports/security-summary.md << EOF
# Security Test Summary

Generated: $(date)

## Test Results

### Security Test Suite
$(python -c "
import json
import os
if os.path.exists('reports/security-test-results.json'):
    with open('reports/security-test-results.json') as f:
        data = json.load(f)
        summary = data.get('summary', {})
        print(f'- Total tests: {summary.get(\"total\", 0)}')
        print(f'- Passed: {summary.get(\"passed\", 0)}')
        print(f'- Failed: {summary.get(\"failed\", 0)}')
        print(f'- Skipped: {summary.get(\"skipped\", 0)}')
        if summary.get('failed', 0) > 0:
            print('\\n⚠️ Some security tests failed. Review detailed report.')
        else:
            print('\\n✅ All security tests passed.')
else:
    print('No test results found.')
")

### Static Analysis Results
$(if [ -f "reports/bandit-report.json" ]; then
    python -c "
import json
with open('reports/bandit-report.json') as f:
    data = json.load(f)
    results = data.get('results', [])
    high = len([r for r in results if r.get('issue_severity') == 'HIGH'])
    medium = len([r for r in results if r.get('issue_severity') == 'MEDIUM'])
    low = len([r for r in results if r.get('issue_severity') == 'LOW'])
    print(f'Bandit: {high} high, {medium} medium, {low} low severity issues')
"
else
    echo "Bandit: No report generated"
fi)

### Dependency Security
$(if [ -f "reports/safety-report.json" ]; then
    python -c "
import json
with open('reports/safety-report.json') as f:
    data = json.load(f)
    vulnerable = len(data.get('vulnerabilities', []))
    print(f'Safety: {vulnerable} vulnerable dependencies found')
"
else
    echo "Safety: No report generated"
fi)

## Files Generated
- Detailed HTML report: reports/security-test-report.html
- JSON results: reports/security-test-results.json
- Bandit report: reports/bandit-report.json
- Safety report: reports/safety-report.json
- Pip-audit report: reports/pip-audit-report.json

## Next Steps
1. Review the detailed HTML report for test failures
2. Address any high-severity issues found by bandit
3. Update vulnerable dependencies identified by safety
4. Fix failing security tests
5. Run tests again to verify fixes

EOF
    
    echo "✅ Security report generated: reports/security-summary.md"
}

# Function to display help
show_help() {
    cat << EOF
Security Testing Script for Zoho MCP Server

Usage: $0 [OPTIONS]

Options:
    --help, -h          Show this help message
    --static-only       Run only static analysis (no dynamic tests)
    --tests-only        Run only security tests (no static analysis)
    --performance       Include performance security tests
    --install-deps      Install security testing dependencies
    --quick             Run quick security check (essential tests only)

Examples:
    $0                  Run full security test suite
    $0 --quick          Run quick security check
    $0 --static-only    Run only static analysis
    $0 --install-deps   Install dependencies and run full suite

EOF
}

# Parse command line arguments
STATIC_ONLY=false
TESTS_ONLY=false
PERFORMANCE=false
INSTALL_DEPS=false
QUICK=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --help|-h)
            show_help
            exit 0
            ;;
        --static-only)
            STATIC_ONLY=true
            shift
            ;;
        --tests-only)
            TESTS_ONLY=true
            shift
            ;;
        --performance)
            PERFORMANCE=true
            shift
            ;;
        --install-deps)
            INSTALL_DEPS=true
            shift
            ;;
        --quick)
            QUICK=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            show_help
            exit 1
            ;;
    esac
done

# Main execution
main() {
    echo "🔒 Zoho MCP Server Security Testing"
    echo "===================================="
    echo "Environment: $ENVIRONMENT"
    echo "Timestamp: $(date)"
    echo ""
    
    # Install dependencies if requested
    if [ "$INSTALL_DEPS" = true ]; then
        install_deps
    fi
    
    # Check prerequisites
    check_redis
    
    # Create reports directory
    mkdir -p reports
    
    # Run appropriate tests based on flags
    if [ "$STATIC_ONLY" = true ]; then
        run_static_analysis
    elif [ "$TESTS_ONLY" = true ]; then
        run_security_tests
        if [ "$PERFORMANCE" = true ]; then
            run_performance_tests
        fi
    elif [ "$QUICK" = true ]; then
        echo "🚀 Running quick security check..."
        pytest tests/security/test_authentication_security.py::TestAuthenticationSecurity::test_unauthorized_access_blocked -v
        pytest tests/security/test_injection_attacks.py::TestInjectionSecurity::test_json_injection_in_mcp_requests -v
        bandit -r server/ -ll || true
    else
        # Full security test suite
        run_static_analysis
        run_security_tests
        if [ "$PERFORMANCE" = true ]; then
            run_performance_tests
        fi
    fi
    
    # Generate summary report
    generate_report
    
    echo ""
    echo "🎯 Security testing complete!"
    echo "📄 Check reports/security-summary.md for summary"
    echo "🌐 Open reports/security-test-report.html for detailed results"
}

# Run main function
main "$@"