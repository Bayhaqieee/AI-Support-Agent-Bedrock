import inspect
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

print("MCPClient init signature:", inspect.signature(MCPClient.__init__))
