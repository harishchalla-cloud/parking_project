from django.contrib import admin
from .models import ParkingSpot, Booking, Spot
from .parking_utils import ParkingUtils
import logging
import os
import tempfile

logger = logging.getLogger('django')

class SpotInline(admin.TabularInline):
    model = Spot
    extra = 0
    readonly_fields = ('spot_number',)

class ParkingSpotAdmin(admin.ModelAdmin):
    list_display = ('parking_name', 'location', 'price', 'total_spots', 'available_spots_count', 'image')
    search_fields = ('parking_name', 'location')
    inlines = [SpotInline]

    def save_model(self, request, obj, form, change):
        logger.debug(f"Starting save_model for {obj}")
        utils = ParkingUtils('x23417498-parking-s3', 'x23417498-parking-static')
        try:
            if 'image' in request.FILES:
                image_file = request.FILES['image']
                logger.debug(f"Processing image: {image_file.name}, size: {image_file.size}")
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, image_file.name)
                with open(temp_path, 'wb') as f:
                    for chunk in image_file.chunks():
                        f.write(chunk)
                # Upload original image (no resizing)
                utils.resize_image(temp_path, temp_path)  # No size param = original
                obj.image = f"parking_spots/{image_file.name}"
                os.remove(temp_path)
                logger.debug(f"Uploaded image to S3: {obj.image}")
            super().save_model(request, obj, form, change)
            logger.debug(f"Model saved: {obj}")
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            raise

    def available_spots_count(self, obj):
        return obj.available_spots().count()
    available_spots_count.short_description = 'Available Spots'

class BookingAdmin(admin.ModelAdmin):
    list_display = ('booking_id', 'user', 'spot', 'start_time', 'end_time', 'vehicle_number', 'total_price')
    list_filter = ('user', 'start_time')
    search_fields = ('user__username', 'vehicle_number', 'spot__parking_spot__parking_name')

admin.site.register(ParkingSpot, ParkingSpotAdmin)
admin.site.register(Booking, BookingAdmin)
admin.site.register(Spot)