import os
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"
account_id = "016586718516"
role_arn = f"arn:aws:iam::{account_id}:role/CustomerSupportGatewayRole"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
agent_client = session.client("bedrock-agent")

print("Testing create_knowledge_base with type=MANAGED...")
try:
    res = agent_client.create_knowledge_base(
        name="CustomerSupportKB",
        description="Knowledge base for product catalog and support policy",
        roleArn=role_arn,
        knowledgeBaseConfiguration={
            "type": "MANAGED"
        }
    )
    print("Created KB:", res)
except Exception as e:
    print("Error with type=MANAGED:", e)

    print("Testing create_knowledge_base with type=VECTOR and titan model...")
    try:
        res = agent_client.create_knowledge_base(
            name="CustomerSupportKB",
            description="Knowledge base for product catalog and support policy",
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
                }
            }
        )
        print("Created KB:", res)
    except Exception as e2:
        print("Error with type=VECTOR:", e2)
