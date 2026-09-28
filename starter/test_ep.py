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

try:
    aoss.delete_security_policy(name="cs-agent-ep", type="encryption")
except Exception:
    pass

try:
    aoss.create_security_policy(
        name="cs-agent-ep",
        type="encryption",
        policy=json.dumps({
            "Rules": [{"ResourceType": "collection", "Resource": ["collection/cs-agent-coll"]}],
            "KmsARN": "auto"
        })
    )
    print("Created encryption policy with KmsARN auto")
except Exception as e:
    print("Error KmsARN:", e)

    try:
        aoss.create_security_policy(
            name="cs-agent-ep",
            type="encryption",
            policy=json.dumps({
                "Rules": [{"ResourceType": "collection", "Resource": ["collection/cs-agent-coll"]}],
                "AWSKMSSingleMasterKeyArn": "auto"
            })
        )
        print("Created encryption policy with AWSKMSSingleMasterKeyArn auto")
    except Exception as e2:
        print("Error AWSKMSSingleMasterKeyArn:", e2)
