from django.db.models.signals import post_delete
from django.dispatch import receiver
from .models import ParkingSpot, Booking
import boto3
from botocore.config import Config
from .parking_utils import ParkingUtils
import logging

logger = logging.getLogger('django')


# Existing signal for ParkingSpot image deletion
@receiver(post_delete, sender=ParkingSpot)
def delete_s3_image(sender, instance, **kwargs):
    if instance.image:
        try:
            logger.debug(f"Deleting S3 image: {instance.image}")
            s3_client = boto3.client('s3', config=Config(connect_timeout=5, read_timeout=5))
            s3_client.delete_object(Bucket='x23417498-parking-s3', Key=str(instance.image))
            logger.debug(f"Deleted S3 image: {instance.image}")
        except Exception as e:
            logger.error(f"Error deleting S3 image {instance.image}: {str(e)}")
