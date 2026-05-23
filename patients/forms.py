from django import forms
from .models import Patient
from datetime import date
import re

class PatientRegistrationForm(forms.ModelForm):
    """Form for registering new patients"""
    
    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'gender', 'date_of_birth',
            'phone_number', 'email', 'national_id', 'marital_status',
            'village', 'cell', 'sector', 'district', 'landmark',
            'emergency_name', 'emergency_relationship', 'emergency_phone',
            'weight_kg', 'height_cm', 'blood_pressure_systolic', 'blood_pressure_diastolic',
            'temperature_c', 'pulse_rate',
            'known_conditions', 'current_medications', 'allergies', 'past_surgeries',
            'is_pregnant'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
            'gender': forms.Select(attrs={'class': 'form-control', 'id': 'genderSelect'}),
            'date_of_birth': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+XXX XXXXXXXXX'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'patient@example.com'}),
            'national_id': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional'}),
            'marital_status': forms.Select(attrs={'class': 'form-control'}),
            'village': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter village name'}),
            'cell': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter cell'}),
            'sector': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter sector'}),
            'district': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter district'}),
            'landmark': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Optional - e.g., Near church'}),
            'emergency_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name of emergency contact'}),
            'emergency_relationship': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Spouse, Parent'}),
            'emergency_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+XXX XXXXXXXXX'}),
            'weight_kg': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Weight in kg', 'step': '0.1'}),
            'height_cm': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Height in cm', 'step': '0.1'}),
            'blood_pressure_systolic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Systolic (top number)'}),
            'blood_pressure_diastolic': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Diastolic (bottom number)'}),
            'temperature_c': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Temperature in °C', 'step': '0.1'}),
            'pulse_rate': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Pulse rate (bpm)'}),
            'known_conditions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'List any known medical conditions'}),
            'current_medications': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'List current medications'}),
            'allergies': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'List any allergies'}),
            'past_surgeries': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Optional - List past surgeries'}),
            'is_pregnant': forms.Select(attrs={'class': 'form-control', 'id': 'pregnancySelect'}),
        }
    
    def clean_phone_number(self):
        """Validate phone number - accepts any country code followed by 9 digits"""
        phone = self.cleaned_data.get('phone_number')
        
        if not phone:
            raise forms.ValidationError('Phone number is required')
        
        # Remove any spaces, dashes, parentheses, or plus sign for validation
        cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Pattern: Plus sign optional, then country code (1-3 digits), then exactly 9 digits
        # This matches formats like: +123456789012, 123456789012, +1 234 567 8901, etc.
        pattern = r'^\+?\d{1,3}\d{9}$'
        
        if not re.match(pattern, cleaned_phone):
            raise forms.ValidationError(
                'Phone number must include country code followed by exactly 9 digits. '
                'Examples: +123456789012, +23456789012, 123456789012'
            )
        
        # Return the phone number in a consistent format (with plus sign)
        if not cleaned_phone.startswith('+'):
            # Add plus sign if it doesn't have one
            # Extract country code (assuming first 1-3 digits are country code)
            # This is a simple approach - we'll just add the plus sign
            cleaned_phone = '+' + cleaned_phone
        
        return cleaned_phone
    
    def clean_emergency_phone(self):
        """Validate emergency phone number - accepts any country code followed by 9 digits"""
        phone = self.cleaned_data.get('emergency_phone')
        
        if not phone:
            raise forms.ValidationError('Emergency phone number is required')
        
        # Remove any spaces, dashes, parentheses, or plus sign for validation
        cleaned_phone = re.sub(r'[\s\-\(\)]', '', phone)
        
        # Pattern: Plus sign optional, then country code (1-3 digits), then exactly 9 digits
        pattern = r'^\+?\d{1,3}\d{9}$'
        
        if not re.match(pattern, cleaned_phone):
            raise forms.ValidationError(
                'Emergency phone number must include country code followed by exactly 9 digits. '
                'Examples: +123456789012, +23456789012, 123456789012'
            )
        
        # Return the phone number in a consistent format (with plus sign)
        if not cleaned_phone.startswith('+'):
            cleaned_phone = '+' + cleaned_phone
        
        return cleaned_phone
    
    def clean_date_of_birth(self):
        dob = self.cleaned_data.get('date_of_birth')
        if dob and dob > date.today():
            raise forms.ValidationError('Date of birth cannot be in the future')
        return dob
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            # Basic email validation
            if '@' not in email or '.' not in email:
                raise forms.ValidationError('Enter a valid email address')
        return email