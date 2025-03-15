from django.urls import path
from . import views

app_name = 'parking'

urlpatterns = [
    path('', views.parking_list, name='parking_list'),
    path('signup/', views.signup, name='signup'),
    path('book/<uuid:spot_id>/', views.book_spot, name='book_spot'),
    path('my-bookings/', views.my_bookings, name='my_bookings'),
    path('booking-confirmation/<uuid:booking_id>/', views.booking_confirmation, name='booking_confirmation'),
    path('modify-booking/<uuid:booking_id>/', views.modify_booking, name='modify_booking'),
    path('cancel-booking/<uuid:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('profile/', views.profile, name='profile'),
]