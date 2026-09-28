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
iam = session.client("iam")

for r_name in ["voclabs", "vocareum", "vocstartsoft"]:
    try:
        r = iam.get_role(RoleName=r_name)
        print(f"Role {r_name} trust policy: {json.dumps(r['Role']['AssumeRolePolicyDocument'])}")
    except Exception as e:
        print(r_name, e)
