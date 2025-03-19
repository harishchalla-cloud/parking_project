import uuid
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

class ParkingSpot(models.Model):
    spot_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    parking_name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    total_spots = models.PositiveIntegerField(default=1)
    price = models.DecimalField(max_digits=6, decimal_places=2)  # Price per hour
    image = models.ImageField(upload_to='parking_spots/', blank=True, null=True)

    class Meta:
        db_table = 'ParkingSpots'

    def __str__(self):
        return f"{self.parking_name} - {self.location}"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        current_spots = self.spots.count()
        logger.debug(f"Saving {self.parking_name}: Total Spots={self.total_spots}, Current Spots={current_spots}")
        if current_spots < self.total_spots:
            for i in range(current_spots + 1, self.total_spots + 1):
                spot_number = f"Spot {i}"
                if not Spot.objects.filter(parking_spot=self, spot_number=spot_number).exists():
                    Spot.objects.create(parking_spot=self, spot_number=spot_number)
                    logger.debug(f"Created {spot_number} for {self.parking_name}")
        elif current_spots > self.total_spots:
            excess_spots = Spot.objects.filter(parking_spot=self)[self.total_spots:]
            for spot in excess_spots:
                if not spot.is_booked():
                    spot.delete()
                    logger.debug(f"Deleted excess {spot.spot_number} from {self.parking_name}")

    def available_spots(self):
        """Return spots that are not booked or whose bookings have ended."""
        now = timezone.now()
        available = self.spots.filter(
            models.Q(booking__isnull=True) |
            models.Q(booking__end_time__lt=now)
        ).distinct()
        logger.debug(f"{self.parking_name}: Available spots count={available.count()} at {now}")
        return available

    def is_available(self):
        """Return True if any spots are available."""
        result = self.available_spots().exists()
        logger.debug(f"{self.parking_name}: Is available? {result}")
        return result

class Spot(models.Model):
    parking_spot = models.ForeignKey(ParkingSpot, related_name='spots', on_delete=models.CASCADE)
    spot_number = models.CharField(max_length=50)

    class Meta:
        db_table = 'Spots'
        unique_together = ('parking_spot', 'spot_number')

    def __str__(self):
        return f"{self.parking_spot.parking_name} - {self.spot_number}"

    def is_booked(self):
        """Check if the spot is currently booked."""
        now = timezone.now()
        booked = Booking.objects.filter(
            spot=self,
            start_time__lte=now,
            end_time__gte=now
        ).exists()
        logger.debug(f"{self}: Is booked? {booked} at {now}")
        return booked

class Booking(models.Model):
    booking_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    spot = models.ForeignKey(Spot, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    vehicle_number = models.CharField(max_length=20)
    total_price = models.DecimalField(max_digits=6, decimal_places=2)

    class Meta:
        db_table = 'Bookings'

    def __str__(self):
        return f"Booking {self.booking_id} by {self.user.username} for {self.spot}"

    def is_active(self):
        """Check if the booking is still active."""
        return self.end_time > timezone.now()

    def calculate_price(self):
        """Calculate total price based on duration and spot price."""
        duration = (self.end_time - self.start_time).total_seconds() / 3600  # Hours
        return round(self.spot.parking_spot.price * duration, 2)