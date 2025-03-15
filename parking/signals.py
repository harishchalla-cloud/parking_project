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


# New signal for Booking deletion
@receiver(post_delete, sender=Booking)
def notify_user_on_booking_deletion(sender, instance, **kwargs):
    """Send email notification to user when their booking is deleted."""
    try:
        # Initialize ParkingUtils with your bucket names
        utils = ParkingUtils('x23417498-parking-s3', 'x23417498-parking-static')

        # Prepare notification message
        message = (
            f"Your booking for {instance.spot.parking_spot.parking_name} has been cancelled!\n"
            f"Spot: {instance.spot.spot_number}\n"
            f"Start: {instance.start_time}\n"
            f"End: {instance.end_time}\n"
            f"Vehicle: {instance.vehicle_number}\n"
            f"Note: This booking was cancelled by an administrator."
        )

        # Send notification to the user
        utils.notify_user(
            email=instance.user.email,
            subject="Booking Cancelled by Admin",
            message=message
        )
        logger.debug(f"Notification sent to {instance.user.email} for booking {instance.booking_id} deletion")
    except Exception as e:
        logger.error(f"Error sending notification for booking {instance.booking_id} deletion: {str(e)}")