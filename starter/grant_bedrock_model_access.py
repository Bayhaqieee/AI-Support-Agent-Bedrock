import os
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"
role_name = "CustomerSupportGatewayRole"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
iam = session.client("iam")

policy_arn = "arn:aws:iam::aws:policy/AmazonBedrockFullAccess"
try:
    iam.attach_role_policy(RoleName=role_name, PolicyArn=policy_arn)
    print("Attached AmazonBedrockFullAccess to", role_name)
except Exception as e:
    print("Error attaching policy:", e)
