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
                s3_key = str(spot.image).split('/')[-2] + '/' + str(spot.image).split('/')[-1]
                spot.image_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': 'x23417498-parking-s3', 'Key': s3_key},
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
        form = BookingForm(request.POST)
        if form.is_valid():
            start_time = form.cleaned_data["start_time"]
            end_time = form.cleaned_data["end_time"]
            vehicle_number = form.cleaned_data["vehicle_number"]
            if not utils.check_spot_availability(parking_spot, start_time, end_time):
                messages.error(request, f"No available spots at {parking_spot.parking_name} for this time.")
                return redirect("parking:parking_list")
            duration_hours = (end_time - start_time).total_seconds() / 3600
            total_price = Decimal(parking_spot.price) * Decimal(duration_hours)
            booking_id = uuid.uuid4()
            available_spot = parking_spot.available_spots().first()
            result = add_booking(booking_id, request.user, available_spot, start_time, end_time, vehicle_number, total_price)
            if "message" in result:
                utils.notify_user(
                    request.user.email,
                    "Booking Confirmation",
                    f"Your booking for {parking_spot.parking_name} is confirmed!\n"
                    f"Spot: {available_spot.spot_number}\nStart: {start_time}\nEnd: {end_time}\nVehicle: {vehicle_number}\nPrice: €{total_price:.2f}"
                )
                messages.success(request, f"Booking created! Spot: {available_spot.spot_number}")
                return redirect("parking:booking_confirmation", booking_id=booking_id)
            else:
                messages.error(request, "Failed to create booking.")
    else:
        form = BookingForm()
    total_price = None
    if 'start_time' in request.POST and 'end_time' in request.POST:
        try:
            start_time = form.fields['start_time'].to_python(request.POST['start_time'])
            end_time = form.fields['end_time'].to_python(request.POST['end_time'])
            if start_time and end_time and end_time > start_time:
                duration_hours = (end_time - start_time).total_seconds() / 3600
                total_price = Decimal(parking_spot.price) * Decimal(duration_hours)
        except:
            total_price = None
    return render(request, "parking/book_spot.html", {"form": form, "spot": parking_spot, "total_price": total_price})

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
    bookings = Booking.objects.filter(user=request.user)
    return render(request, "parking/my_bookings.html", {"bookings": bookings})

@login_required
def cancel_booking(request, booking_id):
    booking = get_object_or_404(Booking, booking_id=booking_id, user=request.user)
    result = delete_booking(booking_id)
    if result:
        utils.notify_user(
            request.user.email,
            "Booking Cancelled",
            f"Your booking for {booking.spot.parking_spot.parking_name} cancelled!\n"
            f"Spot: {booking.spot.spot_number}\nStart: {booking.start_time}\nEnd: {booking.end_time}\nVehicle: {booking.vehicle_number}"
        )
        messages.success(request, "Booking canceled!")
    else:
        messages.error(request, "Failed to cancel booking.")
    return redirect("parking:my_bookings")

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