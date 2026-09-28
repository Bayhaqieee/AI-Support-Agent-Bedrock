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

tool_config = model.shape_for("ApiGatewayToolConfiguration")
print("ApiGatewayToolConfiguration shape members:", tool_config.members)
for name, member in tool_config.members.items():
    print(name, "->", member.name)
