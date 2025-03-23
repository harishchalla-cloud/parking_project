import boto3
from botocore.exceptions import ClientError

# Define AWS region
AWS_REGION = 'us-east-1'

# Initialize CloudWatch Logs client using the default profile
logs_client = boto3.client('logs', region_name=AWS_REGION)

def create_log_group(log_group_name):
    """Create a CloudWatch log group."""
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

def create_log_stream(log_group_name, log_stream_name):
    """Create a log stream within the log group."""
    try:
        response = logs_client.create_log_stream(
            logGroupName=log_group_name,
            logStreamName=log_stream_name
        )
        print(f"Created log stream: {log_stream_name} in {log_group_name}")
        return response
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceAlreadyExistsException':
            print(f"Log stream {log_stream_name} already exists in {log_group_name}.")
        else:
            print(f"Error creating log stream: {e}")
        return None

def main():
    log_group_name = 'ParkingLogs'
    log_stream_name = 'ApplicationStream'

    # Setup log group and stream
    create_log_group(log_group_name)
    create_log_stream(log_group_name, log_stream_name)
    print(f"CloudWatch setup complete: {log_group_name}/{log_stream_name}")

if __name__ == "__main__":
    main()