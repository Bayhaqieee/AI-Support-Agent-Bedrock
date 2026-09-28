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

def get_or_create_lambda_role():
    role_name = "CustomerSupportLambdaRole"
    trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"Service": "lambda.amazonaws.com"},
                "Action": "sts:AssumeRole"
            }
        ]
    }
    try:
        r = iam.get_role(RoleName=role_name)
        print("Using existing role:", r["Role"]["Arn"])
        return r["Role"]["Arn"]
    except Exception:
        pass

    try:
        r = iam.create_role(
            RoleName=role_name,
            AssumeRolePolicyDocument=json.dumps(trust_policy)
        )
        iam.attach_role_policy(
            RoleName=role_name,
            PolicyArn="arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
        )
        print("Created role:", r["Role"]["Arn"])
        return r["Role"]["Arn"]
    except Exception as e:
        print("Failed to create role:", e)
        # Check all existing roles for lambda.amazonaws.com in trust policy
        roles = iam.list_roles()["Roles"]
        for role in roles:
            policy = role.get("AssumeRolePolicyDocument", {})
            policy_str = json.dumps(policy)
            if "lambda.amazonaws.com" in policy_str:
                print("Found Lambda-compatible role:", role["RoleName"], role["Arn"])
                return role["Arn"]
        return None

role_arn = get_or_create_lambda_role()
print("Selected Role ARN:", role_arn)
