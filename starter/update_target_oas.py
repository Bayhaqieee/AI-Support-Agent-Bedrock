import json
import os
import time
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"
account_id = "016586718516"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
control = session.client("bedrock-agentcore-control")
apigw = session.client("apigateway")

export = apigw.get_export(restApiId="qcgrynusr4", stageName="prod", exportType="oas30")
oas_spec = export["body"].read().decode("utf-8")

gateway_name = "CustomerSupportGateway"
gateway_id = [g["gatewayId"] for g in control.list_gateways().get("items", []) if g["name"] == gateway_name][0]

targets = control.list_gateway_targets(gatewayIdentifier=gateway_id).get("items", [])
order_target = [t for t in targets if t["name"] == "order-tracker"]

if order_target:
    t_id = order_target[0]["targetId"]
    print("Updating order-tracker target:", t_id)
    control.update_gateway_target(
        gatewayIdentifier=gateway_id,
        targetId=t_id,
        name="order-tracker",
        description="API Gateway target for order tracking",
        credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
        targetConfiguration={
            "mcp": {
                "openApiSchema": {
                    "inlinePayload": oas_spec
                }
            }
        }
    )
    print("Updated order-tracker target using openApiSchema")

print("Waiting for target to be READY...")
while True:
    t_detail = control.get_gateway_target(gatewayIdentifier=gateway_id, targetId=t_id)
    status = t_detail.get("status")
    print("Target status:", status)
    if status in ["READY", "FAILED"]:
        break
    time.sleep(3)
