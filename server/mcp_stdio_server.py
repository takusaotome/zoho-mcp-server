#!/Users/takueisaotome/PycharmProjects/zoho-mcp-server/venv/bin/python
"""Stdio-based MCP server for Cursor compatibility."""

import asyncio
import json
import logging
import sys
import tempfile
from pathlib import Path
from typing import Any

# Add project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from server.core.mcp_handler import MCPHandler

# Configure logging to file (stdout is used for MCP communication)
# Use secure temporary directory instead of hardcoded /tmp
log_dir = Path(tempfile.gettempdir()) / "mcp_server"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / "mcp_server.log"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(log_file), mode='a'),
        logging.StreamHandler(sys.stderr)  # Also log to stderr for debugging
    ]
)
logger = logging.getLogger(__name__)


class StdioMCPServer:
    """Stdio-based MCP server for Cursor compatibility."""

    def __init__(self):
        """Initialize the stdio MCP server."""
        try:
            self.mcp_handler = MCPHandler()
            logger.info("Stdio MCP server initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize MCP server: {e}")
            raise

    async def handle_request(self, request_data: dict[str, Any]) -> dict[str, Any]:
        """Handle a single MCP request.

        Args:
            request_data: The JSON-RPC request

        Returns:
            The JSON-RPC response
        """
        try:
            response = await self.mcp_handler.handle_request(request_data)
            return response
        except Exception as e:
            logger.error(f"Request handling failed: {e}")
            return {
                "jsonrpc": "2.0",
                "error": {
                    "code": -32603,
                    "message": "Internal error"
                },
                "id": request_data.get("id")
            }

    async def run(self):
        """Run the stdio MCP server main loop."""
        logger.info("Starting stdio MCP server...")
        logger.info(f"Working directory: {Path.cwd()}")
        logger.info(f"Python executable: {sys.executable}")
        logger.info(f"Python path: {sys.path[:3]}...")
        
        try:
            while True:
                # Read request from stdin
                try:
                    line = await asyncio.get_event_loop().run_in_executor(
                        None, sys.stdin.readline
                    )

                    if not line:
                        logger.info("EOF received, shutting down")
                        break

                    line = line.strip()
                    if not line:
                        continue

                    logger.info(f"Received request: {line}")

                    # Parse JSON request
                    try:
                        request_data = json.loads(line)
                        logger.info(f"Parsed request - method: {request_data.get('method')}, id: {request_data.get('id')}")
                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid JSON: {e}")
                        continue

                    # Handle request
                    try:
                        response = await self.handle_request(request_data)
                        if response is not None:
                            logger.info(f"Generated response for {request_data.get('method')}: {json.dumps(response)[:200]}...")
                        else:
                            logger.info(f"No response needed for notification: {request_data.get('method')}")
                    except Exception as e:
                        logger.error(f"Error handling request: {e}")
                        response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": f"Internal error: {str(e)}"
                            },
                            "id": request_data.get("id")
                        }

                    # Send response to stdout (only if response is not None)
                    if response is not None:
                        response_json = json.dumps(response, separators=(',', ':'), ensure_ascii=False)
                        print(response_json)
                        sys.stdout.flush()  # Ensure immediate delivery

                        logger.info(f"Sent response for method: {request_data.get('method', 'unknown')}")
                        logger.info(f"Response size: {len(response_json)} bytes")
                        logger.info(f"Response ID: {response.get('id')}")
                        logger.info("Response flushed to stdout")
                    else:
                        logger.info("Notification processed, no response sent: %s", request_data.get('method', 'unknown'))

                except Exception as e:
                    logger.error(f"Error in main loop: {e}")
                    # Send error response instead of crashing
                    try:
                        error_response = {
                            "jsonrpc": "2.0",
                            "error": {
                                "code": -32603,
                                "message": f"Server error: {str(e)}"
                            },
                            "id": None
                        }
                        print(json.dumps(error_response, separators=(',', ':')))
                        sys.stdout.flush()
                    except Exception as json_error:
                        logger.error(f"Failed to send error response: {json_error}")
                        pass
                    continue

        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        except Exception as e:
            logger.error(f"Server error: {e}")
        finally:
            logger.info("Stdio MCP server shutting down")


async def main():
    """Main entry point."""
    server = StdioMCPServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
