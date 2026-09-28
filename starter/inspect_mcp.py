import os
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
control = session.client("bedrock-agentcore-control")
model = control.meta.service_model

mcp_shape = model.shape_for("McpTargetConfiguration")
print("McpTargetConfiguration members:", list(mcp_shape.members.keys()))
for name, member in mcp_shape.members.items():
    print(" ", name, "->", member.name, getattr(member, 'members', {}).keys() if hasattr(member, 'members') else '')
