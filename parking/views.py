from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib import messages
from django.db.models import Q
from .models import ParkingSpot, Booking, Spot
from .forms import BookingForm, CustomUserCreationForm
from .crud_operations import add_booking, update_booking, delete_booking
from .parking_utils import ParkingUtils
from decimal import Decimal
import uuid
import boto3
import time
import logging
from django.conf import settings
from django.utils import timezone
from datetime import datetime
from datetime import datetime, time as dttime, timedelta
from django.contrib.admin.views.decorators import staff_member_required

logger = logging.getLogger('django')

utils = ParkingUtils(settings.AWS_STORAGE_BUCKET_NAME, settings.AWS_STORAGE_BUCKET_NAME)

def parking_list(request):
    start_time = time.time()
    query = request.GET.get("q")
    spots = ParkingSpot.objects.all().defer('image')
    if query:
        spots = spots.filter(Q(location__icontains=query) | Q(parking_name__icontains=query))
        if not spots.exists():
            messages.warning(request, f"No parking spots found for '{query}'.")
    utils.log_to_cloudwatch(f"DB query took: {time.time() - start_time} seconds")

    s3_start = time.time()
    s3_client = boto3.client('s3')
    spot_list = []
    # Default time range for availability check (next hour)
    now = timezone.now()
    default_start = now + timedelta(hours=1)
    default_end = default_start + timedelta(hours=1)
    for spot in spots:
        # Get available spots count
        available_spots_count = spot.available_spots(start_time=default_start, end_time=default_end).count()
        spot_dict = {
            'spot_id': str(spot.spot_id),
            'parking_name': spot.parking_name,
            'location': spot.location,
            'price': float(spot.price),
            'total_spots': spot.total_spots,
            'image_url': None,
            'is_available': spot.is_available(start_time=default_start, end_time=default_end),
            'available_spots_count': available_spots_count  # Add the count
        }
        if spot.image:
            try:
                s3_key = str(spot.image)
                spot_dict['image_url'] = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': s3_key},
                    ExpiresIn=3600
                )
                utils.log_to_cloudwatch(f"Generated presigned URL for {spot.parking_name}")
            except Exception as e:
                logger.error(f"Error generating URL for {spot.image}: {str(e)}")
                utils.log_to_cloudwatch(f"Error loading image for {spot.parking_name}: {str(e)}", level='ERROR')
                messages.error(request, f"Error loading image for {spot.parking_name}")
        spot_list.append(spot_dict)
    utils.log_to_cloudwatch(f"S3 operations took: {time.time() - s3_start} seconds")
    utils.put_metric('ParkingListRequests', 1)
    utils.log_to_cloudwatch(f"Total parking_list time: {time.time() - start_time} seconds")
    return render(request, "parking/list.html", {"spots": spot_list, "query": query})

@login_required
def book_spot(request, spot_id):
    parking_spot = get_object_or_404(ParkingSpot, spot_id=spot_id)
    if request.method == "POST":
        if request.POST.get("confirm"):
            form = BookingForm(request.POST)
            if form.is_valid():
                start_time = form.cleaned_data["start_time"]
                end_time = form.cleaned_data["end_time"]
                vehicle_number = form.cleaned_data["vehicle_number"]
                utils.log_to_cloudwatch(f"Booking attempt: Spot ID {spot_id}, Start: {start_time}, End: {end_time}")
                # Check availability
                availability = utils.check_spot_availability(parking_spot, start_time, end_time)
                utils.log_to_cloudwatch(f"Availability result: {availability}")
                if not availability:
                    messages.error(request, f"No available spots at {parking_spot.parking_name}.")
                    utils.log_to_cloudwatch(f"Booking failed: No spots available at {parking_spot.parking_name}", level='WARNING')
                    utils.put_metric('BookingFailures', 1)
                    return redirect("parking:parking_list")
                duration_hours = (end_time - start_time).total_seconds() / 3600
                total_price = Decimal(parking_spot.price) * Decimal(duration_hours)
                # Get available spots
                available_spots = parking_spot.available_spots(start_time=start_time, end_time=end_time)
                utils.log_to_cloudwatch(f"Available spots count: {available_spots.count()}")
                for spot in available_spots:
                    utils.log_to_cloudwatch(f"Available spot: {spot.spot_number}")
                available_spot = available_spots.first()
                if not available_spot:
                    messages.error(request, "No available spot found.")
                    utils.log_to_cloudwatch("Booking failed: No available spot found", level='WARNING')
                    utils.put_metric('BookingFailures', 1)
                    return redirect("parking:parking_list")
                utils.log_to_cloudwatch(f"Selected spot for booking: {available_spot.spot_number}")
                booking_id = uuid.uuid4()
                result = add_booking(
                    booking_id,
                    request.user,
                    available_spot,
                    start_time,
                    end_time,
                    vehicle_number,
                    total_price
                )
                utils.log_to_cloudwatch(f"add_booking result: {result}")
                if "message" in result and result["message"] == "Booking added successfully":
                    # Before sending notification, ensure user is subscribed and has confirmed
                    subscription_arn = utils.subscribe_user(request.user.email)
                    if subscription_arn == 'PendingConfirmation':
                        # If still pending confirmation, log and skip the notification
                        utils.log_to_cloudwatch(f"Notification to {request.user.email} pending confirmation", level='WARNING')
                        logger.info(f"User {request.user.email} has not confirmed their subscription yet.")
                        messages.info(request, "Please confirm your email subscription to receive the booking confirmation.")
                        return redirect("parking:booking_confirmation", booking_id=booking_id)

                    # If already confirmed, proceed with notification
                    utils.notify_user(
                        request.user.email,
                        "Booking Confirmed",
                        f"Your booking for {parking_spot.parking_name} is confirmed!\nSpot: {available_spot.spot_number}\nStart: {start_time}\nEnd: {end_time}\nPrice: €{total_price:.2f}"
                    )
                    utils.log_to_cloudwatch(f"Booking confirmed for {parking_spot.parking_name} by {request.user.email}")
                    utils.put_metric('BookingsCreated', 1)
                    messages.success(request, "Booking confirmed!")
                    return redirect("parking:booking_confirmation", booking_id=booking_id)
                messages.error(request, "Booking failed.")
                utils.log_to_cloudwatch(f"Booking failed: {result.get('error', 'Unknown error')}", level='ERROR')
                utils.put_metric('BookingFailures', 1)
        else:
            form = BookingForm(request.POST)
            if form.is_valid():
                start_time = form.cleaned_data["start_time"]
                end_time = form.cleaned_data["end_time"]
                vehicle_number = form.cleaned_data["vehicle_number"]
                duration_hours = (end_time - start_time).total_seconds() / 3600
                total_price = Decimal(parking_spot.price) * Decimal(duration_hours)
                preview = {
                    "start_time": start_time,
                    "end_time": end_time,
                    "vehicle_number": vehicle_number,
                    "total_price": total_price,
                }
                return render(request, "parking/book_spot.html", {"form": form, "spot": parking_spot, "preview": preview})
    else:
        form = BookingForm()
    return render(request, "parking/book_spot.html", {"form": form, "spot": parking_spot})



@login_required
def modify_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    parking_spot = booking.spot.parking_spot
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]
            vehicle_number = form.cleaned_data["vehicle_number"]
            duration_hours = (end_time - start_time).total_seconds() / 3600
            total_price = Decimal(parking_spot.price) * Decimal(duration_hours)
            if parking_spot.is_available(start_time, end_time) or (start_time == booking.start_time and end_time == booking.end_time):
                result = update_booking(booking_id, start_time, end_time, vehicle_number, total_price)
                if "message" in result and result["message"] == "Booking updated successfully":
                    utils.notify_user(
                        request.user.email,
                        "Booking Modified",
                        f"Your booking for {parking_spot.parking_name} has been updated!\nSpot: {booking.spot.spot_number}\nStart: {start_time}\nEnd: {end_time}\nPrice: €{total_price:.2f}"
                    )
                    messages.success(request, "Booking modified successfully!")
                    return redirect("parking:my_bookings")
                messages.error(request, "Failed to modify booking.")
            else:
                messages.error(request, "Spot not available for the selected time.")
    else:
        form = BookingForm(initial={
            "start_time": booking.start_time,
            "end_time": booking.end_time,
            "vehicle_number": booking.vehicle_number
        })
    return render(request, "parking/modify_booking.html", {"form": form, "booking": booking})

@login_required
def booking_confirmation(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    return render(request, "parking/booking_confirmation.html", {"booking": booking})

@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user, end_time__gt=timezone.now())
    return render(request, "parking/my_bookings.html", {"bookings": bookings})

@login_required
def booking_history(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-start_time')
    return render(request, "parking/booking_history.html", {"bookings": bookings})

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    if request.method == "POST" and request.POST.get("confirm") == "yes":
        result = delete_booking(booking_id)
        if result:
            utils.notify_user(
                request.user.email,
                "Booking Cancelled",
                f"Your booking for {booking.spot.parking_spot.parking_name} has been cancelled!\nSpot: {booking.spot.spot_number}"
            )
            utils.log_to_cloudwatch(f"Booking cancelled for {booking.spot.parking_spot.parking_name} by {request.user.email}")
            utils.put_metric('BookingsCancelled', 1)
            messages.success(request, "Booking canceled!")
            return redirect("parking:my_bookings")
        messages.error(request, "Failed to cancel booking.")
        utils.log_to_cloudwatch("Cancellation failed", level='ERROR')
        utils.put_metric('BookingFailures', 1)
    return render(request, "parking/confirm_cancel.html", {"booking": booking})

def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            email_message = (
                f"Dear {user.username},\n\n"
                f"Welcome to the Parking App!\n\n"
                f"Account Details:\n"
                f"Username: {user.username}\n"
                f"Email: {user.email}\n"
                f"Account Created On: {timezone.now()}\n\n"
                f"You can now log in and start booking parking spots. Enjoy our service!"
            )
            notification_status = utils.notify_user(
                user.email,
                "Welcome to Parking App",
                email_message
            )
            login(request, user)
            if notification_status == "pending_confirmation":
                messages.info(request, "Please check your email and confirm your SNS subscription to receive notifications.")
            elif notification_status == "error":
                messages.warning(request, "Account created, but failed to send welcome email. Please check your email settings.")
            messages.success(request, "Account created! Please check your email.")
            return redirect("parking:parking_list")
    else:
        form = CustomUserCreationForm()
    return render(request, "parking/signup.html", {"form": form})

@login_required
def profile(request):
    return render(request, "parking/profile.html", {"user": request.user})

@staff_member_required
def daily_bookings(request):
    today = timezone.now().date()
    start_of_day = timezone.make_aware(datetime.combine(today, dttime.min))
    end_of_day = timezone.make_aware(datetime.combine(today, dttime.max))
    bookings = Booking.objects.filter(start_time__range=(start_of_day, end_of_day))
    total_bookings = bookings.count()
    return render(request, "parking/daily_bookings.html", {
        "bookings": bookings,
        "total_bookings": total_bookings,
        "date": today
    })