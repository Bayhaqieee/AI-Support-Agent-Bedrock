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
kb_id = "75EMY72ZDW"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
agent_client = session.client("bedrock-agent")

print("Waiting for KB to be ACTIVE...")
while True:
    kb_info = agent_client.get_knowledge_base(knowledgeBaseId=kb_id)["knowledgeBase"]
    status = kb_info["status"]
    print("KB status:", status)
    if status == "ACTIVE":
        break
    time.sleep(5)

ds_list = agent_client.list_data_sources(knowledgeBaseId=kb_id).get("dataSourceSummaries", [])
ds_id = None
for ds in ds_list:
    if ds["name"] == "ProductCatalogS3":
        ds_id = ds["dataSourceId"]
        break

if not ds_id:
    print("Creating Data Source ProductCatalogS3...")
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

print("Starting Ingestion Job (Sync)...")
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
        break
    time.sleep(5)

print("Knowledge Base Sync Complete. KB_ID =", kb_id)
