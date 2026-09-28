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
agent_client = session.client("bedrock-agent")
model = agent_client.meta.service_model

doc = model.operation_model("CreateKnowledgeBase")
print("CreateKnowledgeBase parameters:", list(doc.input_shape.members.keys()))
kb_config = model.shape_for("KnowledgeBaseConfiguration")
print("KnowledgeBaseConfiguration type:", kb_config.members.keys() if kb_config else '')
storage_config = model.shape_for("StorageConfiguration")
print("StorageConfiguration type:", storage_config.members.keys() if storage_config else '')
