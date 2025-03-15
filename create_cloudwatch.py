import boto3
from botocore.exceptions import ClientError
from decouple import config

# AWS credentials from .env
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_SESSION_TOKEN = config('AWS_SESSION_TOKEN', default='')
AWS_REGION = config('AWS_REGION', default='us-east-1')

# Initialize CloudWatch Logs client
logs_client = boto3.client(
    'logs',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN
)

def create_log_group(log_group_name):           #Creating a CloudWatch log group.
    try:
        response = logs_client.create_log_group(logGroupName=log_group_name)
        print(f"Created log group: {log_group_name}")
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
            print(f"Log group {log_group_name} already exists.")
        else:
            print(f"Error creating log group: {e}")
        return None

def main():
    log_group_name = 'ParkingLogs'  # Updated log group name
    create_log_group(log_group_name)

if __name__ == "__main__":
    main()