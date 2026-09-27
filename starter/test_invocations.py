import json
import os
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"
agent_arn = "arn:aws:bedrock-agentcore:us-east-1:016586718516:runtime/customer_support_agent-MoXBtpDpHj"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
client = session.client("bedrock-agentcore")

def invoke_agent(prompt: str, customer_id: str = "cust-alex-100", session_id: str = None):
    payload = {
        "prompt": prompt,
        "customer_id": customer_id
    }
    if session_id:
        payload["session_id"] = session_id

    kwargs = {
        "agentRuntimeArn": agent_arn,
        "payload": json.dumps(payload).encode("utf-8")
    }
    if session_id:
        kwargs["runtimeSessionId"] = session_id
    if customer_id:
        kwargs["runtimeUserId"] = customer_id

    resp = client.invoke_agent_runtime(**kwargs)
    body = resp["response"].read().decode("utf-8")
    return body

if __name__ == "__main__":
    import sys
    prompt_text = sys.argv[1] if len(sys.argv) > 1 else "Hello"
    cust_id = sys.argv[2] if len(sys.argv) > 2 else "cust-alex-100"
    sess_id = sys.argv[3] if len(sys.argv) > 3 else None
    print(f"--- Invoking agent: prompt='{prompt_text}' customer_id='{cust_id}' session_id='{sess_id}' ---")
    out = invoke_agent(prompt_text, cust_id, sess_id)
    print("Response:\n", out)
