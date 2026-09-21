import os
import time
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"
account_id = "016586718516"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
s3 = session.client("s3")
agent_client = session.client("bedrock-agent")

bucket_name = f"cs-agent-kb-{account_id}"

try:
    s3.head_bucket(Bucket=bucket_name)
    print("S3 bucket exists:", bucket_name)
except Exception:
    print("Creating S3 bucket:", bucket_name)
    s3.create_bucket(Bucket=bucket_name)

s3.upload_file("product_catalog.txt", bucket_name, "product_catalog.txt")
print("Uploaded product_catalog.txt to S3 bucket.")

# Check for existing Knowledge Base named CustomerSupportKB
existing_kbs = agent_client.list_knowledge_bases().get("knowledgeBaseSummaries", [])
kb_id = None
for kb in existing_kbs:
    if kb["name"] == "CustomerSupportKB":
        kb_id = kb["knowledgeBaseId"]
        print("Found existing KB:", kb_id)
        break

print("S3 Bucket:", bucket_name)
print("Existing KB ID:", kb_id)
