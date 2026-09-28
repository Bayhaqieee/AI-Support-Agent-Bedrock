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
gateway_name = "CustomerSupportGateway"
gateway_id = [g["gatewayId"] for g in control.list_gateways().get("items", []) if g["name"] == gateway_name][0]

targets = control.list_gateway_targets(gatewayIdentifier=gateway_id).get("items", [])
for t in targets:
    t_detail = control.get_gateway_target(gatewayIdentifier=gateway_id, targetId=t["targetId"])
    print("Target:", t["name"], t_detail.get("status"), t_detail)
