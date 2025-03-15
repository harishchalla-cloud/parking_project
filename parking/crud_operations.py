from django.core.exceptions import ObjectDoesNotExist
from .models import ParkingSpot, Booking, Spot

# CRUD Operation for Create Parking Spot
def add_parking_spot(spot_id, parking_name, location, price, total_spots=1, image=None):
    parking_spot = ParkingSpot(
        spot_id=spot_id,
        parking_name=parking_name,
        location=location,
        price=price,
        total_spots=total_spots,
        image=image
    )
    parking_spot.save()  # This triggers Spot creation via save() in models.py
    return {"message": "Parking spot added successfully"}

# CRUD Operation for Get Parking Spot
def get_parking_spot(spot_id):
    try:
        parking_spot = ParkingSpot.objects.get(spot_id=spot_id)
        return {
            'spot_id': str(parking_spot.spot_id),
            'parking_name': parking_spot.parking_name,
            'location': parking_spot.location,
            'price': float(parking_spot.price),
            'total_spots': parking_spot.total_spots,
            'available_spots': parking_spot.available_spots().count()
        }
    except ObjectDoesNotExist:
        return None

# CRUD Operation for Update Parking Spot
def update_parking_spot(spot_id, price=None, total_spots=None):
    try:
        parking_spot = ParkingSpot.objects.get(spot_id=spot_id)
        if price is not None:
            parking_spot.price = price
        if total_spots is not None:
            parking_spot.total_spots = total_spots  # Updating total_spots triggers Spot adjustments in save()
        parking_spot.save()
        return {"message": "Parking spot updated successfully"}
    except ObjectDoesNotExist:
        return None

# CRUD Operation for Delete Parking Spot
def delete_parking_spot(spot_id):
    try:
        parking_spot = ParkingSpot.objects.get(spot_id=spot_id)
        parking_spot.delete()  # Deletes associated Spots via CASCADE
        return {"message": "Parking spot deleted successfully"}
    except ObjectDoesNotExist:
        return None

# CRUD Operation for Add Booking
def add_booking(booking_id, user, spot, start_time, end_time, vehicle_number, total_price):
    try:
        # `spot` is now a Spot instance, not a spot_id
        booking = Booking(
            booking_id=booking_id,
            user=user,
            spot=spot,
            start_time=start_time,
            end_time=end_time,
            vehicle_number=vehicle_number,
            total_price=total_price
        )
        booking.save()
        return {"message": "Booking added successfully"}
    except ObjectDoesNotExist:
        return {"error": "Spot not found"}

# CRUD Operation for Get Booking
def get_booking(booking_id):
    try:
        booking = Booking.objects.get(booking_id=booking_id)
        return {
            'booking_id': str(booking.booking_id),
            'user_id': booking.user.id,
            'spot_id': str(booking.spot.parking_spot.spot_id),  # Reference ParkingSpot ID
            'spot_number': booking.spot.spot_number,  # Unique spot identifier
            'start_time': booking.start_time,
            'end_time': booking.end_time,
            'vehicle_number': booking.vehicle_number,
            'total_price': float(booking.total_price)
        }
    except ObjectDoesNotExist:
        return None

# CRUD Operation for Update Booking
def update_booking(booking_id, start_time=None, end_time=None, vehicle_number=None, total_price=None):
    try:
        booking = Booking.objects.get(booking_id=booking_id)
        if start_time is not None:
            booking.start_time = start_time
        if end_time is not None:
            booking.end_time = end_time
        if vehicle_number is not None:
            booking.vehicle_number = vehicle_number
        if total_price is not None:
            booking.total_price = total_price
        booking.save()
        return {"message": "Booking updated successfully"}
    except ObjectDoesNotExist:
        return None

# CRUD Operation for Delete Booking
def delete_booking(booking_id):
    try:
        booking = Booking.objects.get(booking_id=booking_id)
        booking.delete()
        return {"message": "Booking deleted successfully"}
    except ObjectDoesNotExist:
        return None