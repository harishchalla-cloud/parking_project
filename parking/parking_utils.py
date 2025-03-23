from PIL import Image
import boto3
import os
from decouple import config
import logging
from django.utils import timezone
from django.conf import settings
from .models import Booking

logger = logging.getLogger(__name__)

class ParkingUtils:
    def __init__(self, media_bucket_name, static_bucket_name):
        self.region = os.getenv('AWS_REGION', 'us-east-1')
        self.s3_client = boto3.client('s3', region_name=self.region)
        self.sns_client = boto3.client('sns', region_name=self.region)
        self.cloudwatch_logs = boto3.client('logs', region_name=self.region)
        self.cloudwatch_metrics = boto3.client('cloudwatch', region_name=self.region)
        self.media_bucket = media_bucket_name
        self.static_bucket = static_bucket_name
        self.topic_arn = config('SNS_TOPIC_ARN')
        self.log_group_name = 'ParkingLogs'
        self.log_stream_name = 'ApplicationStream'
        self.sequence_token = None

    def resize_image(self, image_path, output_path, size=None):
        try:
            s3_key = f"parking_spots/{os.path.basename(image_path)}"
            if size:
                with Image.open(image_path) as img:
                    img.thumbnail(size)
                    img.save(output_path, quality=95)
                self.s3_client.upload_file(
                    output_path, self.media_bucket, s3_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
            else:
                self.s3_client.upload_file(
                    image_path, self.media_bucket, s3_key,
                    ExtraArgs={'ContentType': 'image/jpeg'}
                )
            url = f"https://{self.media_bucket}.s3.amazonaws.com/{s3_key}"
            self.log_to_cloudwatch(f"Uploaded image to S3: {url}")
            return url
        except Exception as e:
            self.log_to_cloudwatch(f"Error uploading image {image_path}: {str(e)}", level='ERROR')
            raise

    def check_spot_availability(self, parking_spot, start_time, end_time):
        """Check if any spot is available for the given time range."""
        overlapping = Booking.objects.filter(
            spot__parking_spot=parking_spot,
            start_time__lt=end_time,
            end_time__gt=start_time
        ).count()
        available = overlapping < parking_spot.total_spots
        logger.debug(f"Availability check for {parking_spot.parking_name}: {available}, Overlapping: {overlapping}")
        return available

    def subscribe_user(self, email):
        """Subscribe an email to the SNS topic with a filter policy if not already subscribed."""
        try:
            subscriptions = self.sns_client.list_subscriptions_by_topic(TopicArn=self.topic_arn)
            subscribed_emails = [sub['Endpoint'] for sub in subscriptions['Subscriptions'] if sub['Protocol'] == 'email']

            if email not in subscribed_emails:
                response = self.sns_client.subscribe(
                    TopicArn=self.topic_arn,
                    Protocol='email',
                    Endpoint=email
                )
                subscription_arn = response['SubscriptionArn']
                logger.debug(f"Subscription request sent to {email}: {subscription_arn}")
                logger.info(f"User {email} must confirm SNS subscription to receive notifications.")
                return subscription_arn
            else:
                for sub in subscriptions['Subscriptions']:
                    if sub['Endpoint'] == email and sub['SubscriptionArn'] != 'PendingConfirmation':
                        # Ensure filter policy is applied
                        self.set_subscription_filter(sub['SubscriptionArn'], email)
                        return sub['SubscriptionArn']
            return None
        except Exception as e:
            logger.error(f"Error subscribing {email}: {str(e)}")
            raise

    def set_subscription_filter(self, subscription_arn, email):
        """Set a filter policy on the subscription to match the email."""
        try:
            self.sns_client.set_subscription_attributes(
                SubscriptionArn=subscription_arn,
                AttributeName='FilterPolicy',
                AttributeValue=f'{{"email": ["{email}"]}}'
            )
            logger.debug(f"Filter policy set for {email} on {subscription_arn}")
        except Exception as e:
            logger.error(f"Error setting filter policy for {email}: {str(e)}")
            raise

    def notify_user(self, email, subject, message):
        """Send SNS notification to the specified email only."""
        logger.info(f"Attempting to notify {email} with subject: {subject}")
        try:
            # Ensure the user is subscribed with a filter
            subscription_arn = self.subscribe_user(email)

            # If subscription is pending, log a warning and return status
            if subscription_arn == 'PendingConfirmation':
                logger.warning(f"Notification to {email} may not be sent: subscription pending confirmation.")
                self.log_to_cloudwatch(f"Notification to {email} skipped: subscription pending confirmation.", level='WARNING')
                return "pending_confirmation"
            elif not subscription_arn:
                logger.warning(f"No confirmed subscription found for {email}.")
                self.log_to_cloudwatch(f"No confirmed subscription found for {email}.", level='WARNING')
                return "no_subscription"

            # If subscription is confirmed, set the filter policy
            self.set_subscription_filter(subscription_arn, email)

            # Publish the message
            response = self.sns_client.publish(
                TopicArn=self.topic_arn,
                Message=message,
                Subject=subject,
                MessageAttributes={
                    'email': {
                        'DataType': 'String',
                        'StringValue': email
                    }
                }
            )
            logger.debug(f"SNS notification sent to {email}: {response['MessageId']} with subject: {subject}")
            self.log_to_cloudwatch(f"SNS notification sent to {email}: {response['MessageId']} with subject: {subject}")
            return "success"
        except Exception as e:
            logger.error(f"Failed to send SNS notification to {email}: {str(e)}")
            self.log_to_cloudwatch(f"Failed to send SNS notification to {email}: {str(e)}", level='ERROR')
            return "error"

    def log_to_cloudwatch(self, message, level='INFO'):
        try:
            log_event = {
                'logGroupName': self.log_group_name,
                'logStreamName': self.log_stream_name,
                'logEvents': [
                    {
                        'timestamp': int(timezone.now().timestamp() * 1000),
                        'message': f"{level}: {message}"
                    }
                ]
            }
            if self.sequence_token:
                log_event['sequenceToken'] = self.sequence_token
            response = self.cloudwatch_logs.put_log_events(**log_event)
            self.sequence_token = response['nextSequenceToken']
            logger.debug(f"Logged to CloudWatch: {message}")
        except Exception as e:
            logger.error(f"Failed to log to CloudWatch: {str(e)}")

    def put_metric(self, metric_name, value, unit='Count'):
        try:
            self.cloudwatch_metrics.put_metric_data(
                Namespace='ParkingAppMetrics',
                MetricData=[{
                    'MetricName': metric_name,
                    'Value': value,
                    'Unit': unit
                }]
            )
            logger.debug(f"Sent metric {metric_name}: {value} to CloudWatch")
        except Exception as e:
            logger.error(f"Failed to send metric {metric_name}: {str(e)}")