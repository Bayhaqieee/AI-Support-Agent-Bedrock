import json
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
bucket_name = f"cs-agent-kb-{account_id}"
role_arn = f"arn:aws:iam::{account_id}:role/CustomerSupportGatewayRole"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
aoss = session.client("opensearchserverless")
agent_client = session.client("bedrock-agent")

coll_name = "cs-agent-coll"
index_name = "bedrock-knowledge-base-default-index"

colls = aoss.list_collections().get("collectionSummaries", [])
coll_detail = [c for c in colls if c["name"] == coll_name][0]
coll_id = coll_detail["id"]
coll_arn = coll_detail["arn"]

print("Waiting for collection to be ACTIVE...")
while True:
    c_info = aoss.batch_get_collection(ids=[coll_id])["collectionDetails"][0]
    status = c_info.get("status")
    print("Collection status:", status)
    if status == "ACTIVE":
        endpoint = c_info.get("collectionEndpoint")
        break
    time.sleep(5)

print("Collection Endpoint:", endpoint)

existing_kbs = agent_client.list_knowledge_bases().get("knowledgeBaseSummaries", [])
kb_id = None

for kb in existing_kbs:
    if kb["name"] == "CustomerSupportKBVector":
        kb_id = kb["knowledgeBaseId"]
        print("Found existing Vector KB:", kb_id)
        break

if not kb_id:
    print("Creating Vector KB in Bedrock...")
    try:
        res = agent_client.create_knowledge_base(
            name="CustomerSupportKBVector",
            description="Vector Knowledge Base for customer support",
            roleArn=role_arn,
            knowledgeBaseConfiguration={
                "type": "VECTOR",
                "vectorKnowledgeBaseConfiguration": {
                    "embeddingModelArn": f"arn:aws:bedrock:{region}::foundation-model/amazon.titan-embed-text-v2:0"
                }
            },
            storageConfiguration={
                "type": "OPENSEARCH_SERVERLESS",
                "opensearchServerlessConfiguration": {
                    "collectionArn": coll_arn,
                    "vectorIndexName": index_name,
                    "fieldMapping": {
                        "vectorField": "bedrock-knowledge-base-default-vector",
                        "textField": "AMAZON_BEDROCK_TEXT_CHUNK",
                        "metadataField": "AMAZON_BEDROCK_METADATA"
                    }
                }
            }
        )
        kb_id = res["knowledgeBase"]["knowledgeBaseId"]
        print("Created Vector KB:", kb_id)
    except Exception as e:
        print("Create Vector KB error:", e)

print("KB_ID =", kb_id)
