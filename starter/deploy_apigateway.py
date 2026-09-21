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
lambda_function_name = "order-tracker"
lambda_arn = f"arn:aws:lambda:{region}:{account_id}:function:{lambda_function_name}"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
apigw = session.client("apigateway")
lambda_client = session.client("lambda")

api_name = "OrderTrackerRESTAPI"

apis = apigw.get_rest_apis()["items"]
api_id = None
for item in apis:
    if item["name"] == api_name:
        api_id = item["id"]
        print("Found existing REST API:", api_id)
        break

if not api_id:
    res = apigw.create_rest_api(name=api_name, description="REST API for Order Tracker")
    api_id = res["id"]
    print("Created REST API:", api_id)

resources = apigw.get_resources(restApiId=api_id)["items"]
root_id = [r["id"] for r in resources if r["path"] == "/"][0]

def get_or_create_resource(path_part, parent_id):
    current_resources = apigw.get_resources(restApiId=api_id)["items"]
    for r in current_resources:
        if r.get("parentId") == parent_id and r.get("pathPart") == path_part:
            return r["id"]
    res = apigw.create_resource(restApiId=api_id, parentId=parent_id, pathPart=path_part)
    return res["id"]

orders_res_id = get_or_create_resource("orders", root_id)
order_id_res_id = get_or_create_resource("{order_id}", orders_res_id)

customers_res_id = get_or_create_resource("customers", root_id)
customer_id_res_id = get_or_create_resource("{customer_id}", customers_res_id)
cust_orders_res_id = get_or_create_resource("orders", customer_id_res_id)

uri = f"arn:aws:apigateway:{region}:lambda:path/2015-03-31/functions/{lambda_arn}/invocations"

def setup_method_and_integration(resource_id, http_method, operation_name):
    try:
        apigw.get_method(restApiId=api_id, resourceId=resource_id, httpMethod=http_method)
        print(f"Method {http_method} already exists for resource {resource_id}")
    except apigw.exceptions.NotFoundException:
        apigw.put_method(
            restApiId=api_id,
            resourceId=resource_id,
            httpMethod=http_method,
            authorizationType="NONE",
            operationName=operation_name
        )
        print(f"Created method {http_method} (op: {operation_name})")

    apigw.put_integration(
        restApiId=api_id,
        resourceId=resource_id,
        httpMethod=http_method,
        type="AWS_PROXY",
        integrationHttpMethod="POST",
        uri=uri
    )
    print(f"Set AWS_PROXY integration for {operation_name}")

setup_method_and_integration(order_id_res_id, "GET", "get_order")
setup_method_and_integration(customer_id_res_id, "GET", "get_customer")
setup_method_and_integration(cust_orders_res_id, "GET", "get_customer_orders")

try:
    lambda_client.add_permission(
        FunctionName=lambda_function_name,
        StatementId="apigateway-invoke-permission",
        Action="lambda:InvokeFunction",
        Principal="apigateway.amazonaws.com",
        SourceArn=f"arn:aws:execute-api:{region}:{account_id}:{api_id}/*/*/*"
    )
    print("Added API Gateway permission to Lambda")
except lambda_client.exceptions.ResourceConflictException:
    print("API Gateway permission already exists on Lambda")

deployment = apigw.create_deployment(restApiId=api_id, stageName="prod")
print(f"Deployed REST API {api_id} to stage prod")
print(f"REST API ID: {api_id}")
