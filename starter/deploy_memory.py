import os
import time
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
control = session.client("bedrock-agentcore-control")

memory_name = "CustomerSupportMemory"

existing_memories = control.list_memories().get("memories", [])
memory_id = None

for m in existing_memories:
    m_id = m.get("id") or m.get("memoryId")
    if memory_name in m.get("arn", "") or m_id.startswith(memory_name):
        memory_id = m_id
        print("Found existing Memory:", memory_id)
        break

if not memory_id:
    print("Creating AgentCore Memory resource:", memory_name)
    res = control.create_memory(
        name=memory_name,
        description="Customer Support Agent Memory Resource",
        eventExpiryDuration=30,
        memoryStrategies=[
            {
                "semanticMemoryStrategy": {
                    "name": "customer_facts",
                    "namespaceTemplates": ["cs_agent/{actorId}/facts"]
                }
            },
            {
                "userPreferenceMemoryStrategy": {
                    "name": "customer_preferences",
                    "namespaceTemplates": ["cs_agent/{actorId}/preferences"]
                }
            }
        ]
    )
    memory = res.get("memory", {})
    memory_id = memory.get("id") or memory.get("memoryId") or res.get("id") or res.get("memoryId")

print("Waiting for Memory resource to be ACTIVE...")
while True:
    m_info = control.get_memory(memoryId=memory_id)
    mem_obj = m_info.get("memory", {})
    status = mem_obj.get("status") or m_info.get("status")
    print("Memory status:", status)
    if status in ["ACTIVE", "READY"]:
        break
    time.sleep(5)

print("MEMORY_ID =", memory_id)
