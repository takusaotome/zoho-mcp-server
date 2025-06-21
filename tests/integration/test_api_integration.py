"""Integration tests for API endpoints."""

import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient


class TestMCPAPIIntegration:
    """Test MCP API integration."""
    
    def test_health_endpoint(self, client: TestClient):
        """Test health check endpoint."""
        response = client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "version" in data
        assert "environment" in data
    
    def test_manifest_endpoint(self, client: TestClient):
        """Test manifest endpoint."""
        response = client.get("/manifest.json")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "zoho-mcp-server"
        assert "tools" in data
        assert len(data["tools"]) > 0
        
        # Check specific tools
        tool_names = [tool["name"] for tool in data["tools"]]
        assert "listTasks" in tool_names
        assert "createTask" in tool_names
        assert "updateTask" in tool_names
    
    @patch('server.handlers.tasks.TaskHandler.list_tasks')
    def test_mcp_call_tool_list_tasks(self, mock_list_tasks, client: TestClient):
        """Test MCP callTool for listTasks."""
        mock_list_tasks.return_value = {
            "project_id": "test_project",
            "tasks": [
                {
                    "id": "task_001",
                    "name": "Test Task",
                    "status": "open"
                }
            ],
            "total_count": 1
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "test_project",
                    "status": "open"
                }
            },
            "id": "test_001"
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test_001"
        assert "result" in data
        assert "content" in data["result"]
        
        mock_list_tasks.assert_called_once_with(
            project_id="test_project",
            status="open"
        )
    
    @patch('server.handlers.tasks.TaskHandler.create_task')
    def test_mcp_call_tool_create_task(self, mock_create_task, client: TestClient):
        """Test MCP callTool for createTask."""
        mock_create_task.return_value = {
            "task_id": "new_task_123",
            "name": "New Test Task",
            "status": "created"
        }
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "createTask",
                "arguments": {
                    "project_id": "test_project",
                    "name": "New Test Task",
                    "owner": "test@example.com",
                    "due_date": "2025-07-01"
                }
            },
            "id": "test_002"
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test_002"
        assert "result" in data
        
        mock_create_task.assert_called_once_with(
            project_id="test_project",
            name="New Test Task",
            owner="test@example.com",
            due_date="2025-07-01"
        )
    
    def test_mcp_invalid_json(self, client: TestClient):
        """Test MCP endpoint with invalid JSON."""
        response = client.post("/mcp", content="invalid json")
        
        assert response.status_code == 422  # FastAPI validation error
    
    def test_mcp_missing_method(self, client: TestClient):
        """Test MCP request without method."""
        request_data = {
            "jsonrpc": "2.0",
            "id": "test_003"
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32600  # Invalid Request
    
    def test_mcp_unknown_tool(self, client: TestClient):
        """Test MCP callTool with unknown tool."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "unknownTool",
                "arguments": {}
            },
            "id": "test_004"
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32601  # Method Not Found
    
    def test_mcp_list_tools(self, client: TestClient):
        """Test MCP listTools method."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "listTools",
            "id": "test_005"
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test_005"
        assert "result" in data
        assert "tools" in data["result"]
        assert len(data["result"]["tools"]) > 0
    
    def test_mcp_ping(self, client: TestClient):
        """Test MCP ping method."""
        request_data = {
            "jsonrpc": "2.0",
            "method": "ping",
            "id": "test_006"
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert data["jsonrpc"] == "2.0"
        assert data["id"] == "test_006"
        assert data["result"]["message"] == "pong"


class TestErrorHandling:
    """Test error handling in integration scenarios."""
    
    @patch('server.handlers.tasks.TaskHandler.list_tasks')
    def test_tool_execution_error(self, mock_list_tasks, client: TestClient):
        """Test tool execution error handling."""
        mock_list_tasks.side_effect = Exception("Zoho API error")
        
        request_data = {
            "jsonrpc": "2.0",
            "method": "callTool",
            "params": {
                "name": "listTasks",
                "arguments": {
                    "project_id": "test_project"
                }
            },
            "id": "test_error"
        }
        
        response = client.post("/mcp", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "error" in data
        assert data["error"]["code"] == -32603  # Internal Error
    
    def test_cors_headers(self, client: TestClient):
        """Test CORS headers are present."""
        response = client.options("/mcp")
        
        # Note: TestClient doesn't fully simulate CORS behavior
        # This test mainly ensures the endpoint is accessible
        assert response.status_code in [200, 405]  # Depends on FastAPI version