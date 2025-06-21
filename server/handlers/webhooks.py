"""Webhook handlers for Zoho integrations."""

import hashlib
import hmac
import logging
from typing import Any, Dict

from fastapi import HTTPException, Request

from server.core.config import settings

logger = logging.getLogger(__name__)


class WebhookHandler:
    """Handler for Zoho webhook events."""
    
    def __init__(self) -> None:
        """Initialize webhook handler."""
        self.webhook_secret = settings.webhook_secret
        logger.info("Webhook handler initialized")
    
    def verify_signature(self, payload: bytes, signature: str) -> bool:
        """Verify webhook signature.
        
        Args:
            payload: Raw request payload
            signature: Signature from headers
            
        Returns:
            True if signature is valid
        """
        if not self.webhook_secret:
            logger.warning("Webhook secret not configured, skipping verification")
            return True
        
        try:
            expected_signature = hmac.new(
                self.webhook_secret.encode('utf-8'),
                payload,
                hashlib.sha256
            ).hexdigest()
            
            # Remove 'sha256=' prefix if present
            if signature.startswith('sha256='):
                signature = signature[7:]
            
            return hmac.compare_digest(expected_signature, signature)
        except Exception as e:
            logger.error(f"Signature verification failed: {e}")
            return False
    
    async def handle_task_updated(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle task updated webhook event.
        
        Args:
            event_data: Webhook event data
            
        Returns:
            Processing result
        """
        try:
            task_id = event_data.get("task_id")
            project_id = event_data.get("project_id")
            changes = event_data.get("changes", {})
            
            logger.info(f"Task updated webhook: {task_id} in project {project_id}")
            
            # Process the webhook event
            # This could trigger GitHub sync, notifications, etc.
            
            result = {
                "status": "processed",
                "task_id": task_id,
                "project_id": project_id,
                "changes_processed": list(changes.keys()) if changes else []
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to process task updated webhook: {e}")
            raise
    
    async def process_webhook(
        self,
        request: Request,
        event_type: str,
        event_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process incoming webhook.
        
        Args:
            request: FastAPI request
            event_type: Type of webhook event
            event_data: Event payload
            
        Returns:
            Processing result
        """
        try:
            # Verify signature if configured
            signature = request.headers.get("X-Zoho-Signature", "")
            payload = await request.body()
            
            if not self.verify_signature(payload, signature):
                raise HTTPException(status_code=401, detail="Invalid signature")
            
            # Route to appropriate handler
            if event_type == "task.updated":
                return await self.handle_task_updated(event_data)
            else:
                logger.warning(f"Unknown webhook event type: {event_type}")
                return {"status": "ignored", "reason": "unknown_event_type"}
                
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            raise