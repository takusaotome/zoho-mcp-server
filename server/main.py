"""FastAPI application for Zoho MCP Server."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from server.auth.ip_allowlist import IPAllowlistMiddleware
from server.auth.jwt_handler import jwt_handler, TokenData
from server.core.config import settings
from server.core.mcp_handler import MCPHandler
from server.handlers.webhooks import WebhookHandler
from server.middleware.rate_limit import RateLimitMiddleware

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize security scheme
security = HTTPBearer()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events."""
    # Startup
    logger.info("Starting Zoho MCP Server...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug mode: {settings.debug}")

    yield

    # Shutdown
    logger.info("Shutting down Zoho MCP Server...")


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    app = FastAPI(
        title="Zoho MCP Server",
        description="Model Context Protocol integration for Zoho APIs",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        lifespan=lifespan,
    )

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=settings.cors_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )

    # Add custom middleware
    app.add_middleware(IPAllowlistMiddleware, allowed_ips=settings.allowed_ips.split(","))
    app.add_middleware(
        RateLimitMiddleware,
        calls=settings.rate_limit_per_minute,
        period=60
    )

    # Initialize handlers
    mcp_handler = MCPHandler()
    webhook_handler = WebhookHandler()

    async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> TokenData:
        """Get current authenticated user from JWT token."""
        try:
            token_data = jwt_handler.verify_token(credentials.credentials)
            return token_data
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.environment
        }

    @app.post("/mcp")
    async def mcp_endpoint(
        request: Request,
        current_user: TokenData = Depends(get_current_user)
    ) -> JSONResponse:
        """MCP JSON-RPC endpoint with JWT authentication."""
        try:
            body = await request.json()
            logger.info(f"MCP request from user: {current_user.sub}")
            response = await mcp_handler.handle_request(body)
            return JSONResponse(content=response)
        except Exception as e:
            logger.error(f"MCP request failed: {e}")
            return JSONResponse(
                status_code=500,
                content={
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,
                        "message": "Internal error"
                    },
                    "id": body.get("id") if 'body' in locals() else None
                }
            )

    @app.get("/manifest.json")
    async def get_manifest() -> dict[str, object]:
        """Get MCP manifest with available tools."""
        return {
            "name": "zoho-mcp-server",
            "version": "0.1.0",
            "description": "Zoho MCP Server for project and file management",
            "tools": [
                {
                    "name": "listTasks",
                    "description": "List tasks from a Zoho project",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "status": {
                                "type": "string",
                                "enum": ["open", "closed", "overdue"]
                            }
                        },
                        "required": ["project_id"]
                    }
                },
                {
                    "name": "createTask",
                    "description": "Create a new task in Zoho project",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "name": {"type": "string"},
                            "owner": {"type": "string"},
                            "due_date": {"type": "string", "format": "date"}
                        },
                        "required": ["project_id", "name"]
                    }
                },
                {
                    "name": "updateTask",
                    "description": "Update an existing task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"},
                            "status": {"type": "string"},
                            "due_date": {"type": "string", "format": "date"},
                            "owner": {"type": "string"}
                        },
                        "required": ["task_id"]
                    }
                },
                {
                    "name": "getTaskDetail",
                    "description": "Get detailed information about a task",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task_id": {"type": "string"}
                        },
                        "required": ["task_id"]
                    }
                },
                {
                    "name": "getProjectSummary",
                    "description": "Get project summary with completion rate",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "period": {
                                "type": "string",
                                "enum": ["week", "month"]
                            }
                        },
                        "required": ["project_id"]
                    }
                },
                {
                    "name": "downloadFile",
                    "description": "Download a file from WorkDrive",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "file_id": {"type": "string"}
                        },
                        "required": ["file_id"]
                    }
                },
                {
                    "name": "uploadReviewSheet",
                    "description": "Upload a review sheet to WorkDrive",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "project_id": {"type": "string"},
                            "folder_id": {"type": "string"},
                            "name": {"type": "string"},
                            "content_base64": {"type": "string"}
                        },
                        "required": ["project_id", "folder_id", "name", "content_base64"]
                    }
                },
                {
                    "name": "searchFiles",
                    "description": "Search files in WorkDrive",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string"},
                            "folder_id": {"type": "string"}
                        },
                        "required": ["query"]
                    }
                }
            ]
        }

    @app.post("/webhook/task-updated")
    async def webhook_task_updated(request: Request) -> JSONResponse:
        """Handle task updated webhook from Zoho."""
        try:
            body_data = await request.json()
            result = await webhook_handler.process_webhook(
                request=request,
                event_type="task.updated",
                event_data=body_data
            )
            return JSONResponse(content=result)
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Webhook processing failed: {e}")
            raise HTTPException(
                status_code=500,
                detail="Webhook processing failed"
            )

    return app


# Create the application instance
app = create_app()
