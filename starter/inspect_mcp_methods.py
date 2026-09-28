import asyncio
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

gateway_url = "https://customersupportgateway-eeqgr9w2fn.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

client = MCPClient(lambda: streamable_http_client(gateway_url))
print("MCPClient methods:", [m for m in dir(client) if not m.startswith("_")])
