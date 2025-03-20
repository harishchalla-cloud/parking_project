import boto3
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_sns_topic():
    try:
        # Initialize the SNS client
        sns_client = boto3.client('sns')

        # Create the new SNS topic
        response = sns_client.create_topic(Name='ParkingAppLambdaAdminNotifications')
        topic_arn = response['TopicArn']
        logger.info(f"SNS topic created successfully: {topic_arn}")
        return topic_arn

    except Exception as e:
        logger.error(f"Failed to create SNS topic: {str(e)}")
        raise

if __name__ == "__main__":
    create_sns_topic()