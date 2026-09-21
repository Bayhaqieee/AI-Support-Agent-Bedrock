import io
import os
import time
import zipfile
import boto3
import dotenv

dotenv.load_dotenv("../.env")

access_key = os.getenv("ACCESS_KEY")
secret_key = os.getenv("SECRET_ACCESS_KEY")
session_token = os.getenv("SESSION_TOKEY") or os.getenv("SESSION_TOKEN")
region = "us-east-1"
role_arn = "arn:aws:iam::016586718516:role/CustomerSupportLambdaRole"

session = boto3.Session(
    aws_access_key_id=access_key,
    aws_secret_access_key=secret_key,
    aws_session_token=session_token,
    region_name=region
)
lambda_client = session.client("lambda")

def zip_file(filename, path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(path, arcname=filename)
    return buf.getvalue()

def deploy_function(name, handler_filename, file_path):
    zip_bytes = zip_file(handler_filename, file_path)
    handler_name = f"{os.path.splitext(handler_filename)[0]}.lambda_handler"
    try:
        res = lambda_client.get_function(FunctionName=name)
        print(f"Updating function {name}...")
        lambda_client.update_function_code(
            FunctionName=name,
            ZipFile=zip_bytes
        )
        arn = res["Configuration"]["FunctionArn"]
    except lambda_client.exceptions.ResourceNotFoundException:
        print(f"Creating function {name}...")
        for attempt in range(6):
            try:
                res = lambda_client.create_function(
                    FunctionName=name,
                    Runtime="python3.12",
                    Role=role_arn,
                    Handler=handler_name,
                    Code={"ZipFile": zip_bytes},
                    Timeout=30,
                    MemorySize=128
                )
                arn = res["FunctionArn"]
                break
            except lambda_client.exceptions.InvalidParameterValueException as e:
                print(f"Waiting for IAM role propagation... attempt {attempt+1}")
                time.sleep(5)
                if attempt == 5:
                    raise e
    print(f"Deployed {name}: {arn}")
    return arn

order_arn = deploy_function("order-tracker", "order_tracker.py", "lambda/order_tracker.py")
refund_arn = deploy_function("refund-processor", "refund_processor.py", "lambda/refund_processor.py")
