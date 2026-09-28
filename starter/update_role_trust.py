import json
import os
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"
role_name = "CustomerSupportLambdaRole"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
iam = session.client("iam")

trust_policy = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Principal": {
                "Service": [
                    "lambda.amazonaws.com",
                    "bedrock-agentcore.amazonaws.com",
                    "bedrock.amazonaws.com",
                    "apigateway.amazonaws.com"
                ]
            },
            "Action": "sts:AssumeRole"
        }
    ]
}

iam.update_assume_role_policy(
    RoleName=role_name,
    PolicyDocument=json.dumps(trust_policy)
)
print("Updated trust policy for role:", role_name)

# Attach administrator access or specific policy to gateway role so it can invoke lambda & apigateway
iam.attach_role_policy(
    RoleName=role_name,
    PolicyArn="arn:aws:iam::aws:policy/AWSLambda_FullAccess"
)
iam.attach_role_policy(
    RoleName=role_name,
    PolicyArn="arn:aws:iam::aws:policy/AmazonAPIGatewayInvokeFullAccess"
)
print("Attached execution policies to role.")
