import json
import os
import time
import boto3
import dotenv
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

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
s3 = session.client("s3")

# 1. Get OpenSearch Collection
colls = aoss.list_collections().get("collectionSummaries", [])
coll = [c for c in colls if c["name"] == "cs-agent-coll"][0]
coll_id = coll["id"]
coll_arn = coll["arn"]

c_detail = aoss.batch_get_collection(ids=[coll_id])["collectionDetails"][0]
host = c_detail["collectionEndpoint"].replace("https://", "")

print("OpenSearch Host:", host)

# 2. Create Index in OpenSearch Serverless
awsauth = AWS4Auth(access_key, secret_key, region, "aoss", session_token=session_token)
oss_client = OpenSearch(
    hosts=[{"host": host, "port": 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    connection_class=RequestsHttpConnection
)

index_name = "bedrock-knowledge-base-default-index"
index_body = {
    "settings": {
        "index.knn": True
    },
    "mappings": {
        "properties": {
            "bedrock-knowledge-base-default-vector": {
                "type": "knn_vector",
                "dimension": 1024,
                "method": {
                    "name": "hnsw",
                    "engine": "faiss",
                    "space_type": "l2"
                }
            },
            "AMAZON_BEDROCK_TEXT_CHUNK": {
                "type": "text"
            },
            "AMAZON_BEDROCK_METADATA": {
                "type": "text"
            }
        }
    }
}

if not oss_client.indices.exists(index=index_name):
    print(f"Creating OpenSearch Index '{index_name}'...")
    try:
        res = oss_client.indices.create(index=index_name, body=index_body)
        print("Created index response:", res)
        # Wait for index propagation in AOSS
        time.sleep(10)
    except Exception as e:
        print("Error creating index:", e)
else:
    print(f"Index '{index_name}' already exists.")

# 3. Create Vector Knowledge Base in Bedrock
existing_kbs = agent_client.list_knowledge_bases().get("knowledgeBaseSummaries", [])
kb_id = None
for kb in existing_kbs:
    if kb["name"] == "CustomerSupportKBVector":
        kb_id = kb["knowledgeBaseId"]
        print("Found existing CustomerSupportKBVector:", kb_id)
        break

if not kb_id:
    print("Creating Bedrock Knowledge Base CustomerSupportKBVector...")
    res = agent_client.create_knowledge_base(
        name="CustomerSupportKBVector",
        description="Vector Knowledge Base for customer support catalog",
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
    print("Created KB ID:", kb_id)

    # Wait for KB to be ACTIVE
    while True:
        kb_info = agent_client.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]
        st = kb_info["status"]
        print("KB status:", st)
        if st == "ACTIVE":
            break
        time.sleep(5)

# 4. Create S3 Data Source
ds_list = agent_client.list_data_sources(knowledgeBaseId=kb_id).get("dataSourceSummaries", [])
ds_id = None
for ds in ds_list:
    if ds["name"] == "ProductCatalogS3":
        ds_id = ds["dataSourceId"]
        break

if not ds_id:
    print("Creating S3 Data Source ProductCatalogS3...")
    ds_res = agent_client.create_data_source(
        knowledgeBaseId=kb_id,
        name="ProductCatalogS3",
        description="Product Catalog S3 Data Source",
        dataSourceConfiguration={
            "type": "S3",
            "s3Configuration": {
                "bucketArn": f"arn:aws:s3:::{bucket_name}",
                "inclusionPrefixes": ["product_catalog.txt"]
            }
        }
    )
    ds_id = ds_res["dataSource"]["dataSourceId"]
    print("Created Data Source ID:", ds_id)

# 5. Start Ingestion Job (Sync)
print("Starting Ingestion Job...")
job_res = agent_client.start_ingestion_job(
    knowledgeBaseId=kb_id,
    dataSourceId=ds_id,
    description="Sync product catalog"
)
job_id = job_res["ingestionJob"]["ingestionJobId"]
print("Ingestion Job ID:", job_id)

while True:
    job = agent_client.get_ingestion_job(
        knowledgeBaseId=kb_id,
        dataSourceId=ds_id,
        ingestionJobId=job_id
    )["ingestionJob"]
    j_status = job["status"]
    print("Ingestion job status:", j_status)
    if j_status in ["COMPLETE", "FAILED"]:
        if j_status == "FAILED":
            print("Failure reasons:", job.get("failureReasons"))
        break
    time.sleep(5)

print(f"RAG Setup Complete! KB_ID = {kb_id}")
