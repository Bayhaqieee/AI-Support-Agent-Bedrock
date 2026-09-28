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
sts = session.client("sts")
user_arn = sts.get_caller_identity()["Arn"]

coll_name = "cs-agent-coll"
index_name = "bedrock-knowledge-base-default-index"

# 1. Encryption Policy
try:
    aoss.create_security_policy(
        name="cs-agent-ep",
        type="encryption",
        policy=json.dumps({
            "Rules": [{"ResourceType": "collection", "Resource": [f"collection/{coll_name}"]}]
        })
    )
    print("Created encryption policy")
except Exception as e:
    print("Encryption policy:", e)

# 2. Network Policy
try:
    aoss.create_security_policy(
        name="cs-agent-np",
        type="network",
        policy=json.dumps([{
            "Rules": [{"ResourceType": "collection", "Resource": [f"collection/{coll_name}"]},
                      {"ResourceType": "dashboard", "Resource": [f"collection/{coll_name}"]}],
            "AllowFromPublic": True
        }])
    )
    print("Created network policy")
except Exception as e:
    print("Network policy:", e)

# 3. Data Access Policy
try:
    aoss.create_access_policy(
        name="cs-agent-ap",
        type="data",
        policy=json.dumps([{
            "Rules": [
                {"ResourceType": "collection", "Resource": [f"collection/{coll_name}"],
                 "Permission": ["aoss:CreateCollectionItems", "aoss:DeleteCollectionItems", "aoss:UpdateCollectionItems", "aoss:DescribeCollectionItems"]},
                {"ResourceType": "index", "Resource": [f"index/{coll_name}/*"],
                 "Permission": ["aoss:CreateIndex", "aoss:DeleteIndex", "aoss:UpdateIndex", "aoss:DescribeIndex", "aoss:ReadDocument", "aoss:WriteDocument"]}
            ],
            "Principal": [user_arn, role_arn]
        }])
    )
    print("Created data access policy")
except Exception as e:
    print("Data access policy:", e)

# 4. Create Collection
colls = aoss.list_collections().get("collectionSummaries", [])
coll_id = None
coll_arn = None

for c in colls:
    if c["name"] == coll_name:
        coll_id = c["id"]
        coll_arn = c["arn"]
        print("Found collection:", coll_id)
        break

if not coll_id:
    res = aoss.create_collection(name=coll_name, type="VECTORSEARCH")
    coll_id = res["createCollectionDetail"]["id"]
    coll_arn = res["createCollectionDetail"]["arn"]
    print("Created collection:", coll_id)

print("Waiting for collection to be ACTIVE...")
while True:
    c_detail = aoss.batch_get_collection(ids=[coll_id])["collectionDetails"][0]
    status = c_detail["status"]
    print("Collection status:", status)
    if status == "ACTIVE":
        endpoint = c_detail["collectionEndpoint"]
        break
    time.sleep(5)

print("Collection endpoint:", endpoint)
print("Collection ARN:", coll_arn)
