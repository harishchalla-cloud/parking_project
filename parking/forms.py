from django import forms
from django.utils import timezone
from datetime import timedelta
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm  # Added import for UserCreationForm

class CustomUserCreationForm(UserCreationForm):  # Changed to inherit from UserCreationForm
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True, help_text="Required. Enter your first name.")
    last_name = forms.CharField(max_length=30, required=True, help_text="Required. Enter your last name.")

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        if commit:
            user.save()
        return user

class BookingForm(forms.Form):
    start_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    end_time = forms.DateTimeField(widget=forms.DateTimeInput(attrs={'type': 'datetime-local'}))
    vehicle_number = forms.CharField(max_length=20)

    def clean_start_time(self):
        start_time = self.cleaned_data['start_time']
        if start_time < timezone.now():
            raise forms.ValidationError("Start time must be in the future.")
        return start_time

    def clean_end_time(self):
        end_time = self.cleaned_data['end_time']
        return end_time

    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        if start_time and end_time:
            duration = end_time - start_time
            duration_hours = duration.total_seconds() / 3600  # Convert to hours including minutes as decimals
            min_duration = 1  # Minimum 1 hour
            max_duration = 12  # Maximum 12 hours

            if duration.total_seconds() <= 0:
                raise forms.ValidationError("End time must be after start time.")
            if duration_hours < min_duration:
                raise forms.ValidationError(f"Booking duration must be at least {min_duration} hour.")
            if duration_hours > max_duration:
                raise forms.ValidationError(f"Booking duration cannot exceed {max_duration} hours.")
        return cleaned_data