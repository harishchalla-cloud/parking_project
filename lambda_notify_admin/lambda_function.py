import json
import boto3
import logging
import os
from django.conf import settings


# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize SNS client
region = os.getenv('AWS_REGION', 'us-east-1')
sns_client = boto3.client('sns', region_name=settings.AWS_REGION)

# New SNS topic ARN for admin notifications
SNS_TOPIC_ARN = "arn:aws:sns:us-east-1:296779434624:ParkingAppLambdaAdminNotifications"

def lambda_handler(event, context):
    """
    Lambda function to process log events and notify the admin via SNS.
    Event format simulates a CloudWatch Logs event.
    """
    try:
        logger.info(f"Received event: {json.dumps(event, default=str)}")
        # Simulate the structure of a CloudWatch Logs event
        log_data = event.get('awslogs', {}).get('data', {})
        if not log_data:
            raise ValueError("No log data found in event")

        log_event = log_data
        log_group = log_event.get('logGroup', 'UnknownLogGroup')
        log_stream = log_event.get('logStream', 'UnknownLogStream')
        log_messages = [message['message'] for message in log_event.get('logEvents', [])]
        logger.info(f"Extracted log messages: {log_messages}")

        # Check for ERROR or WARNING in log messages
        for message in log_messages:
            if 'ERROR' in message or 'WARNING' in message:
                logger.info(f"Processing {message} for notification")
                # Prepare the notification
                subject = f"Parking App Issue Detected in {log_group}"
                body = f"""
An issue was detected in the Parking App:

Log Group: {log_group}
Log Stream: {log_stream}
Message: {message}

Please investigate the issue in CloudWatch Logs.
                """
                # Send notification to admin via SNS
                response = sns_client.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject=subject,
                    Message=body
                )
                logger.info(f"Notification sent to SNS topic {SNS_TOPIC_ARN}: {response['MessageId']}")
            else:
                logger.info(f"Log message does not contain ERROR or WARNING: {message}")

        return {
            'statusCode': 200,
            'body': json.dumps('Processed log events successfully')
        }

    except Exception as e:
        logger.error(f"Error processing log event: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f"Error: {str(e)}")
        }