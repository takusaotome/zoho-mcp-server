"""JWT authentication handler for Zoho MCP Server."""

import logging
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException, status
from pydantic import BaseModel

from server.core.config import settings

logger = logging.getLogger(__name__)


class TokenData(BaseModel):
    """Token data model."""

    sub: str  # Subject (user ID)
    exp: datetime  # Expiration time
    iat: datetime  # Issued at
    jti: Optional[str] = None  # JWT ID


class JWTHandler:
    """JWT token handler for authentication."""

    def __init__(self) -> None:
        """Initialize JWT handler."""
        self.secret_key = settings.jwt_secret
        self.algorithm = settings.jwt_algorithm
        self.expire_hours = settings.jwt_expire_hours

    def create_access_token(
        self,
        subject: str,
        expires_delta: Optional[timedelta] = None
    ) -> str:
        """Create a new access token.

        Args:
            subject: The subject (user ID) for the token
            expires_delta: Optional custom expiration time

        Returns:
            Encoded JWT token
        """
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(hours=self.expire_hours)

        to_encode = {
            "sub": subject,
            "exp": expire,
            "iat": datetime.now(timezone.utc),
            "type": "access"
        }

        try:
            encoded_jwt = jwt.encode(
                to_encode,
                self.secret_key,
                algorithm=self.algorithm
            )
            logger.info(f"Created access token for subject: {subject}")
            return encoded_jwt
        except Exception as e:
            logger.error(f"Failed to create access token: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Could not create access token"
            )

    def verify_token(self, token: str) -> TokenData:
        """Verify and decode a JWT token.

        Args:
            token: JWT token to verify

        Returns:
            Decoded token data

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )

            subject: str = payload.get("sub")
            if subject is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: missing subject"
                )

            # Check token type
            token_type: str = payload.get("type", "access")
            if token_type != "access":
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token type"
                )

            # Create token data
            token_data = TokenData(
                sub=subject,
                exp=datetime.fromtimestamp(payload["exp"], tz=timezone.utc),
                iat=datetime.fromtimestamp(payload["iat"], tz=timezone.utc),
                jti=payload.get("jti")
            )

            logger.debug(f"Token verified for subject: {subject}")
            return token_data

        except jwt.ExpiredSignatureError:
            logger.warning("Token has expired")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )
        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials"
            )

    def get_token_expiry(self, token: str) -> datetime:
        """Get token expiration time.

        Args:
            token: JWT token

        Returns:
            Token expiration datetime
        """
        try:
            payload = jwt.decode(
                token,
                self.secret_key,
                algorithms=[self.algorithm]
            )
            return datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except Exception as e:
            logger.error(f"Failed to get token expiry: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )

    def is_token_expired(self, token: str) -> bool:
        """Check if token is expired.

        Args:
            token: JWT token to check

        Returns:
            True if token is expired
        """
        try:
            expiry = self.get_token_expiry(token)
            return datetime.now(timezone.utc) >= expiry
        except Exception:
            return True

    def refresh_token_if_needed(
        self,
        token: str,
        threshold_minutes: int = 30
    ) -> Optional[str]:
        """Refresh token if it expires within threshold.

        Args:
            token: Current JWT token
            threshold_minutes: Minutes before expiry to refresh

        Returns:
            New token if refreshed, None otherwise
        """
        try:
            token_data = self.verify_token(token)
            time_to_expiry = token_data.exp - datetime.now(timezone.utc)

            if time_to_expiry.total_seconds() < (threshold_minutes * 60):
                logger.info(f"Refreshing token for subject: {token_data.sub}")
                return self.create_access_token(token_data.sub)

            return None
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            return None


# Global JWT handler instance
jwt_handler = JWTHandler()
