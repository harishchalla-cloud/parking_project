from PIL import Image
import boto3
import os
from decouple import config
import logging
from .models import Booking

logger = logging.getLogger(__name__)

class ParkingUtils:
    def __init__(self, media_bucket_name, static_bucket_name):
        self.s3_client = boto3.client('s3')
        self.sns_client = boto3.client('sns')
        self.media_bucket = media_bucket_name
        self.static_bucket = static_bucket_name

    def resize_image(self, image_path, output_path, size=(200, 200)):
        """Resize image and upload to S3 media bucket."""
        try:
            with Image.open(image_path) as img:
                img.thumbnail(size)
                img.save(output_path)
            s3_key = f"parking_spots/{os.path.basename(output_path)}"
            self.s3_client.upload_file(output_path, self.media_bucket, s3_key)
            url = f"https://{self.media_bucket}.s3.amazonaws.com/{s3_key}"
            logger.debug(f"Resized and uploaded image to S3: {url}")
            return url
        except Exception as e:
            logger.error(f"Error resizing image {image_path}: {str(e)}")
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

    def notify_user(self, email, subject, message):
        """Send SNS notification to user."""
        try:
            self.sns_client.publish(
                TopicArn=config('SNS_TOPIC_ARN'),
                Message=message,
                Subject=subject,
                MessageAttributes={'email': {'DataType': 'String', 'StringValue': email}}
            )
            logger.debug(f"SNS notification sent to {email}: {subject}")
        except Exception as e:
            logger.error(f"Failed to send SNS notification to {email}: {str(e)}")