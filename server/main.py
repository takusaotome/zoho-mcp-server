"""FastAPI application for Zoho MCP Server."""

import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from server.core.config import settings
from server.middleware.rate_limit import RateLimitMiddleware
from server.auth.ip_allowlist import IPAllowlistMiddleware
from server.core.mcp_handler import MCPHandler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


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
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_credentials,
        allow_methods=["GET", "POST", "PUT", "DELETE"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(IPAllowlistMiddleware, allowed_ips=settings.allowed_ips)
    app.add_middleware(
        RateLimitMiddleware,
        calls=settings.rate_limit_per_minute,
        period=60
    )
    
    # Initialize MCP handler
    mcp_handler = MCPHandler()
    
    @app.get("/health")
    async def health_check() -> dict[str, str]:
        """Health check endpoint."""
        return {
            "status": "healthy",
            "version": "0.1.0",
            "environment": settings.environment
        }
    
    @app.post("/mcp")
    async def mcp_endpoint(request: Request) -> JSONResponse:
        """MCP JSON-RPC endpoint."""
        try:
            body = await request.json()
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
    
    return app


# Create the application instance
app = create_app()