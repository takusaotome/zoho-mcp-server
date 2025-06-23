"""MCP (Model Context Protocol) handler for JSON-RPC requests."""

import logging
from typing import Any, Dict, Optional

from pydantic import BaseModel, ValidationError as PydanticValidationError

from server.core.exceptions import ValidationError, MCPError, ResourceNotFoundError
from server.handlers.files import FileHandler
from server.handlers.tasks import TaskHandler

logger = logging.getLogger(__name__)


class MCPRequest(BaseModel):
    """MCP JSON-RPC request model."""

    jsonrpc: str = "2.0"
    method: str
    params: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None


class MCPResponse(BaseModel):
    """MCP JSON-RPC response model."""

    jsonrpc: str = "2.0"
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[Any] = None

    def model_dump(self, **kwargs) -> Dict[str, Any]:
        """Custom model dump that excludes null error field."""
        data = super().model_dump(**kwargs)
        # Remove error field if it's None (success case)
        if data.get("error") is None:
            data.pop("error", None)
        return data


class MCPError:
    """MCP error codes and messages."""

    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    @staticmethod
    def create_error(code: int, message: str, data: Any = None) -> Dict[str, Any]:
        """Create MCP error response.

        Args:
            code: Error code
            message: Error message
            data: Additional error data

        Returns:
            Error dictionary
        """
        error = {"code": code, "message": message}
        if data is not None:
            error["data"] = data
        return error


class MCPHandler:
    """Handle MCP JSON-RPC requests and route to appropriate handlers."""

    def __init__(self) -> None:
        """Initialize MCP handler with tool handlers."""
        self.task_handler = TaskHandler()
        self.file_handler = FileHandler()

        # Register available tools
        self.tools = {
            # Project management tools
            "listProjects": self.task_handler.list_projects,

            # Task management tools
            "listTasks": self.task_handler.list_tasks,
            "createTask": self.task_handler.create_task,
            "updateTask": self.task_handler.update_task,
            "getTaskDetail": self.task_handler.get_task_detail,
            "getProjectSummary": self.task_handler.get_project_summary,

            # File management tools
            "downloadFile": self.file_handler.download_file,
            "uploadReviewSheet": self.file_handler.upload_review_sheet,
            "searchFiles": self.file_handler.search_files,
            "listFiles": self.file_handler.list_files,
            "listTeamFiles": self.file_handler.list_team_files,
            "getWorkspacesAndTeams": self.file_handler.get_workspaces_and_teams,
            "listWorkspaces": self.file_handler.list_workspaces,
            "discoverWorkspacesAutomatically": self.file_handler.discover_workspaces_automatically,
            "discoverEverythingAutomatically": self.file_handler.discover_everything_automatically,
            "discoverAllTeamFolders": self.file_handler.discover_all_team_folders,
            "exploreAdvancedApiAccess": self.file_handler.explore_advanced_api_access,
            
            # Advanced exploration tools
            "exploreWebBasedTeamFolders": self.file_handler.explore_web_based_team_folders,
            "discoverHiddenTeamFolders": self.file_handler.discover_hidden_team_folders,
            "mimicBrowserApiCalls": self.file_handler.mimic_browser_api_calls,
            "exploitApiVulnerabilities": self.file_handler.exploit_api_vulnerabilities,
        }

        # Track processed requests to prevent duplicates
        self.processed_requests = set()
        
        logger.info(f"MCP handler initialized with {len(self.tools)} tools")

    async def handle_request(self, raw_request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming MCP JSON-RPC request.

        Args:
            raw_request: Raw JSON-RPC request

        Returns:
            JSON-RPC response
        """
        request_id = raw_request.get("id")

        try:
            # Parse and validate request
            request = MCPRequest(**raw_request)

            # Handle different method types
            if request.method == "initialize":
                return await self._handle_initialize(request)
            elif request.method == "tools/list":
                return await self._handle_tools_list(request)
            elif request.method == "resources/list":
                return await self._handle_resources_list(request)
            elif request.method == "prompts/list":
                return await self._handle_prompts_list(request)
            elif request.method == "initialized":
                return await self._handle_initialized(request)
            elif request.method == "notifications/initialized":
                return await self._handle_initialized(request)
            elif request.method == "tools/call":
                return await self._handle_tools_call(request)
            elif request.method == "callTool":
                return await self._handle_call_tool(request)
            elif request.method == "listTools":
                return await self._handle_list_tools(request)
            elif request.method == "ping":
                return await self._handle_ping(request)
            elif request.method == "listWorkspaces":
                return await self._list_workspaces(request)
            elif request.method == "discoverWorkspacesAutomatically":
                return await self._discover_workspaces_automatically(request)
            elif request.method == "discoverEverythingAutomatically":
                return await self._discover_everything_automatically(request)
            else:
                logger.warning(f"Unknown method: {request.method}")
                return MCPResponse(
                    error=MCPError.create_error(
                        MCPError.METHOD_NOT_FOUND,
                        f"Method '{request.method}' not found"
                    ),
                    id=request.id
                ).model_dump()

        except PydanticValidationError as e:
            logger.error(f"Invalid request format: {e}")
            return MCPResponse(
                error=MCPError.create_error(
                    MCPError.INVALID_REQUEST,
                    "Invalid request format",
                    str(e)
                ),
                id=request_id
            ).model_dump()

        except Exception as e:
            logger.error(f"Internal error handling request: {e}")
            return MCPResponse(
                error=MCPError.create_error(
                    MCPError.INTERNAL_ERROR,
                    "Internal server error"
                ),
                id=request_id
            ).model_dump()

    async def _handle_call_tool(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle callTool method.

        Args:
            request: MCP request

        Returns:
            Tool execution result
        """
        try:
            params = request.params or {}
            tool_name = params.get("name")
            tool_arguments = params.get("arguments", {})
            
            # Extract progressToken and _meta (these are MCP client metadata)
            progress_token = None
            if "_meta" in tool_arguments:
                meta = tool_arguments.pop("_meta")
                progress_token = meta.get("progressToken")
            if "progressToken" in tool_arguments:
                progress_token = tool_arguments.pop("progressToken")
            
            # Log progress token for debugging
            if progress_token is not None:
                logger.info(f"Processing request with progressToken: {progress_token}")

            if not tool_name:
                return MCPResponse(
                    result={
                        "content": [
                            {
                                "type": "text",
                                "text": "Error: Missing tool name"
                            }
                        ],
                        "isError": True
                    },
                    id=request.id
                ).model_dump()

            if tool_name not in self.tools:
                return MCPResponse(
                    result={
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Tool '{tool_name}' not found"
                            }
                        ],
                        "isError": True
                    },
                    id=request.id
                ).model_dump()

            # Execute tool
            logger.info(f"Executing tool: {tool_name}")
            tool_function = self.tools[tool_name]
            result = await tool_function(**tool_arguments)

            # Format result properly for MCP
            if isinstance(result, dict):
                # For structured data, return as JSON text
                import json
                result_text = json.dumps(result, indent=2, ensure_ascii=False)
                logger.info(f"Response size: {len(result_text)} bytes")
            else:
                result_text = str(result)

            # MCP tools/call response format
            response_data = {
                "content": [
                    {
                        "type": "text",
                        "text": result_text
                    }
                ]
            }
            
            # If progressToken was provided, indicate completion
            if progress_token is not None:
                logger.info(f"Completing request with progressToken: {progress_token}")
                # Add completion metadata to signal the client that processing is done
                response_data["_meta"] = {
                    "progressToken": progress_token,
                    "progress": 1.0,  # 100% complete
                    "completed": True
                }
            
            # Add isError flag for MCP compatibility (optional)
            if hasattr(self, '_is_error') and self._is_error:
                response_data["isError"] = True
            
            return MCPResponse(
                result=response_data,
                id=request.id
            ).model_dump()

        except TypeError as e:
            logger.error(f"Invalid tool arguments: {e}")
            return MCPResponse(
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Invalid tool arguments: {e}"
                        }
                    ],
                    "isError": True
                },
                id=request.id
            ).model_dump()

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            # Return error as content for MCP compatibility
            return MCPResponse(
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Tool execution failed: {e}"
                        }
                    ],
                    "isError": True
                },
                id=request.id
            ).model_dump()

    async def _handle_tools_list(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/list method for MCP protocol.

        Args:
            request: MCP request

        Returns:
            List of available tools in MCP format
        """
        tools_list = []

        # Define tool schemas for MCP compatibility
        tool_schemas = {
            "listProjects": {
                "name": "listProjects",
                "description": "List all available Zoho projects",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "listTasks": {
                "name": "listTasks",
                "description": "List tasks from a Zoho project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "status": {"type": "string", "enum": ["open", "closed", "overdue"], "description": "Task status filter (applied after fetching all tasks)"},
                        "get_all": {"type": "boolean", "description": "If true, fetch all tasks using pagination (default: true)", "default": True},
                        "index": {"type": "integer", "description": "Starting index for pagination (1-based, default: 1)", "default": 1},
                        "range": {"type": "integer", "description": "Number of tasks per page (max 200, default: 200)", "default": 200}
                    },
                    "required": ["project_id"]
                }
            },
            "createTask": {
                "name": "createTask",
                "description": "Create a new task in Zoho project",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "project_id": {"type": "string", "description": "Project ID"},
                        "name": {"type": "string", "description": "Task name"},
                        "owner": {"type": "string", "description": "Task owner"},
                        "due_date": {"type": "string", "format": "date", "description": "Due date"}
                    },
                    "required": ["project_id", "name"]
                }
            },
            "searchFiles": {
                "name": "searchFiles",
                "description": "Search files in WorkDrive",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "folder_id": {"type": "string", "description": "Folder ID to search in"}
                    },
                    "required": ["query"]
                }
            },
            "discoverWorkspacesAutomatically": {
                "name": "discoverWorkspacesAutomatically",
                "description": "Automatically discover all accessible workspaces using browser API patterns from HAR analysis",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "listWorkspaces": {
                "name": "listWorkspaces",
                "description": "List all accessible workspaces with detailed information",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            },
            "discoverEverythingAutomatically": {
                "name": "discoverEverythingAutomatically",
                "description": "Complete automatic discovery from zero knowledge - discovers organization, workspaces, Team Folders, and all files without requiring any pre-known IDs",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        }

        # Create tools list with proper schemas
        for tool_name in self.tools.keys():
            if tool_name in tool_schemas:
                tools_list.append(tool_schemas[tool_name])
            else:
                # Fallback for tools without specific schema
                tools_list.append({
                    "name": tool_name,
                    "description": f"Execute {tool_name} operation",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                })

        return MCPResponse(
            result={"tools": tools_list},
            id=request.id
        ).model_dump()

    async def _handle_list_tools(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle listTools method (legacy).

        Args:
            request: MCP request

        Returns:
            List of available tools
        """
        tools_list = [
            {
                "name": tool_name,
                "description": f"Execute {tool_name} operation"
            }
            for tool_name in self.tools.keys()
        ]

        return MCPResponse(
            result={"tools": tools_list},
            id=request.id
        ).model_dump()

    async def _handle_initialize(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle initialize method for MCP protocol setup.

        Args:
            request: MCP request

        Returns:
            Initialization response
        """
        logger.info("MCP protocol initialization requested")

        # Get client protocol version from request
        client_version = request.params.get("protocolVersion", "2024-11-05") if request.params else "2024-11-05"

        return MCPResponse(
            result={
                "protocolVersion": client_version,  # Match client version
                "capabilities": {
                    "tools": {},
                    "logging": {},
                    "prompts": {},
                    "resources": {},
                    "roots": {"listChanged": True}
                },
                "serverInfo": {
                    "name": "zoho-mcp-server",
                    "version": "0.1.0"
                }
            },
            id=request.id
        ).model_dump()

    async def _handle_tools_call(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle tools/call method (alias for callTool).

        Args:
            request: MCP request

        Returns:
            Tool execution result
        """
        # Delegate to existing callTool handler
        return await self._handle_call_tool(request)

    async def _handle_resources_list(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle resources/list method for MCP protocol.

        Args:
            request: MCP request

        Returns:
            List of available resources (empty for now)
        """
        return MCPResponse(
            result={"resources": []},
            id=request.id
        ).model_dump()

    async def _handle_prompts_list(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle prompts/list method for MCP protocol.

        Args:
            request: MCP request

        Returns:
            List of available prompts (empty for now)
        """
        return MCPResponse(
            result={"prompts": []},
            id=request.id
        ).model_dump()

    async def _handle_initialized(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle initialized notification.

        Args:
            request: MCP request

        Returns:
            None (notifications don't require response)
        """
        logger.info("MCP protocol initialization completed - client ready")
        # Notifications should not return a response
        return None

    async def _handle_ping(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle ping method for health check.

        Args:
            request: MCP request

        Returns:
            Pong response
        """
        return MCPResponse(
            result={"message": "pong"},
            id=request.id
        ).model_dump()

    async def _list_workspaces(self, request: MCPRequest) -> Dict[str, Any]:
        """List workspaces tool implementation."""
        try:
            result = await self.file_handler.list_workspaces()
            return MCPResponse(
                result=result,
                id=request.id
            ).model_dump()
        except Exception as e:
            logger.error(f"List workspaces failed: {e}")
            return MCPResponse(
                error=MCPError.create_error(MCPError.INTERNAL_ERROR, str(e)),
                id=request.id
            ).model_dump()

    async def _discover_workspaces_automatically(self, request: MCPRequest) -> Dict[str, Any]:
        """Automatically discover workspaces using browser API patterns."""
        try:
            result = await self.file_handler.discover_workspaces_automatically()
            return MCPResponse(
                result=result,
                id=request.id
            ).model_dump()
        except Exception as e:
            logger.error(f"Automatic workspace discovery failed: {e}")
            return MCPResponse(
                error=MCPError.create_error(MCPError.INTERNAL_ERROR, str(e)),
                id=request.id
            ).model_dump()

    async def _discover_everything_automatically(self, request: MCPRequest) -> Dict[str, Any]:
        """Automatically discover everything using browser API patterns."""
        try:
            result = await self.file_handler.discover_everything_automatically()
            return MCPResponse(
                result=result,
                id=request.id
            ).model_dump()
        except Exception as e:
            logger.error(f"Automatic everything discovery failed: {e}")
            return MCPResponse(
                error=MCPError.create_error(MCPError.INTERNAL_ERROR, str(e)),
                id=request.id
            ).model_dump()
