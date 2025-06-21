"""Unit tests for MCP handler."""

from unittest.mock import AsyncMock, patch

import pytest

from server.core.mcp_handler import MCPError, MCPHandler


class TestMCPHandler:
    """Test MCP handler functionality."""

    @pytest.fixture
    def mcp_handler(self):
        """Create MCP handler instance."""
        return MCPHandler()

    @pytest.mark.asyncio
    @patch('server.core.mcp_handler.MCPHandler.__init__', return_value=None)
    async def test_handle_ping_request(self, mock_init):
        """Test ping request handling."""
        # Create handler without initializing dependencies
        mcp_handler = MCPHandler.__new__(MCPHandler)
        mcp_handler.tools = {}

        request = {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": "test_001"
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test_001"
        assert response["result"]["message"] == "pong"
        assert response.get("error") is None

    @pytest.mark.asyncio
    async def test_handle_list_tools(self, mcp_handler):
        """Test list tools request."""
        request = {
            "jsonrpc": "2.0",
            "method": "listTools",
            "id": "test_002"
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test_002"
        assert "tools" in response["result"]
        assert len(response["result"]["tools"]) > 0

    @pytest.mark.asyncio
    async def test_handle_call_tool_missing_name(self, mcp_handler):
        """Test call tool without tool name."""
        request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "arguments": {}
            },
            "id": "test_003"
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test_003"
        assert "error" in response
        assert response["error"]["code"] == MCPError.INVALID_PARAMS

    @pytest.mark.asyncio
    async def test_handle_call_tool_unknown_tool(self, mcp_handler):
        """Test call tool with unknown tool name."""
        request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "unknownTool",
                "arguments": {}
            },
            "id": "test_004"
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test_004"
        assert "error" in response
        assert response["error"]["code"] == MCPError.METHOD_NOT_FOUND

    @pytest.mark.asyncio
    @patch('server.core.mcp_handler.MCPHandler.__init__', return_value=None)
    async def test_handle_call_tool_success(self, mock_init):
        """Test successful tool call."""
        # Create handler with mocked tools
        mcp_handler = MCPHandler.__new__(MCPHandler)
        mcp_handler.tools = {
            "listTasks": AsyncMock(return_value={
                "project_id": "test_project",
                "tasks": [],
                "total_count": 0
            })
        }

        request = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "test_project"
                }
            },
            "id": "test_005"
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test_005"
        assert "result" in response
        assert "content" in response["result"]
        mcp_handler.tools["listTasks"].assert_called_once_with(project_id="test_project")

    @pytest.mark.asyncio
    async def test_handle_unknown_method(self, mcp_handler):
        """Test unknown method handling."""
        request = {
            "jsonrpc": "2.0",
            "method": "unknownMethod",
            "id": "test_006"
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert response["id"] == "test_006"
        assert "error" in response
        assert response["error"]["code"] == MCPError.METHOD_NOT_FOUND

    @pytest.mark.asyncio
    async def test_handle_invalid_request(self, mcp_handler):
        """Test invalid request format."""
        request = {
            "invalid": "request"
        }

        response = await mcp_handler.handle_request(request)

        assert response["jsonrpc"] == "2.0"
        assert "error" in response
        assert response["error"]["code"] == MCPError.INVALID_REQUEST
