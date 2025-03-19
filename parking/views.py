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
import logging
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger('django')

utils = ParkingUtils(settings.AWS_STORAGE_BUCKET_NAME, settings.AWS_STORAGE_BUCKET_NAME)

def parking_list(request):
    query = request.GET.get("q")
    spots = ParkingSpot.objects.all()
    if query:
        spots = spots.filter(Q(location__icontains=query) | Q(parking_name__icontains=query))
        if not spots.exists():
            messages.warning(request, f"No parking spots found for '{query}'.")
    s3_client = boto3.client('s3')
    for spot in spots:
        spot.image_url = None
        if spot.image:
            try:
                # Ensure the S3 key matches the uploaded file path
                s3_key = str(spot.image)  # e.g., 'parking_spots/image.jpg'
                spot.image_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': settings.AWS_STORAGE_BUCKET_NAME, 'Key': s3_key},
                    ExpiresIn=3600
                )
            except Exception as e:
                logger.error(f"Error generating URL for {spot.image}: {str(e)}")
                messages.error(request, f"Error loading image for {spot.parking_name}: {str(e)}")
    return render(request, "parking/list.html", {"spots": spots, "query": query})

@login_required
def book_spot(request, spot_id):
    parking_spot = get_object_or_404(ParkingSpot, spot_id=spot_id)
    if request.method == "POST":
        if request.POST.get("confirm"):  # Confirmation step
            form = BookingForm(request.POST)
            if form.is_valid():
                start_time = form.cleaned_data["start_time"]
                end_time = form.cleaned_data["end_time"]
                vehicle_number = form.cleaned_data["vehicle_number"]
                if not utils.check_spot_availability(parking_spot, start_time, end_time):
                    messages.error(request, f"No available spots at {parking_spot.parking_name}.")
                    return redirect("parking:parking_list")
                duration_hours = (end_time - start_time).total_seconds() / 3600
                total_price = Decimal(parking_spot.price) * Decimal(duration_hours)
                available_spot = parking_spot.available_spots().first()
                booking_id = add_booking(available_spot.pk, request.user, start_time, end_time, vehicle_number, total_price)
                if booking_id:
                    utils.notify_user(
                        request.user.email,
                        "Booking Confirmed",
                        f"Your booking for {parking_spot.parking_name} is confirmed!\nSpot: {available_spot.spot_number}\nStart: {start_time}\nEnd: {end_time}\nPrice: €{total_price:.2f}"
                    )
                    messages.success(request, "Booking confirmed!")
                    return redirect("parking:booking_confirmation", booking_id=booking_id)
                messages.error(request, "Booking failed.")
        else:  # Preview step
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
    if request.method == "POST":
        form = BookingForm(request.POST)
        if form.is_valid():
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]
            vehicle_number = form.cleaned_data["vehicle_number"]
            if not utils.check_spot_availability(booking.spot.parking_spot, start_time, end_time):
                messages.error(request, f"No available spots at {booking.spot.parking_name} for this time.")
                return redirect("parking:my_bookings")
            duration_hours = (end_time - start_time).total_seconds() / 3600
            total_price = Decimal(booking.spot.parking_spot.price) * Decimal(duration_hours)
            result = update_booking(booking_id, start_time, end_time, vehicle_number, total_price)
            if result:
                utils.notify_user(
                    request.user.email,
                    "Booking Modified",
                    f"Your booking for {booking.spot.parking_spot.parking_name} modified!\n"
                    f"Spot: {booking.spot.spot_number}\nNew Start: {start_time}\nNew End: {end_time}\nVehicle: {vehicle_number}\nPrice: €{total_price:.2f}"
                )
                messages.success(request, "Booking updated!")
                return redirect("parking:my_bookings")
            else:
                messages.error(request, "Failed to update booking.")
    else:
        form = BookingForm(initial={"start_time": booking.start_time, "end_time": booking.end_time, "vehicle_number": booking.vehicle_number})
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
    bookings = Booking.objects.filter(user=request.user, end_time__lte=timezone.now())
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
            messages.success(request, "Booking canceled!")
            return redirect("parking:my_bookings")
        messages.error(request, "Failed to cancel booking.")
    return render(request, "parking/confirm_cancel.html", {"booking": booking})


def signup(request):
    if request.method == "POST":
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            utils.notify_user(
                user.email,
                "Welcome to Parking App",
                f"Welcome, {user.username}! Your account is created.\nLogin to book parking spots."
            )
            login(request, user)
            messages.success(request, "Account created! Please check your email.")
            return redirect("parking:parking_list")
    else:
        form = CustomUserCreationForm()
    return render(request, "parking/signup.html", {"form": form})

@login_required
def profile(request):
    return render(request, "parking/profile.html", {"user": request.user})


@login_required
def booking_history(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-start_time')
    return render(request, 'parking/booking_history.html', {'bookings': bookings})