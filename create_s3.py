import boto3
import os
from botocore.exceptions import ClientError

AWS_REGION = os.getenv('AWS_REGION', 'us-east-1')
BUCKET_NAME = os.getenv('BUCKET_NAME')
if not BUCKET_NAME:
    raise ValueError("Environment variable BUCKET_NAME must be set")

aws_access_key_id = os.getenv('AWS_ACCESS_KEY_ID')
aws_secret_access_key = os.getenv('AWS_SECRET_ACCESS_KEY')
aws_session_token = os.getenv('AWS_SESSION_TOKEN')

client_kwargs = {
    "region_name": AWS_REGION
}
if aws_access_key_id and aws_secret_access_key:
    client_kwargs["aws_access_key_id"] = aws_access_key_id
    client_kwargs["aws_secret_access_key"] = aws_secret_access_key
    if aws_session_token:
        client_kwargs["aws_session_token"] = aws_session_token

s3_client = boto3.client('s3', **client_kwargs)

def create_s3_bucket():
    try:
        print(f"Creating S3 bucket: {BUCKET_NAME}")
        response = s3_client.create_bucket(Bucket=BUCKET_NAME)
        print(f"S3 bucket created: {response['Location']}")

        s3_client.put_public_access_block(
            Bucket=BUCKET_NAME,
            PublicAccessBlockConfiguration={
                'BlockPublicAcls': False,
                'IgnorePublicAcls': False,
                'BlockPublicPolicy': False,
                'RestrictPublicBuckets': False
            }
        )
        print("Block Public Access settings updated.")

        s3_client.put_bucket_policy(
            Bucket=BUCKET_NAME,
            Policy=f'''{{
                "Version": "2012-10-17",
                "Statement": [
                    {{
                        "Sid": "PublicRead",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": "arn:aws:s3:::{BUCKET_NAME}/*"
                    }}
                ]
            }}'''
        )
        print("Bucket policy applied for public read access.")

        bucket_info = s3_client.head_bucket(Bucket=BUCKET_NAME)
        print(f"Bucket verified: {bucket_info['ResponseMetadata']}")

    except ClientError as e:
        print(f"Error creating S3 bucket: {e}")

if __name__ == "__main__":
    create_s3_bucket()
