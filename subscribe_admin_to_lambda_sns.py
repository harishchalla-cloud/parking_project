import boto3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def subscribe_to_sns():
    try:
        # Initialize the SNS client
        sns_client = boto3.client('sns')

        # New SNS topic ARN
        topic_arn = "arn:aws:sns:us-east-1:296779434624:ParkingAppLambdaAdminNotifications"
        email = "x23417498@student.ncirl.ie"

        # Subscribe the email to the SNS topic
        response = sns_client.subscribe(
            TopicArn=topic_arn,
            Protocol='email',
            Endpoint=email
        )

        logger.info(f"Subscription request sent successfully: {response['SubscriptionArn']}")
        logger.info(f"Please check {email} to confirm the subscription.")

    except Exception as e:
        logger.error(f"Failed to subscribe to SNS topic: {str(e)}")
        raise

if __name__ == "__main__":
    subscribe_to_sns()