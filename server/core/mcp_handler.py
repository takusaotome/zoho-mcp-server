"""MCP (Model Context Protocol) handler for JSON-RPC requests."""

import logging
from typing import Any, Dict, Optional, Union

from pydantic import BaseModel, ValidationError

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
        }

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
            if request.method == "callTool":
                return await self._handle_call_tool(request)
            elif request.method == "listTools":
                return await self._handle_list_tools(request)
            elif request.method == "ping":
                return await self._handle_ping(request)
            else:
                logger.warning(f"Unknown method: {request.method}")
                return MCPResponse(
                    error=MCPError.create_error(
                        MCPError.METHOD_NOT_FOUND,
                        f"Method '{request.method}' not found"
                    ),
                    id=request.id
                ).model_dump()

        except ValidationError as e:
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

            if not tool_name:
                return MCPResponse(
                    error=MCPError.create_error(
                        MCPError.INVALID_PARAMS,
                        "Missing tool name"
                    ),
                    id=request.id
                ).model_dump()

            if tool_name not in self.tools:
                return MCPResponse(
                    error=MCPError.create_error(
                        MCPError.METHOD_NOT_FOUND,
                        f"Tool '{tool_name}' not found"
                    ),
                    id=request.id
                ).model_dump()

            # Execute tool
            logger.info(f"Executing tool: {tool_name}")
            tool_function = self.tools[tool_name]
            result = await tool_function(**tool_arguments)

            return MCPResponse(
                result={
                    "content": [
                        {
                            "type": "text",
                            "text": str(result)
                        }
                    ]
                },
                id=request.id
            ).model_dump()

        except TypeError as e:
            logger.error(f"Invalid tool arguments: {e}")
            return MCPResponse(
                error=MCPError.create_error(
                    MCPError.INVALID_PARAMS,
                    f"Invalid tool arguments: {e}"
                ),
                id=request.id
            ).model_dump()

        except Exception as e:
            logger.error(f"Tool execution failed: {e}")
            return MCPResponse(
                error=MCPError.create_error(
                    MCPError.INTERNAL_ERROR,
                    f"Tool execution failed: {e}"
                ),
                id=request.id
            ).model_dump()

    async def _handle_list_tools(self, request: MCPRequest) -> Dict[str, Any]:
        """Handle listTools method.

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
