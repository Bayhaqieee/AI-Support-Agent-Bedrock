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
apigw = session.client("apigateway")
control = session.client("bedrock-agentcore-control")

api_id = "qcgrynusr4"
resources = apigw.get_resources(restApiId=api_id)["items"]

for r in resources:
    res_id = r["id"]
    path = r["path"]
    methods = r.get("resourceMethods", {})
    if "GET" in methods:
        print(f"Adding 200 method response to {path} ({res_id})...")
        try:
            apigw.put_method_response(
                restApiId=api_id,
                resourceId=res_id,
                httpMethod="GET",
                statusCode="200",
                responseModels={"application/json": "Empty"}
            )
            print(f"Added 200 response to {path}")
        except apigw.exceptions.ConflictException:
            print(f"200 response already exists for {path}")
        except Exception as e:
            print(f"Error on {path}: {e}")

apigw.create_deployment(restApiId=api_id, stageName="prod")
print("Re-deployed REST API to stage prod")

# Now update the Gateway target
gateway_name = "CustomerSupportGateway"
gateway_id = [g["gatewayId"] for g in control.list_gateways().get("items", []) if g["name"] == gateway_name][0]
targets = control.list_gateway_targets(gatewayIdentifier=gateway_id).get("items", [])
t_id = [t["targetId"] for t in targets if t["name"] == "order-tracker"][0]

print("Updating order-tracker target in Gateway...")
control.update_gateway_target(
    gatewayIdentifier=gateway_id,
    targetId=t_id,
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
    print(f"Target status ({i}):", status, t_detail.get("statusReasons"))
    if status in ["READY", "FAILED", "UPDATE_UNSUCCESSFUL"]:
        break
    time.sleep(3)
