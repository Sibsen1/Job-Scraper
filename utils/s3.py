import boto3
import os

session = boto3.session.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION")
)

s3 = session.client("s3")

def uploadBytes(data: bytes, key: str, content_type="application/octet-stream"):
    bucket = os.getenv("S3_BUCKET")
    resp = s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)

    if resp["ResponseMetadata"]["HTTPStatusCode"] != 200:
        raise RuntimeError("S3 upload failed: ", resp)

    
def uploadFile(filepath: str, key: str):
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    bucket = os.getenv("S3_BUCKET")

    try:
        s3.upload_file(filepath, bucket, key)
    except Exception as e:
        raise RuntimeError(f"Upload failed: {e}")