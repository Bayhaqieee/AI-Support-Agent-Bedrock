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
role_arn = "arn:aws:iam::016586718516:role/CustomerSupportGatewayRole"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
control = session.client("bedrock-agentcore-control")
apigw = session.client("apigateway")

api_name = "OrderTrackerRESTAPI"
apis = apigw.get_rest_apis()["items"]
api_id = [item["id"] for item in apis if item["name"] == api_name][0]

gateway_name = "CustomerSupportGateway"

existing_gateways = control.list_gateways().get("items", [])
gateway_id = None

for g in existing_gateways:
    if g["name"] == gateway_name:
        gateway_id = g["gatewayId"]
        print("Found existing Gateway:", gateway_id)
        if g.get("roleArn") != role_arn:
            print("Deleting targets for existing gateway...")
            targets = control.list_gateway_targets(gatewayIdentifier=gateway_id).get("items", [])
            for t in targets:
                t_id = t.get("targetId")
                print("Deleting target:", t_id)
                try:
                    control.delete_gateway_target(gatewayIdentifier=gateway_id, targetId=t_id)
                except Exception as e:
                    print("Error deleting target:", e)

            while True:
                rem = control.list_gateway_targets(gatewayIdentifier=gateway_id).get("items", [])
                if not rem:
                    break
                print("Waiting for target deletion...")
                time.sleep(3)

            print("Deleting existing gateway with old role...")
            control.delete_gateway(gatewayIdentifier=gateway_id)
            gateway_id = None
            time.sleep(5)

if not gateway_id:
    print("Creating Gateway with role:", role_arn)
    res = control.create_gateway(
        name=gateway_name,
        description="Customer Support AgentCore Gateway",
        protocolType="MCP",
        authorizerType="NONE",
        roleArn=role_arn
    )
    gateway_id = res["gatewayId"]
    print("Created Gateway:", gateway_id)

print("Waiting for Gateway to be READY/ACTIVE...")
while True:
    g_info = control.get_gateway(gatewayIdentifier=gateway_id)
    status = g_info.get("status")
    print("Current status:", status)
    if status in ["READY", "ACTIVE"]:
        break
    time.sleep(3)

gateway_url = g_info.get("gatewayUrl")

targets = control.list_gateway_targets(gatewayIdentifier=gateway_id).get("items", [])
target_names = [t["name"] for t in targets]

if "order-tracker" not in target_names and "order_tracker" not in target_names:
    print("Adding order-tracker target...")
    control.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="order-tracker",
        description="API Gateway target for order tracking",
        credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
        targetConfiguration={
            "mcp": {
                "apiGateway": {
                    "restApiId": api_id,
                    "stage": "prod",
                    "apiGatewayToolConfiguration": {
                        "toolFilters": [
                            {"filterPath": "/orders/{order_id}", "methods": ["GET"]},
                            {"filterPath": "/customers/{customer_id}/orders", "methods": ["GET"]},
                            {"filterPath": "/customers/{customer_id}", "methods": ["GET"]}
                        ]
                    }
                }
            }
        }
    )
    print("Added order-tracker target.")

if "refund-processor" not in target_names and "refund_processor" not in target_names:
    print("Adding refund-processor target...")
    with open("lambda/lambda_schema", "r", encoding="utf-8") as f:
        schema_json = json.load(f)

    refund_lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:refund-processor"
    control.create_gateway_target(
        gatewayIdentifier=gateway_id,
        name="refund-processor",
        description="Lambda target for refund processing",
        credentialProviderConfigurations=[{"credentialProviderType": "GATEWAY_IAM_ROLE"}],
        targetConfiguration={
            "mcp": {
                "lambda": {
                    "lambdaArn": refund_lambda_arn,
                    "toolSchema": {
                        "inlinePayload": schema_json
                    }
                }
            }
        }
    )
    print("Added refund-processor target.")

print("GATEWAY_URL =", gateway_url)
