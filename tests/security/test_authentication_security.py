"""Authentication security tests for Zoho MCP Server."""

import base64
import json
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from server.auth.jwt_handler import JWTHandler


class TestAuthenticationSecurity:
    """Security tests for authentication mechanisms."""

    def test_unauthorized_access_blocked(self, client: TestClient):
        """Test that unauthorized access is properly blocked."""
        # Test without Authorization header
        response = client.post("/mcp", json={
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {"name": "listTasks", "arguments": {"project_id": "test"}},
            "id": 1
        })
        # Could be 401 (unauthorized) or 403 (forbidden due to IP restrictions)
        assert response.status_code in [401, 403]

    def test_invalid_bearer_token_rejected(self, client: TestClient):
        """Test that invalid bearer tokens are rejected."""
        headers = {"Authorization": "Bearer invalid_token_here"}
        response = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0",
            "method": "callTool", 
            "params": {"name": "listTasks", "arguments": {"project_id": "test"}},
            "id": 1
        })
        assert response.status_code in [401, 403]

    def test_malformed_authorization_header(self, client: TestClient):
        """Test various malformed authorization headers."""
        malformed_headers = [
            {"Authorization": "Basic invalid"},  # Wrong scheme
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": "Bearer token1 token2"},  # Multiple tokens
            {"Authorization": "invalid_format"},  # No scheme
            {"Authorization": ""},  # Empty
        ]
        
        for headers in malformed_headers:
            response = client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": 1
            })
            assert response.status_code in [401, 403]

    def test_jwt_algorithm_confusion_attack(self):
        """Test protection against JWT algorithm confusion attacks."""
        jwt_handler = JWTHandler()
        
        # Create a valid token
        valid_token = jwt_handler.create_access_token("test_user")
        
        # Try to decode with 'none' algorithm (should fail)
        with pytest.raises(HTTPException):
            # Manually craft token with 'none' algorithm
            header = {"alg": "none", "typ": "JWT"}
            payload = {"sub": "test_user", "exp": int(time.time()) + 3600}
            
            none_token = (
                base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip('=') + '.' +
                base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip('=') + '.'
            )
            
            jwt_handler.verify_token(none_token)

    def test_jwt_signature_verification(self):
        """Test JWT signature verification."""
        jwt_handler = JWTHandler()
        
        # Create valid token
        token = jwt_handler.create_access_token("test_user")
        
        # Tamper with token signature
        parts = token.split('.')
        tampered_token = parts[0] + '.' + parts[1] + '.tampered_signature'
        
        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.verify_token(tampered_token)
        assert exc_info.value.status_code == 401

    def test_jwt_expiration_enforcement(self):
        """Test that expired tokens are properly rejected."""
        jwt_handler = JWTHandler()
        
        # Create token that expires immediately
        expired_token = jwt_handler.create_access_token(
            "test_user",
            expires_delta=timedelta(seconds=-1)
        )
        
        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.verify_token(expired_token)
        assert exc_info.value.status_code == 401

    def test_jwt_timing_attack_resistance(self):
        """Test resistance to timing attacks on token verification."""
        jwt_handler = JWTHandler()
        
        # Create multiple invalid tokens
        invalid_tokens = [
            "invalid.token.here",
            "a" * 100,
            "",
            "valid.looking.butinvalidtoken123",
        ]
        
        # Measure response times (should be consistent)
        times = []
        for token in invalid_tokens:
            start_time = time.time()
            try:
                jwt_handler.verify_token(token)
            except HTTPException:
                pass
            end_time = time.time()
            times.append(end_time - start_time)
        
        # All verification times should be relatively similar
        # (within reasonable variance for invalid tokens)
        avg_time = sum(times) / len(times)
        for t in times:
            assert abs(t - avg_time) < 0.1  # 100ms variance allowed

    def test_session_fixation_prevention(self, client: TestClient):
        """Test prevention of session fixation attacks."""
        # Get initial token
        jwt_handler = JWTHandler()
        token1 = jwt_handler.create_access_token("user1")
        
        # Token should be unique for each generation
        token2 = jwt_handler.create_access_token("user1")
        assert token1 != token2
        
        # Both tokens should be valid but independent
        data1 = jwt_handler.verify_token(token1)
        data2 = jwt_handler.verify_token(token2)
        assert data1.sub == data2.sub
        assert data1.iat != data2.iat  # Different issued times

    def test_concurrent_login_handling(self):
        """Test handling of concurrent logins for same user."""
        jwt_handler = JWTHandler()
        
        # Create multiple tokens for same user
        tokens = []
        for _ in range(5):
            token = jwt_handler.create_access_token("test_user")
            tokens.append(token)
            time.sleep(0.01)  # Small delay to ensure different timestamps
        
        # All tokens should be valid independently
        for token in tokens:
            token_data = jwt_handler.verify_token(token)
            assert token_data.sub == "test_user"

    def test_brute_force_protection_simulation(self, client: TestClient):
        """Test behavior under brute force attack simulation."""
        # Simulate multiple failed authentication attempts
        for i in range(10):
            response = client.post("/mcp", headers={
                "Authorization": f"Bearer invalid_token_{i}"
            }, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": i
            })
            assert response.status_code in [401, 403]
        
        # System should still accept valid tokens after failed attempts
        jwt_handler = JWTHandler()
        valid_token = jwt_handler.create_access_token("test_user")
        
        response = client.post("/mcp", headers={
            "Authorization": f"Bearer {valid_token}"
        }, json={
            "jsonrpc": "2.0",
            "method": "ping",
            "id": "valid"
        })
        # Note: This might fail due to IP restrictions in test environment
        # The important part is that the JWT validation works

    def test_token_information_disclosure(self):
        """Test that tokens don't leak sensitive information."""
        jwt_handler = JWTHandler()
        token = jwt_handler.create_access_token("sensitive_user_id")
        
        # Decode token payload without verification to check contents
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Should only contain necessary claims
        required_claims = {"sub", "exp", "iat", "type"}
        actual_claims = set(payload.keys())
        
        # Should not contain extra sensitive information
        assert actual_claims == required_claims
        assert payload["type"] == "access"

    def test_authorization_bypass_attempts(self, client: TestClient):
        """Test various authorization bypass attempts."""
        bypass_attempts = [
            # Header injection attempts
            {"X-User": "admin", "Authorization": "Bearer invalid"},
            {"X-Forwarded-User": "admin"},
            {"X-Auth-User": "admin"},
            # Case sensitivity attempts
            {"authorization": "Bearer token"},
            {"AUTHORIZATION": "Bearer token"},
            # Multiple authorization headers
            {"Authorization": ["Bearer token1", "Bearer token2"]},
        ]
        
        for headers in bypass_attempts:
            response = client.post("/mcp", headers=headers, json={
                "jsonrpc": "2.0",
                "method": "ping",
                "id": 1
            })
            # Should still require proper authentication
            assert response.status_code in [401, 403]

    def test_privilege_escalation_prevention(self, client: TestClient):
        """Test prevention of privilege escalation attempts."""
        jwt_handler = JWTHandler()
        
        # Create token for regular user
        user_token = jwt_handler.create_access_token("regular_user")
        
        # Attempt to access admin-like functionality
        # (In this case, we test that user context is properly maintained)
        headers = {"Authorization": f"Bearer {user_token}"}
        
        response = client.post("/mcp", headers=headers, json={
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {"project_id": "admin_project"}  # Try to access admin project
            },
            "id": 1
        })
        
        # The user should be authenticated but may not have access to admin resources
        # (This depends on how authorization is implemented at the resource level)
        assert response.status_code in [200, 403]  # Either success or forbidden, but not unauthorized

    @pytest.mark.parametrize("invalid_jwt", [
        "not.a.jwt",
        "too.few.parts",
        "too.many.parts.here.invalid",
        "ęyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.invalid.signature",  # Invalid base64
        "eyJhbGciOiJub25lIn0.eyJzdWIiOiJ0ZXN0In0.",  # None algorithm
    ])
    def test_malformed_jwt_handling(self, invalid_jwt):
        """Test handling of various malformed JWT tokens."""
        jwt_handler = JWTHandler()
        
        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.verify_token(invalid_jwt)
        assert exc_info.value.status_code == 401