# parking/urls.py
from django.urls import path
from . import views

app_name = 'parking'

urlpatterns = [
    path('', views.parking_list, name='parking_list'),
    path('book/<uuid:spot_id>/', views.book_spot, name='book_spot'),
    path('confirmation/<uuid:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('my_bookings/', views.my_bookings, name='my_bookings'),
    path('history/', views.booking_history, name='booking_history'),
    path('modify/<uuid:booking_id>/', views.modify_booking, name='modify_booking'),
    path('cancel/<uuid:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('profile/', views.profile, name='profile'),
    path('signup/', views.signup, name='signup'),
    path('admin/daily_bookings/', views.daily_bookings, name='daily_bookings'),
    path('verify/<uuid:booking_id>/', views.verify_booking, name='verify_booking'),
    path('verify/', views.verify_booking_scan, name='verify_booking_scan'),  # New route for scanning
]