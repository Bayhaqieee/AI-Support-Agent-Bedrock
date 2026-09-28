import os
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"
kb_id = "75EMY72ZDW"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
agent_client = session.client("bedrock-agent")

with open("product_catalog.txt", "r", encoding="utf-8") as f:
    text_content = f.read()

ds_list = agent_client.list_data_sources(knowledgeBaseId=kb_id).get("dataSourceSummaries", [])
ds_id = None
for ds in ds_list:
    if ds["name"] == "CustomDataSource":
        ds_id = ds["dataSourceId"]
        break

if not ds_id:
    ds_res = agent_client.create_data_source(
        knowledgeBaseId=kb_id,
        name="CustomDataSource",
        description="Custom In-line Data Source",
        dataSourceConfiguration={
            "type": "CUSTOM"
        }
    )
    ds_id = ds_res["dataSource"]["dataSourceId"]

print("Data Source ID:", ds_id)

res = agent_client.ingest_knowledge_base_documents(
    knowledgeBaseId=kb_id,
    dataSourceId=ds_id,
    documents=[
        {
            "content": {
                "custom": {
                    "customDocumentIdentifier": {"id": "productcatalog001"},
                    "sourceType": "IN_LINE",
                    "inlineContent": {
                        "type": "TEXT",
                        "textContent": {
                            "data": text_content
                        }
                    }
                },
                "dataSourceType": "CUSTOM"
            }
        }
    ]
)
print("Ingest documents response:", res)
