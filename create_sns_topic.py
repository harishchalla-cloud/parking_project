import boto3
from botocore.exceptions import ClientError
from decouple import config

# Define AWS credentials and region from .env
AWS_ACCESS_KEY_ID = config('AWS_ACCESS_KEY_ID')
AWS_SECRET_ACCESS_KEY = config('AWS_SECRET_ACCESS_KEY')
AWS_SESSION_TOKEN = config('AWS_SESSION_TOKEN', default='')  # Optional if using permanent creds
AWS_REGION = config('AWS_REGION', default='us-east-1')

# Initialize SNS client
sns_client = boto3.client(
    'sns',
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    aws_session_token=AWS_SESSION_TOKEN
)

def create_sns_topic(topic_name):
    """Create an SNS topic and return its ARN."""
    try:
        response = sns_client.create_topic(Name=topic_name)
        topic_arn = response['TopicArn']
        print(f"Created SNS topic: {topic_arn}")
        return topic_arn
    except ClientError as e:
        print(f"Error creating topic: {e}")
        return None

def subscribe_email(topic_arn, email):
    """Subscribe an email to the SNS topic."""
    try:
        response = sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email
        )
        subscription_arn = response['SubscriptionArn']
        print(f"Subscribed {email} to {topic_arn}. Subscription ARN: {subscription_arn}")
        print(f"Please check {email} to confirm the subscription.")
    except ClientError as e:
        print(f"Error subscribing email: {e}")

def main():
    topic_name = 'ParkingNotifications'
    test_email = 'challaharish15@gmail.com'  # Replace with your email

    # Create topic
    topic_arn = create_sns_topic(topic_name)
    if topic_arn:
        # Subscribe test email
        subscribe_email(topic_arn, test_email)
        print(f"Topic ARN to use in settings.py: {topic_arn}")

if __name__ == "__main__":
    main()