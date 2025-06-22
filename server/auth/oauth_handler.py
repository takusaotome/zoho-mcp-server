"""OAuth authentication handler for Zoho integration."""

import logging
import httpx
from typing import Optional, Dict, Any
from urllib.parse import parse_qs, urlparse

from server.core.config import settings

logger = logging.getLogger(__name__)


class OAuthHandler:
    """Handle OAuth authentication flow."""
    
    def __init__(self):
        self.client_id = settings.zoho_client_id
        self.client_secret = settings.zoho_client_secret
        self.redirect_uri = "http://localhost:8000/auth/callback"
        
    async def exchange_code_for_token(self, auth_code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens."""
        try:
            logger.info(f"Exchanging authorization code for tokens: {auth_code[:20]}...")
            
            # Prepare token exchange request
            token_url = "https://accounts.zoho.com/oauth/v2/token"
            
            data = {
                "grant_type": "authorization_code",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "redirect_uri": self.redirect_uri,
                "code": auth_code
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(token_url, data=data)
                response.raise_for_status()
                
                token_data = response.json()
                logger.info("Token exchange successful")
                
                return {
                    "success": True,
                    "access_token": token_data.get("access_token"),
                    "refresh_token": token_data.get("refresh_token"),
                    "expires_in": token_data.get("expires_in"),
                    "scope": token_data.get("scope"),
                    "api_domain": token_data.get("api_domain")
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"Token exchange HTTP error: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}: {e.response.text}"
            }
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def update_env_file(self, refresh_token: str) -> bool:
        """Update .env file with new refresh token."""
        try:
            import os
            from pathlib import Path
            
            env_file = Path(".env")
            if not env_file.exists():
                logger.error(".env file not found")
                return False
            
            # Read current .env content
            with open(env_file, 'r') as f:
                lines = f.readlines()
            
            # Update refresh token line
            updated_lines = []
            token_updated = False
            
            for line in lines:
                if line.strip().startswith("ZOHO_REFRESH_TOKEN="):
                    updated_lines.append(f"ZOHO_REFRESH_TOKEN={refresh_token}\n")
                    token_updated = True
                else:
                    updated_lines.append(line)
            
            # If token line doesn't exist, add it
            if not token_updated:
                updated_lines.append(f"ZOHO_REFRESH_TOKEN={refresh_token}\n")
            
            # Write updated content
            with open(env_file, 'w') as f:
                f.writelines(updated_lines)
            
            logger.info("Successfully updated .env file with new refresh token")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update .env file: {e}")
            return False


oauth_handler = OAuthHandler() 