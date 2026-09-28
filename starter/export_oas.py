import json
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
apigw = session.client("apigateway")
export = apigw.get_export(
    restApiId="qcgrynusr4",
    stageName="prod",
    exportType="oas30"
)
body = export["body"].read().decode("utf-8")
print("Exported OpenAPI:")
print(body)
