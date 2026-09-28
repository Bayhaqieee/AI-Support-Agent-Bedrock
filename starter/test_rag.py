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
_bedrock_runtime = session.client("bedrock-agent-runtime")

print("Testing RAG retrieval on KB:", kb_id)
try:
    resp = _bedrock_runtime.retrieve(
        knowledgeBaseId=kb_id,
        retrievalQuery={"text": "What is the return policy for electronics?"}
    )
    print("Retrieval response:", resp)
except Exception as e:
    print("Retrieval error:", e)
