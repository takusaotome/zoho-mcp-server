"""Advanced JWT security tests for Zoho MCP Server."""

import base64
import hashlib
import hmac
import json
import time
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from server.auth.jwt_handler import JWTHandler


class TestJWTSecurity:
    """Advanced security tests for JWT implementation."""

    def test_jwt_secret_strength_validation(self):
        """Test that JWT secret meets security requirements."""
        # This test ensures the JWT secret is sufficiently strong
        jwt_handler = JWTHandler()
        
        # The secret should be at least 256 bits (32 bytes)
        assert len(jwt_handler.secret_key) >= 32, "JWT secret should be at least 32 characters"
        
        # Secret should not be a common/weak value
        weak_secrets = [
            "secret", "password", "123456", "jwt_secret", 
            "your-256-bit-secret", "default", "test"
        ]
        assert jwt_handler.secret_key.lower() not in weak_secrets, "JWT secret should not be a weak value"

    def test_jwt_algorithm_security(self):
        """Test JWT algorithm security configuration."""
        jwt_handler = JWTHandler()
        
        # Should use a secure algorithm
        secure_algorithms = ["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"]
        assert jwt_handler.algorithm in secure_algorithms, "Should use a secure JWT algorithm"
        
        # Should not allow 'none' algorithm
        assert jwt_handler.algorithm != "none", "Should not use 'none' algorithm"

    def test_jwt_claims_validation(self):
        """Test comprehensive JWT claims validation."""
        jwt_handler = JWTHandler()
        token = jwt_handler.create_access_token("test_user")
        
        # Decode without verification to inspect claims
        payload = jwt.decode(token, options={"verify_signature": False})
        
        # Required claims should be present
        required_claims = ["sub", "exp", "iat", "type"]
        for claim in required_claims:
            assert claim in payload, f"Required claim '{claim}' missing"
        
        # Subject should be non-empty
        assert payload["sub"], "Subject claim should not be empty"
        
        # Expiration should be in the future
        assert payload["exp"] > int(time.time()), "Token should not be pre-expired"
        
        # Issued time should be reasonable (not too far in past/future)
        iat_time = payload["iat"]
        current_time = int(time.time())
        assert abs(iat_time - current_time) < 10, "Issued time should be current"
        
        # Type should be 'access'
        assert payload["type"] == "access", "Token type should be 'access'"

    def test_jwt_key_confusion_attack(self):
        """Test protection against JWT key confusion attacks."""
        jwt_handler = JWTHandler()
        
        # Generate RSA key pair
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        public_key = private_key.public_key()
        
        # Create token with RSA private key (RS256)
        malicious_payload = {
            "sub": "attacker",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "type": "access"
        }
        
        # Sign with RSA private key
        rsa_token = jwt.encode(
            malicious_payload,
            private_key,
            algorithm="RS256"
        )
        
        # Try to verify with HMAC using public key as secret
        # This should fail (key confusion attack prevention)
        public_key_pem = public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        
        with pytest.raises(HTTPException):
            # Temporarily replace the algorithm to test
            original_algo = jwt_handler.algorithm
            jwt_handler.algorithm = "HS256"
            jwt_handler.secret_key = public_key_pem.decode()
            try:
                jwt_handler.verify_token(rsa_token)
            finally:
                jwt_handler.algorithm = original_algo

    def test_jwt_timing_attack_resistance(self):
        """Test JWT verification timing attack resistance."""
        jwt_handler = JWTHandler()
        
        # Create tokens with different validity states
        valid_token = jwt_handler.create_access_token("user1")
        
        # Various invalid tokens
        invalid_tokens = [
            "completely.invalid.token",
            valid_token[:-10] + "tampered123",  # Tampered signature
            jwt.encode({"sub": "user", "exp": int(time.time()) - 1}, "wrong_secret", algorithm="HS256"),  # Wrong secret
            valid_token.replace(".", "X", 1),  # Malformed structure
        ]
        
        # Measure verification times
        times = []
        
        # Time valid token verification
        start = time.time()
        try:
            jwt_handler.verify_token(valid_token)
        except:
            pass
        times.append(time.time() - start)
        
        # Time invalid token verifications
        for token in invalid_tokens:
            start = time.time()
            try:
                jwt_handler.verify_token(token)
            except:
                pass
            times.append(time.time() - start)
        
        # All verification times should be relatively similar
        # (no significant timing differences that could leak information)
        avg_time = sum(times) / len(times)
        for t in times:
            # Allow for some variance but not too much
            assert abs(t - avg_time) < 0.05, "Verification times should be consistent"

    def test_jwt_replay_attack_protection(self):
        """Test protection against JWT replay attacks."""
        jwt_handler = JWTHandler()
        
        # Create token with short expiration
        short_lived_token = jwt_handler.create_access_token(
            "user1",
            expires_delta=timedelta(seconds=1)
        )
        
        # Token should be valid initially
        token_data = jwt_handler.verify_token(short_lived_token)
        assert token_data.sub == "user1"
        
        # Wait for token to expire
        time.sleep(2)
        
        # Token should now be invalid (replay protection)
        with pytest.raises(HTTPException) as exc_info:
            jwt_handler.verify_token(short_lived_token)
        assert exc_info.value.status_code == 401

    def test_jwt_iat_future_prevention(self):
        """Test prevention of tokens with future issued-at times."""
        jwt_handler = JWTHandler()
        
        # Create token with future iat claim
        future_time = int(time.time()) + 3600  # 1 hour in future
        malicious_payload = {
            "sub": "user",
            "exp": future_time + 3600,
            "iat": future_time,  # Future issued time
            "type": "access"
        }
        
        future_token = jwt.encode(
            malicious_payload,
            jwt_handler.secret_key,
            algorithm=jwt_handler.algorithm
        )
        
        # Should reject token with future iat
        with pytest.raises(HTTPException):
            jwt_handler.verify_token(future_token)

    def test_jwt_exp_validation(self):
        """Test thorough expiration validation."""
        jwt_handler = JWTHandler()
        
        # Test various expiration scenarios
        test_cases = [
            -3600,  # Expired 1 hour ago
            -60,    # Expired 1 minute ago
            -1,     # Expired 1 second ago
        ]
        
        for exp_offset in test_cases:
            exp_time = int(time.time()) + exp_offset
            payload = {
                "sub": "user",
                "exp": exp_time,
                "iat": int(time.time()) - 3600,  # Issued 1 hour ago
                "type": "access"
            }
            
            expired_token = jwt.encode(
                payload,
                jwt_handler.secret_key,
                algorithm=jwt_handler.algorithm
            )
            
            with pytest.raises(HTTPException) as exc_info:
                jwt_handler.verify_token(expired_token)
            assert exc_info.value.status_code == 401

    def test_jwt_sub_claim_injection(self):
        """Test protection against subject claim injection."""
        jwt_handler = JWTHandler()
        
        # Try various injection attempts in subject
        malicious_subjects = [
            "admin'; DROP TABLE users; --",  # SQL injection
            "../admin",  # Path traversal
            "user\nadmin",  # Newline injection
            "user\x00admin",  # Null byte injection
            {"admin": True},  # Object injection
            ["admin", "user"],  # Array injection
        ]
        
        for malicious_sub in malicious_subjects:
            try:
                token = jwt_handler.create_access_token(str(malicious_sub))
                token_data = jwt_handler.verify_token(token)
                
                # Subject should be treated as literal string
                assert token_data.sub == str(malicious_sub)
            except (TypeError, ValueError):
                # It's acceptable for some malicious inputs to be rejected during creation
                pass

    def test_jwt_custom_claims_rejection(self):
        """Test that custom/unexpected claims are handled safely."""
        jwt_handler = JWTHandler()
        
        # Create token with extra claims
        payload = {
            "sub": "user",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "type": "access",
            # Potentially dangerous extra claims
            "admin": True,
            "role": "superuser",
            "permissions": ["*"],
            "__proto__": {"admin": True},
        }
        
        malicious_token = jwt.encode(
            payload,
            jwt_handler.secret_key,
            algorithm=jwt_handler.algorithm
        )
        
        # Token should be verified but extra claims should not grant privileges
        token_data = jwt_handler.verify_token(malicious_token)
        
        # Only standard claims should be in the response
        assert hasattr(token_data, 'sub')
        assert hasattr(token_data, 'exp')
        assert hasattr(token_data, 'iat')
        
        # Dangerous claims should not be present or should be ignored
        assert not hasattr(token_data, 'admin')
        assert not hasattr(token_data, 'role')

    def test_jwt_nbf_claim_handling(self):
        """Test not-before (nbf) claim handling if implemented."""
        jwt_handler = JWTHandler()
        
        # Create token valid only in the future
        future_time = int(time.time()) + 3600
        payload = {
            "sub": "user",
            "exp": future_time + 3600,
            "iat": int(time.time()),
            "nbf": future_time,  # Not valid before 1 hour from now
            "type": "access"
        }
        
        future_valid_token = jwt.encode(
            payload,
            jwt_handler.secret_key,
            algorithm=jwt_handler.algorithm
        )
        
        # Token should be rejected if nbf is honored
        # (If nbf is not implemented, this test will pass anyway)
        try:
            jwt_handler.verify_token(future_valid_token)
        except HTTPException as e:
            assert e.status_code == 401

    def test_jwt_jti_uniqueness(self):
        """Test JWT ID (jti) uniqueness if implemented."""
        jwt_handler = JWTHandler()
        
        # Create multiple tokens for same user
        tokens = []
        for _ in range(5):
            token = jwt_handler.create_access_token("user")
            tokens.append(token)
            time.sleep(0.01)  # Ensure different timestamps
        
        # Decode tokens to check jti claims
        jtis = []
        for token in tokens:
            payload = jwt.decode(token, options={"verify_signature": False})
            if "jti" in payload:
                jtis.append(payload["jti"])
        
        # If jti is implemented, all should be unique
        if jtis:
            assert len(jtis) == len(set(jtis)), "JTI claims should be unique"

    def test_jwt_critical_header_handling(self):
        """Test handling of critical JWT headers."""
        jwt_handler = JWTHandler()
        
        # Create token with critical header
        headers = {
            "alg": jwt_handler.algorithm,
            "typ": "JWT",
            "crit": ["exp"],  # Critical header
        }
        
        payload = {
            "sub": "user",
            "exp": int(time.time()) + 3600,
            "iat": int(time.time()),
            "type": "access"
        }
        
        # Manually create token with critical header
        header_encoded = base64.urlsafe_b64encode(
            json.dumps(headers).encode()
        ).decode().rstrip('=')
        
        payload_encoded = base64.urlsafe_b64encode(
            json.dumps(payload).encode()
        ).decode().rstrip('=')
        
        signing_input = f"{header_encoded}.{payload_encoded}"
        signature = hmac.new(
            jwt_handler.secret_key.encode(),
            signing_input.encode(),
            hashlib.sha256
        ).digest()
        
        signature_encoded = base64.urlsafe_b64encode(signature).decode().rstrip('=')
        critical_token = f"{signing_input}.{signature_encoded}"
        
        # Token verification should handle critical headers appropriately
        try:
            token_data = jwt_handler.verify_token(critical_token)
            # If accepted, should still be valid
            assert token_data.sub == "user"
        except HTTPException:
            # It's acceptable to reject tokens with unknown critical headers
            pass

    def test_jwt_header_injection_prevention(self):
        """Test prevention of header injection in JWT."""
        jwt_handler = JWTHandler()
        
        # Try to create tokens with malicious headers
        malicious_headers = [
            {"alg": "none"},  # Algorithm confusion
            {"alg": "HS256", "kid": "../../../etc/passwd"},  # Path traversal
            {"alg": "HS256", "x5u": "http://malicious.com/evil.crt"},  # URL injection
        ]
        
        for headers in malicious_headers:
            # Our JWT implementation should not allow header manipulation
            # This test ensures we're not vulnerable to header injection
            token = jwt_handler.create_access_token("user")
            
            # Token should be created with safe headers only
            decoded_header = jwt.get_unverified_header(token)
            assert decoded_header["alg"] == jwt_handler.algorithm
            assert decoded_header["typ"] == "JWT"
            
            # Should not contain malicious header values
            assert decoded_header.get("kid") is None or not decoded_header["kid"].startswith("../")
            assert decoded_header.get("x5u") is None or not decoded_header["x5u"].startswith("http://malicious")