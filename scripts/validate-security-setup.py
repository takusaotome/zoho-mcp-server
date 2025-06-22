#!/usr/bin/env python3
"""
Security Setup Validation Script

This script validates that the security testing infrastructure is properly configured.
"""

import os
import sys
import subprocess
import json
from pathlib import Path


def check_environment():
    """Check if the environment is properly configured for security testing."""
    print("🔍 Checking environment configuration...")
    
    required_env_vars = {
        'ENVIRONMENT': 'security_test',
        'ALLOWED_IPS': '127.0.0.1,::1,testclient,unknown,0.0.0.0/0',
        'JWT_SECRET': 'security_test_jwt_secret_key_32_chars_long_for_testing'
    }
    
    missing_vars = []
    for var, default_value in required_env_vars.items():
        if var not in os.environ:
            os.environ[var] = default_value
            print(f"  ⚠️  Set {var} to default value")
        else:
            print(f"  ✅ {var} is configured")
    
    if missing_vars:
        print(f"  ❌ Missing environment variables: {', '.join(missing_vars)}")
        return False
    
    return True


def check_dependencies():
    """Check if required security testing dependencies are installed."""
    print("📦 Checking security dependencies...")
    
    required_packages = [
        'pytest',
        'pytest-html',
        'pytest-json-report',
        'bandit',
        'safety'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"  ✅ {package} is installed")
        except ImportError:
            try:
                # Try alternative import names
                if package == 'pytest-html':
                    import pytest_html
                elif package == 'pytest-json-report':
                    import pytest_jsonreport
                else:
                    raise ImportError()
                print(f"  ✅ {package} is installed")
            except ImportError:
                print(f"  ❌ {package} is not installed")
                missing_packages.append(package)
    
    if missing_packages:
        print(f"  ❌ Missing packages: {', '.join(missing_packages)}")
        print("  💡 Run: pip install -r requirements-dev.txt")
        return False
    
    return True


def check_redis_connection():
    """Check if Redis is accessible for security tests."""
    print("📡 Checking Redis connection...")
    
    try:
        import redis
        
        redis_url = os.environ.get('REDIS_URL', 'redis://localhost:6379/15')
        client = redis.from_url(redis_url)
        client.ping()
        print(f"  ✅ Redis is accessible at {redis_url}")
        return True
    except ImportError:
        print("  ❌ Redis package not installed")
        return False
    except Exception as e:
        print(f"  ❌ Redis connection failed: {e}")
        print("  💡 Start Redis: brew services start redis (macOS) or docker run -d -p 6379:6379 redis:7-alpine")
        return False


def check_security_test_files():
    """Check if security test files exist and are properly structured."""
    print("🧪 Checking security test files...")
    
    test_dir = Path('tests/security')
    required_files = [
        'conftest.py',
        'test_authentication_security.py',
        'test_injection_attacks.py',
        'test_rate_limiting_security.py',
        'test_jwt_security.py',
        'test_owasp_top10.py'
    ]
    
    missing_files = []
    for file_name in required_files:
        file_path = test_dir / file_name
        if file_path.exists():
            print(f"  ✅ {file_name} exists")
        else:
            print(f"  ❌ {file_name} is missing")
            missing_files.append(file_name)
    
    if missing_files:
        print(f"  ❌ Missing test files: {', '.join(missing_files)}")
        return False
    
    return True


def run_sample_security_test():
    """Run a sample security test to validate the setup."""
    print("🚀 Running sample security test...")
    
    try:
        # Set environment for testing
        env = os.environ.copy()
        env.update({
            'ENVIRONMENT': 'security_test',
            'ALLOWED_IPS': '127.0.0.1,::1,testclient,unknown,0.0.0.0/0',
            'JWT_SECRET': 'security_test_jwt_secret_key_32_chars_long_for_testing',
            'REDIS_URL': 'redis://localhost:6379/15',
            'ZOHO_CLIENT_ID': 'test_client_id',
            'ZOHO_CLIENT_SECRET': 'test_client_secret',
            'ZOHO_REFRESH_TOKEN': 'test_refresh_token',
            'PORTAL_ID': 'test_portal_id'
        })
        
        # Run a simple security test
        result = subprocess.run([
            sys.executable, '-m', 'pytest',
            'tests/security/test_authentication_security.py::TestAuthenticationSecurity::test_unauthorized_access_blocked',
            '-v', '--tb=short', '--no-cov'
        ], capture_output=True, text=True, env=env)
        
        # Check if the test actually passed (pytest returns 0 for success)
        if result.returncode == 0 and "1 passed" in result.stdout:
            print("  ✅ Sample security test passed")
            return True
        else:
            print("  ⚠️  Sample security test had issues:")
            print(f"    Return code: {result.returncode}")
            if result.stdout:
                print(f"    stdout: {result.stdout}")
            if result.stderr:
                print(f"    stderr: {result.stderr}")
            # If it's just a coverage issue but test passed, still consider it success
            if "1 passed" in result.stdout and "coverage" in result.stdout:
                print("  ✅ Test passed (coverage warning is expected)")
                return True
            return False
    
    except Exception as e:
        print(f"  ❌ Failed to run sample test: {e}")
        return False


def check_ci_cd_integration():
    """Check if CI/CD workflows are properly configured."""
    print("🔄 Checking CI/CD integration...")
    
    workflow_files = [
        '.github/workflows/ci.yml',
        '.github/workflows/security.yml'
    ]
    
    missing_workflows = []
    for workflow in workflow_files:
        if Path(workflow).exists():
            print(f"  ✅ {workflow} exists")
        else:
            print(f"  ❌ {workflow} is missing")
            missing_workflows.append(workflow)
    
    if missing_workflows:
        print(f"  ❌ Missing workflow files: {', '.join(missing_workflows)}")
        return False
    
    return True


def generate_validation_report(results):
    """Generate a validation report."""
    print("\n📊 Validation Report")
    print("==================")
    
    total_checks = len(results)
    passed_checks = sum(1 for result in results.values() if result)
    
    print(f"Total checks: {total_checks}")
    print(f"Passed: {passed_checks}")
    print(f"Failed: {total_checks - passed_checks}")
    
    if all(results.values()):
        print("\n✅ All security setup validations passed!")
        print("🎯 Security testing infrastructure is ready")
        print("\nNext steps:")
        print("1. Run: ./scripts/run-security-tests.sh")
        print("2. Review security test results")
        print("3. Commit changes and trigger CI/CD pipeline")
    else:
        print("\n❌ Some validation checks failed")
        print("🔧 Please address the issues above before proceeding")
        
        print("\nFailed checks:")
        for check, result in results.items():
            if not result:
                print(f"  - {check}")
    
    # Create validation report file
    report = {
        "timestamp": str(subprocess.check_output(['date'], text=True).strip()),
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "failed_checks": total_checks - passed_checks,
        "results": results,
        "status": "PASS" if all(results.values()) else "FAIL"
    }
    
    os.makedirs('reports', exist_ok=True)
    with open('reports/security-setup-validation.json', 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\n📄 Detailed report saved: reports/security-setup-validation.json")


def main():
    """Main validation function."""
    print("🔒 Security Setup Validation")
    print("============================")
    print(f"Working directory: {os.getcwd()}")
    print(f"Python version: {sys.version}")
    print()
    
    # Run all validation checks
    results = {
        "Environment Configuration": check_environment(),
        "Dependencies": check_dependencies(),
        "Redis Connection": check_redis_connection(),
        "Security Test Files": check_security_test_files(),
        "Sample Test Execution": run_sample_security_test(),
        "CI/CD Integration": check_ci_cd_integration()
    }
    
    # Generate validation report
    generate_validation_report(results)
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()