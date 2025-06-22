"""Unit tests for MCP Stdio server."""

import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open

import pytest

from server.mcp_stdio_server import StdioMCPServer


class TestStdioMCPServer:
    """Test MCP Stdio server."""

    @pytest.fixture
    def mock_mcp_handler(self):
        """Create mock MCP handler."""
        with patch('server.mcp_stdio_server.MCPHandler') as mock_handler_class:
            mock_handler = AsyncMock()
            mock_handler_class.return_value = mock_handler
            yield mock_handler

    @pytest.fixture
    def server(self, mock_mcp_handler):
        """Create stdio server instance."""
        return StdioMCPServer()

    def test_initialization_success(self, mock_mcp_handler):
        """Test successful server initialization."""
        server = StdioMCPServer()
        
        assert server.mcp_handler is not None
        assert server.mcp_handler == mock_mcp_handler

    def test_initialization_failure(self):
        """Test server initialization failure."""
        with patch('server.mcp_stdio_server.MCPHandler', side_effect=Exception("Handler init failed")):
            with pytest.raises(Exception, match="Handler init failed"):
                StdioMCPServer()

    @pytest.mark.asyncio
    async def test_handle_request_success(self, server, mock_mcp_handler):
        """Test successful request handling."""
        # Setup mock response
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"tools": []},
            "id": 1
        }
        mock_mcp_handler.handle_request.return_value = mock_response

        # Test request
        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }

        result = await server.handle_request(request_data)

        # Verify
        assert result == mock_response
        mock_mcp_handler.handle_request.assert_called_once_with(request_data)

    @pytest.mark.asyncio
    async def test_handle_request_exception(self, server, mock_mcp_handler):
        """Test request handling with exception."""
        # Setup mock to raise exception
        mock_mcp_handler.handle_request.side_effect = Exception("Handler error")

        request_data = {
            "jsonrpc": "2.0",
            "method": "tools/list",
            "id": 1
        }

        result = await server.handle_request(request_data)

        # Verify error response
        assert result["jsonrpc"] == "2.0"
        assert result["error"]["code"] == -32603
        assert result["error"]["message"] == "Internal error"
        assert result["id"] == 1

    @pytest.mark.asyncio
    async def test_handle_request_no_id(self, server, mock_mcp_handler):
        """Test request handling without ID (notification)."""
        mock_mcp_handler.handle_request.side_effect = Exception("Handler error")

        request_data = {
            "jsonrpc": "2.0",
            "method": "initialized"
        }

        result = await server.handle_request(request_data)

        # Verify error response includes None ID
        assert result["id"] is None

    @pytest.mark.asyncio
    async def test_run_single_request_success(self, server, mock_mcp_handler):
        """Test main loop with single successful request."""
        # Mock stdin readline
        mock_stdin_readline = Mock()
        mock_stdin_readline.side_effect = [
            '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}\n',
            ''  # EOF
        ]

        # Mock MCP handler response
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"tools": []},
            "id": 1
        }
        mock_mcp_handler.handle_request.return_value = mock_response

        with patch('sys.stdin.readline', mock_stdin_readline), \
             patch('builtins.print') as mock_print, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            # Mock executor to run synchronously
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            await server.run()

            # Verify print was called with response
            mock_print.assert_called_once_with(
                '{"jsonrpc":"2.0","result":{"tools":[]},"id":1}',
                flush=True
            )

    @pytest.mark.asyncio
    async def test_run_invalid_json(self, server, mock_mcp_handler):
        """Test main loop with invalid JSON input."""
        mock_stdin_readline = Mock()
        mock_stdin_readline.side_effect = [
            'invalid json\n',
            ''  # EOF
        ]

        with patch('sys.stdin.readline', mock_stdin_readline), \
             patch('builtins.print') as mock_print, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            await server.run()

            # Verify no print was called (invalid JSON is skipped)
            mock_print.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_empty_lines(self, server, mock_mcp_handler):
        """Test main loop with empty lines."""
        mock_stdin_readline = Mock()
        mock_stdin_readline.side_effect = [
            '\n',  # Empty line
            '   \n',  # Whitespace only
            ''  # EOF
        ]

        with patch('sys.stdin.readline', mock_stdin_readline), \
             patch('builtins.print') as mock_print, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            await server.run()

            # Verify no print was called (empty lines are skipped)
            mock_print.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_request_handling_exception(self, server, mock_mcp_handler):
        """Test main loop with request handling exception."""
        mock_stdin_readline = Mock()
        mock_stdin_readline.side_effect = [
            '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}\n',
            ''  # EOF
        ]

        # Mock handler to raise exception
        mock_mcp_handler.handle_request.side_effect = Exception("Handler crashed")

        with patch('sys.stdin.readline', mock_stdin_readline), \
             patch('builtins.print') as mock_print, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            await server.run()

            # Verify error response was printed
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            error_response = json.loads(call_args)
            
            assert error_response["jsonrpc"] == "2.0"
            assert error_response["error"]["code"] == -32603
            assert "Internal error: Handler crashed" in error_response["error"]["message"]
            assert error_response["id"] == 1

    @pytest.mark.asyncio
    async def test_run_notification_no_response(self, server, mock_mcp_handler):
        """Test main loop with notification (no response expected)."""
        mock_stdin_readline = Mock()
        mock_stdin_readline.side_effect = [
            '{"jsonrpc": "2.0", "method": "initialized"}\n',
            ''  # EOF
        ]

        # Mock handler to return None (notification)
        mock_mcp_handler.handle_request.return_value = None

        with patch('sys.stdin.readline', mock_stdin_readline), \
             patch('builtins.print') as mock_print, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            await server.run()

            # Verify no print was called (notification has no response)
            mock_print.assert_not_called()

    @pytest.mark.asyncio
    async def test_run_keyboard_interrupt(self, server):
        """Test main loop with keyboard interrupt."""
        mock_stdin_readline = Mock()
        mock_stdin_readline.side_effect = KeyboardInterrupt()

        with patch('sys.stdin.readline', mock_stdin_readline), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            # Should not raise exception
            await server.run()

    @pytest.mark.asyncio
    async def test_run_main_loop_exception(self, server):
        """Test main loop with unexpected exception."""
        with patch('sys.stdin.readline', side_effect=Exception("Unexpected error")), \
             patch('builtins.print') as mock_print, \
             patch('sys.stdout.flush') as mock_flush, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            await server.run()

            # Verify error response was printed
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            error_response = json.loads(call_args)
            
            assert error_response["jsonrpc"] == "2.0"
            assert error_response["error"]["code"] == -32603
            assert "Server error: Unexpected error" in error_response["error"]["message"]
            assert error_response["id"] is None

    @pytest.mark.asyncio
    async def test_run_json_dump_error(self, server):
        """Test main loop with JSON serialization error in error response."""
        with patch('sys.stdin.readline', side_effect=Exception("Unexpected error")), \
             patch('builtins.print', side_effect=Exception("Print failed")), \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            # Should not raise exception even when error response fails
            await server.run()

    def test_logging_configuration(self):
        """Test that logging is configured properly."""
        # Verify that logging is configured to use a temp directory
        with patch('tempfile.gettempdir', return_value='/tmp/test'), \
             patch('pathlib.Path.mkdir') as mock_mkdir, \
             patch('logging.basicConfig') as mock_basic_config:
            
            # Import to trigger logging configuration
            import importlib
            import server.mcp_stdio_server
            importlib.reload(server.mcp_stdio_server)

            # Verify temp directory creation
            mock_mkdir.assert_called_once_with(exist_ok=True)
            
            # Verify logging configuration
            mock_basic_config.assert_called_once()
            call_kwargs = mock_basic_config.call_args[1]
            assert call_kwargs['level'] == logging.INFO
            assert 'filename' in call_kwargs
            assert call_kwargs['filemode'] == 'a'

    @pytest.mark.asyncio
    async def test_main_function(self):
        """Test main function."""
        with patch('server.mcp_stdio_server.StdioMCPServer') as mock_server_class:
            mock_server = AsyncMock()
            mock_server_class.return_value = mock_server

            from server.mcp_stdio_server import main
            await main()

            mock_server_class.assert_called_once()
            mock_server.run.assert_called_once()

    @pytest.mark.asyncio
    async def test_complex_json_response(self, server, mock_mcp_handler):
        """Test handling complex JSON response with Unicode characters."""
        mock_stdin_readline = Mock()
        mock_stdin_readline.side_effect = [
            '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}\n',
            ''  # EOF
        ]

        # Mock response with Unicode characters
        mock_response = {
            "jsonrpc": "2.0",
            "result": {
                "tools": [
                    {
                        "name": "測試テスト",
                        "description": "Test with 日本語 characters"
                    }
                ]
            },
            "id": 1
        }
        mock_mcp_handler.handle_request.return_value = mock_response

        with patch('sys.stdin.readline', mock_stdin_readline), \
             patch('builtins.print') as mock_print, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            await server.run()

            # Verify Unicode handling in JSON response
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            
            # Should be valid JSON with Unicode characters
            parsed_response = json.loads(call_args)
            assert parsed_response["result"]["tools"][0]["name"] == "測試テスト"
            assert "日本語" in parsed_response["result"]["tools"][0]["description"]

    @pytest.mark.asyncio
    async def test_large_response_handling(self, server, mock_mcp_handler):
        """Test handling of large response data."""
        mock_stdin_readline = Mock()
        mock_stdin_readline.side_effect = [
            '{"jsonrpc": "2.0", "method": "tools/list", "id": 1}\n',
            ''  # EOF
        ]

        # Mock large response
        large_data = "x" * 10000  # 10KB of data
        mock_response = {
            "jsonrpc": "2.0",
            "result": {"large_field": large_data},
            "id": 1
        }
        mock_mcp_handler.handle_request.return_value = mock_response

        with patch('sys.stdin.readline', mock_stdin_readline), \
             patch('builtins.print') as mock_print, \
             patch('asyncio.get_event_loop') as mock_loop:
            
            def run_in_executor(executor, func):
                return func()
            
            mock_loop.return_value.run_in_executor.side_effect = run_in_executor

            await server.run()

            # Verify large response is handled correctly
            mock_print.assert_called_once()
            call_args = mock_print.call_args[0][0]
            
            # Should contain the large data
            parsed_response = json.loads(call_args)
            assert len(parsed_response["result"]["large_field"]) == 10000