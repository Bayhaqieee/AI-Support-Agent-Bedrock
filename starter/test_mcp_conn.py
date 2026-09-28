import os
import dotenv
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamable_http_client

dotenv.load_dotenv("../.env")

gateway_url = "https://customersupportgateway-eeqgr9w2fn.gateway.bedrock-agentcore.us-east-1.amazonaws.com/mcp"

with MCPClient(lambda: streamable_http_client(gateway_url)) as client:
    tools = client.list_tools_sync()
    for t in tools:
        print("Tool name:", t.tool_name)
