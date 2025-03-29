import boto3
from botocore.exceptions import ClientError

AWS_REGION = 'us-east-1'
BUCKET_NAME = 'x23417498-parking-s3'

# Initialize S3 client using the default profile
s3_client = boto3.client('s3', region_name=AWS_REGION)

def create_s3_bucket():
    try:
        print(f"Creating S3 bucket: {BUCKET_NAME}")
        # S3 buckets in us-east-1 don't require LocationConstraint
        response = s3_client.create_bucket(Bucket=BUCKET_NAME)
        print(f"S3 bucket created: {response['Location']}")

        # Update public access settings
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

        # Apply bucket policy for public read access
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