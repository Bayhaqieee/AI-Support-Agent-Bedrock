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

doc = control.meta.service_model.operation_model("CreateGateway")
print("CreateGateway input shape:", doc.input_shape.members if doc.input_shape else None)

doc_target = control.meta.service_model.operation_model("CreateGatewayTarget")
print("CreateGatewayTarget input shape:", doc_target.input_shape.members if doc_target.input_shape else None)
