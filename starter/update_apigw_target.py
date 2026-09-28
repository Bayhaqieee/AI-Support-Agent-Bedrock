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
                "apiGateway": {
                    "restApiId": "qcgrynusr4",
                    "stage": "prod",
                    "apiGatewayToolConfiguration": {
                        "toolFilters": [
                            {"filterPath": "/orders/{order_id}", "methods": ["GET"]},
                            {"filterPath": "/customers/{customer_id}", "methods": ["GET"]},
                            {"filterPath": "/customers/{customer_id}/orders", "methods": ["GET"]}
                        ]
                    }
                }
            }
        }
    )

print("Waiting for target status...")
for i in range(10):
    t_detail = control.get_gateway_target(gatewayIdentifier=gateway_id, targetId=t_id)
    status = t_detail.get("status")
    print(f"Status ({i}):", status, t_detail.get("statusReasons"))
    if status in ["READY", "FAILED", "UPDATE_UNSUCCESSFUL"]:
        break
    time.sleep(3)
