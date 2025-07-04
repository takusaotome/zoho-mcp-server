"""FastAPI application for Zoho MCP Server."""

import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware

from server.auth.ip_allowlist import IPAllowlistMiddleware
from server.auth.jwt_handler import TokenData, jwt_handler
from server.auth.oauth_handler import oauth_handler
from server.core.config import settings
from server.core.mcp_handler import MCPHandler
from server.handlers.files import FileHandler
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


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware to add security headers to all responses."""

    async def dispatch(self, request: Request, call_next):
        """Add security headers to response."""
        response = await call_next(request)

        # Security headers to prevent various attacks
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        # Content Security Policy (adjust as needed for your frontend)
        if settings.is_production:
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; "
                "script-src 'self' 'unsafe-inline'; "
                "style-src 'self' 'unsafe-inline'; "
                "img-src 'self' data: https:; "
                "connect-src 'self' https://projectsapi.zoho.com https://workdrive.zoho.com"
            )
        else:
            # More relaxed CSP for development
            response.headers["Content-Security-Policy"] = (
                "default-src 'self' 'unsafe-inline' 'unsafe-eval'; "
                "connect-src 'self' https://projectsapi.zoho.com https://workdrive.zoho.com"
            )

        return response


class RequestSizeLimitMiddleware(BaseHTTPMiddleware):
    """Middleware to limit request body size."""

    def __init__(self, app, max_size: int = 1024 * 1024):  # 1MB default
        """Initialize request size limit middleware.
        
        Args:
            app: FastAPI application
            max_size: Maximum request size in bytes
        """
        super().__init__(app)
        self.max_size = max_size

    async def dispatch(self, request: Request, call_next):
        """Check request size before processing."""
        # Check Content-Length header
        content_length = request.headers.get("Content-Length")
        if content_length:
            try:
                size = int(content_length)
                if size > self.max_size:
                    return JSONResponse(
                        status_code=413,
                        content={
                            "error": "Request Entity Too Large",
                            "message": f"Request size {size} bytes exceeds limit of {self.max_size} bytes"
                        }
                    )
            except ValueError:
                # Invalid Content-Length header
                return JSONResponse(
                    status_code=400,
                    content={
                        "error": "Bad Request",
                        "message": "Invalid Content-Length header"
                    }
                )

        return await call_next(request)


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

    # Add custom middleware (order matters - security headers first)
    app.add_middleware(SecurityHeadersMiddleware)
    app.add_middleware(RequestSizeLimitMiddleware, max_size=settings.max_request_size)
    app.add_middleware(IPAllowlistMiddleware, allowed_ips=settings.allowed_ips.split(","))
    app.add_middleware(
        RateLimitMiddleware,
        calls=settings.rate_limit_per_minute,
        period=60
    )

    # Initialize handlers
    mcp_handler = MCPHandler()
    webhook_handler = WebhookHandler()
    file_handler = FileHandler()

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

    @app.get("/auth/callback")
    async def oauth_callback(code: Optional[str] = None, error: Optional[str] = None) -> HTMLResponse:
        """Handle OAuth callback from Zoho."""
        if error:
            logger.error(f"OAuth error: {error}")
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>認証エラー - Zoho MCP Server</title>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .error {{ color: #d32f2f; }}
                        .icon {{ font-size: 48px; margin-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">❌</div>
                        <h1 class="error">認証エラー</h1>
                        <p>OAuth認証中にエラーが発生しました:</p>
                        <p><strong>{error}</strong></p>
                        <p>もう一度お試しください。</p>
                    </div>
                </body>
                </html>
                """,
                status_code=400
            )

        if not code:
            return HTMLResponse(
                content="""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>認証エラー - Zoho MCP Server</title>
                    <meta charset="UTF-8">
                    <style>
                        body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                        .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                        .error { color: #d32f2f; }
                        .icon { font-size: 48px; margin-bottom: 20px; }
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">❌</div>
                        <h1 class="error">認証コードが見つかりません</h1>
                        <p>認証コードが提供されませんでした。</p>
                        <p>もう一度認証フローを開始してください。</p>
                    </div>
                </body>
                </html>
                """,
                status_code=400
            )

        try:
            # Exchange code for tokens
            logger.info("Processing OAuth callback...")
            result = await oauth_handler.exchange_code_for_token(code)

            if result["success"]:
                # Update .env file with new refresh token
                refresh_token = result["refresh_token"]
                env_updated = await oauth_handler.update_env_file(refresh_token)

                if env_updated:
                    return HTMLResponse(
                        content=f"""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>認証成功 - Zoho MCP Server</title>
                            <meta charset="UTF-8">
                            <style>
                                body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                                .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                                .success {{ color: #2e7d32; }}
                                .info {{ background-color: #e3f2fd; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                                .icon {{ font-size: 48px; margin-bottom: 20px; }}
                                .token {{ font-family: monospace; background-color: #f5f5f5; padding: 10px; border-radius: 4px; word-break: break-all; }}
                                .next-steps {{ background-color: #fff3e0; padding: 15px; border-radius: 4px; margin: 15px 0; }}
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <div class="icon">✅</div>
                                <h1 class="success">認証成功！</h1>
                                <p>Zoho OAuth認証が正常に完了しました。</p>

                                <div class="info">
                                    <h3>取得した情報:</h3>
                                    <ul>
                                        <li><strong>Access Token:</strong> 取得済み（有効期限: {result.get('expires_in', 'N/A')}秒）</li>
                                        <li><strong>Refresh Token:</strong> 取得済み・保存済み</li>
                                        <li><strong>スコープ:</strong> {result.get('scope', 'N/A')}</li>
                                        <li><strong>API Domain:</strong> {result.get('api_domain', 'N/A')}</li>
                                    </ul>
                                </div>

                                <div class="next-steps">
                                    <h3>🎯 次のステップ:</h3>
                                    <ol>
                                        <li>この画面を閉じてください</li>
                                        <li>MCPサーバーが自動的に新しいトークンを使用します</li>
                                        <li>Zoho Projects APIの機能が利用可能になりました</li>
                                    </ol>
                                </div>

                                <p><small>このウィンドウは安全に閉じることができます。</small></p>
                            </div>
                        </body>
                        </html>
                        """
                    )
                else:
                    return HTMLResponse(
                        content="""
                        <!DOCTYPE html>
                        <html>
                        <head>
                            <title>設定エラー - Zoho MCP Server</title>
                            <meta charset="UTF-8">
                            <style>
                                body { font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }
                                .container { max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
                                .warning { color: #f57c00; }
                                .icon { font-size: 48px; margin-bottom: 20px; }
                            </style>
                        </head>
                        <body>
                            <div class="container">
                                <div class="icon">⚠️</div>
                                <h1 class="warning">設定更新エラー</h1>
                                <p>認証は成功しましたが、設定ファイルの更新に失敗しました。</p>
                                <p>手動で以下のRefresh Tokenを.envファイルに設定してください:</p>
                                <p><code>{refresh_token}</code></p>
                            </div>
                        </body>
                        </html>
                        """,
                        status_code=500
                    )
            else:
                return HTMLResponse(
                    content=f"""
                    <!DOCTYPE html>
                    <html>
                    <head>
                        <title>トークン交換エラー - Zoho MCP Server</title>
                        <meta charset="UTF-8">
                        <style>
                            body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                            .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                            .error {{ color: #d32f2f; }}
                            .icon {{ font-size: 48px; margin-bottom: 20px; }}
                        </style>
                    </head>
                    <body>
                        <div class="container">
                            <div class="icon">❌</div>
                            <h1 class="error">トークン交換エラー</h1>
                            <p>認証コードをトークンに変換する際にエラーが発生しました:</p>
                            <p><strong>{result.get('error', 'Unknown error')}</strong></p>
                            <p>もう一度認証フローを開始してください。</p>
                        </div>
                    </body>
                    </html>
                    """,
                    status_code=500
                )

        except Exception as e:
            logger.error(f"OAuth callback processing failed: {e}")
            return HTMLResponse(
                content=f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>処理エラー - Zoho MCP Server</title>
                    <meta charset="UTF-8">
                    <style>
                        body {{ font-family: Arial, sans-serif; margin: 40px; background-color: #f5f5f5; }}
                        .container {{ max-width: 600px; margin: 0 auto; background: white; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
                        .error {{ color: #d32f2f; }}
                        .icon {{ font-size: 48px; margin-bottom: 20px; }}
                    </style>
                </head>
                <body>
                    <div class="container">
                        <div class="icon">❌</div>
                        <h1 class="error">処理エラー</h1>
                        <p>認証処理中に予期しないエラーが発生しました:</p>
                        <p><strong>{str(e)}</strong></p>
                        <p>もう一度認証フローを開始してください。</p>
                    </div>
                </body>
                </html>
                """,
                status_code=500
            )

    @app.post("/mcp")
    async def mcp_endpoint_noauth(request: Request) -> JSONResponse:
        """MCP JSON-RPC endpoint without authentication for Cursor compatibility."""
        try:
            body = await request.json()
            logger.info(f"MCP request (no auth): {body.get('method', 'unknown')}")
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

    @app.post("/mcp-auth")
    async def mcp_endpoint_auth(
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

    @app.get("/api/files/search")
    async def search_files_api(
        query: str = "",
        folder_id: Optional[str] = None,
        limit: int = 10
    ) -> JSONResponse:
        """Search files in WorkDrive via REST API."""
        try:
            result = await file_handler.search_files(query, folder_id)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"File search API failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @app.get("/api/workspaces")
    async def get_workspaces_api() -> JSONResponse:
        """Get workspaces and teams via REST API."""
        try:
            result = await file_handler.get_workspaces_and_teams()
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Workspaces API failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @app.get("/api/team-folders")
    async def get_team_folders_api(team_id: Optional[str] = None) -> JSONResponse:
        """Get team folders via REST API."""
        try:
            result = await file_handler.list_team_folders(team_id)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Team folders API failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
            )

    @app.get("/api/folders/{folder_id}/files")
    async def get_folder_files_api(folder_id: str, limit: int = 50) -> JSONResponse:
        """Get files in a specific folder via REST API."""
        try:
            result = await file_handler.list_folder_contents(folder_id)
            return JSONResponse(content=result)
        except Exception as e:
            logger.error(f"Folder files API failed: {e}")
            return JSONResponse(
                status_code=500,
                content={"error": str(e)}
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
