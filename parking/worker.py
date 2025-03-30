import json
import boto3
import qrcode
from PIL import Image
import os
import logging
import django
import sys
import tempfile

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_project.settings')
django.setup()

from parking.models import Booking
from parking_utils_aec import ParkingUtils

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('D:/parking_project/worker.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

# Initialize ParkingUtils with SNS topic ARN from environment
utils = ParkingUtils(
    media_bucket_name='x23417498-parking-s3',
    static_bucket_name='x23417498-parking-s3',
    sns_topic_arn='arn:aws:sns:us-east-1:296779434624:ParkingNotifications'
)

def generate_qr_code(booking_id, verification_url):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4
    )
    qr.add_data(verification_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    with tempfile.NamedTemporaryFile(suffix=f"_{booking_id}_qr.png", delete=False) as temp_file:
        temp_path = temp_file.name
        img.save(temp_path)
    logger.debug(f"Generated QR code at {temp_path}")
    return temp_path

def process_message(message):
    body = json.loads(message['Body'])
    task_type = body.get('task_type')
    booking_id = body.get('booking_id')
    user_email = body.get('user_email')
    booking_details = body.get('booking_details')

    if task_type != 'generate_qr':
        logger.warning(f"Unknown task type: {task_type}")
        return True

    logger.info(f"Processing QR code generation for booking {booking_id}")

    try:
        booking = Booking.objects.get(booking_id=booking_id)
        if booking.qr_code_url:
            logger.info(f"Booking {booking_id} already has a QR code: {booking.qr_code_url}")
            return True
    except Booking.DoesNotExist:
        logger.error(f"Booking {booking_id} not found in database")
        utils.log_to_cloudwatch(f"Booking {booking_id} not found in database", level='ERROR')
        return True

    verification_url = f"http://parkingapp-env.eba-pjwcyf2j.us-east-1.elasticbeanstalk.com//parking/verify/{booking_id}/"
    qr_path = generate_qr_code(booking_id, verification_url)

    try:
        s3_key = f"qr_codes/{booking_id}/qr_code.png"
        utils.s3_client.upload_file(
            qr_path,
            utils.media_bucket,
            s3_key,
            ExtraArgs={'ContentType': 'image/png'}
        )
        qr_url = f"https://{utils.media_bucket}.s3.amazonaws.com/{s3_key}"
        logger.debug(f"Uploaded QR code to S3: {qr_url}")
        utils.log_to_cloudwatch(f"Uploaded QR code for booking {booking_id}: {qr_url}")

        booking.qr_code_url = qr_url
        booking.save()
        logger.debug(f"Updated booking {booking_id} with QR code URL")
        utils.log_to_cloudwatch(f"Updated booking {booking_id} with QR code URL: {qr_url}")

        message_body = (
            f"Your QR code for your booking at {booking_details['parking_name']} is ready!\n"
            f"Spot: {booking_details['spot_number']}\n"
            f"Start: {booking_details['start_time']}\n"
            f"End: {booking_details['end_time']}\n"
            f"Price: €{booking_details['total_price']:.2f}\n"
            f"Click here to view your QR code: [View Your QR Code]({qr_url})"
        )
        notification_status = utils.notify_user(user_email, "Your QR Code for Parking Booking", message_body)
        logger.info(f"Notified user {user_email} for booking {booking_id} with status: {notification_status}")
        utils.log_to_cloudwatch(f"Notified user {user_email} for booking {booking_id} with status: {notification_status}")

        if notification_status in ["success", "pending_confirmation", "no_subscription"]:
            return True
        else:
            return False

    except Exception as e:
        logger.error(f"Error processing booking {booking_id}: {str(e)}")
        utils.log_to_cloudwatch(f"Error processing booking {booking_id}: {str(e)}", level='ERROR')
        return False

    finally:
        try:
            os.remove(qr_path)
            logger.debug(f"Deleted temporary QR code file: {qr_path}")
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {qr_path}: {str(e)}")

def process_sqs_messages():
    logger.info("Starting SQS worker...")
    while True:
        try:
            response = utils.sqs_client.receive_message(
                QueueUrl=utils.queue_url,
                MaxNumberOfMessages=1,
                WaitTimeSeconds=20,
                MessageAttributeNames=['All']
            )
            if 'Messages' not in response:
                logger.debug("No messages in queue")
                continue

            for message in response['Messages']:
                success = process_message(message)
                if success:
                    utils.sqs_client.delete_message(
                        QueueUrl=utils.queue_url,
                        ReceiptHandle=message['ReceiptHandle']
                    )
                    body = json.loads(message['Body'])
                    booking_id = body.get('booking_id')
                    logger.info(f"Processed and deleted SQS message for booking {booking_id}")
                    utils.log_to_cloudwatch(f"Processed and deleted SQS message for booking {booking_id}")
                else:
                    logger.warning("Message processing failed; message will be retried after visibility timeout")

        except Exception as e:
            logger.error(f"Error polling SQS queue: {str(e)}")
            utils.log_to_cloudwatch(f"Error polling SQS queue: {str(e)}", level='ERROR')
            continue

if __name__ == "__main__":
    process_sqs_messages()