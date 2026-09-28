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

iam = session.client("iam")
roles = iam.list_roles()["Roles"]
print("Available IAM Roles:")
for r in roles:
    print(r["RoleName"], r["Arn"])

sts = session.client("sts")
identity = sts.get_caller_identity()
print("Identity Arn:", identity["Arn"])
