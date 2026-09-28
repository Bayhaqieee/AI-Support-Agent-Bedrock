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
aoss = session.client("opensearchserverless")
kms = session.client("kms")

print("Checking KMS keys...")
aliases = kms.list_aliases()["Aliases"]
aoss_key_arn = None
for a in aliases:
    if "opensearch" in a.get("AliasName", "").lower():
        aoss_key_arn = a.get("TargetKeyId")
        print("Found KMS alias:", a["AliasName"], aoss_key_arn)

if not aoss_key_arn:
    # Create KMS key if allowed
    try:
        res = kms.create_key(Description="Key for OpenSearch Serverless")
        aoss_key_arn = res["KeyMetadata"]["Arn"]
        print("Created KMS key:", aoss_key_arn)
    except Exception as e:
        print("KMS create key error:", e)

if aoss_key_arn:
    key_arn = f"arn:aws:kms:us-east-1:016586718516:key/{aoss_key_arn}" if not aoss_key_arn.startswith("arn:") else aoss_key_arn
    try:
        aoss.create_security_policy(
            name="cs-agent-ep",
            type="encryption",
            policy=json.dumps({
                "Rules": [{"ResourceType": "collection", "Resource": ["collection/cs-agent-coll"]}],
                "KmsARN": key_arn
            })
        )
        print("Created encryption policy with key ARN:", key_arn)
    except Exception as e:
        print("Error creating policy:", e)
