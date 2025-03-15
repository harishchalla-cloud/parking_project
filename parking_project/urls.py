from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.views import LoginView, LogoutView
from django.views.generic import RedirectView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('parking/', include('parking.urls')),
    path('accounts/login/', LoginView.as_view(), name='login'),
    path('accounts/logout/', LogoutView.as_view(template_name='registration/logout.html'), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    path('', RedirectView.as_view(url='/parking/', permanent=False)),
]