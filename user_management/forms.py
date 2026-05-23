from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
import re
from .models import UserProfile

class UserCreateForm(forms.ModelForm):
    """Enhanced form for creating new users with doctor-specific fields"""
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Enter password'}),
        required=True
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Confirm password'}),
        required=True
    )
    user_type = forms.ChoiceField(
        choices=UserProfile.USER_TYPES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'user_type'})
    )
    
    # Common fields
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter first name'}),
        required=True
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter last name'}),
        required=True
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Enter email address'}),
        required=True
    )
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+231 123 456 789'}),
        required=True
    )
    gender = forms.ChoiceField(
        choices=UserProfile.GENDER_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    home_address = forms.CharField(
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Enter home address'}),
        required=True
    )
    hospital_name = forms.ChoiceField(
        choices=UserProfile.HOSPITAL_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=True
    )
    hospital_id = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Hospital assigned ID'}),
        required=False
    )
    
    # Doctor specific fields
    department = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Department (e.g., Medicine, Surgery)'}),
        required=False
    )
    specialization = forms.ChoiceField(
        choices=UserProfile.SPECIALIZATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'specialization'}),
        required=False
    )
    custom_specialization = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your specialization (e.g., Eye Specialist)'}),
        required=False
    )
    
    # Doctor Simplified Fields
    license_number = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., MD-2024-00123'}),
        required=False
    )
    years_of_experience = forms.IntegerField(
        widget=forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'max': '50', 'placeholder': 'Years of experience'}),
        required=False
    )
    availability_status = forms.ChoiceField(
        choices=UserProfile.AVAILABILITY_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control'}),
        required=False
    )
    
    # CHW specific fields
    assigned_village = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Assigned village'}),
        required=False
    )
    
    class Meta:
        model = User
        fields = ['username']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter username'}),
        }
    
    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')
        # Allow any number that starts with + followed by country code
        # Minimum 10 digits, maximum 15 digits total
        pattern = r'^\+\d{9,15}$'
        if not re.match(pattern, phone):
            raise ValidationError('Phone number must start with country code (e.g., +231123456789)')
        return phone
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('Username already exists')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('Email already registered')
        return email
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')
        user_type = cleaned_data.get('user_type')
        specialization = cleaned_data.get('specialization')
        custom_specialization = cleaned_data.get('custom_specialization')
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError("Passwords do not match")
        
        # Validate doctor-specific fields
        if user_type == 'doctor':
            if not cleaned_data.get('department'):
                self.add_error('department', 'Department is required for doctors')
            
            if not specialization:
                self.add_error('specialization', 'Specialization is required for doctors')
            
            if specialization == 'other' and not custom_specialization:
                self.add_error('custom_specialization', 'Please specify your specialization')
        
        # Validate CHW-specific fields
        if user_type == 'chw':
            if not cleaned_data.get('assigned_village'):
                self.add_error('assigned_village', 'Assigned village is required for CHWs')
        
        return cleaned_data
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.email = self.cleaned_data['email']
        
        if commit:
            user.save()
            
            # Handle specialization for doctors
            specialization = self.cleaned_data.get('specialization', '')
            custom_specialization = self.cleaned_data.get('custom_specialization', '')
            
            if specialization == 'other' and custom_specialization:
                final_specialization = 'other'
            else:
                final_specialization = specialization
            
            # Create user profile
            profile_data = {
                'user': user,
                'user_type': self.cleaned_data['user_type'],
                'status': 'pending',
                'first_name': self.cleaned_data['first_name'],
                'last_name': self.cleaned_data['last_name'],
                'gender': self.cleaned_data['gender'],
                'phone_number': self.cleaned_data['phone_number'],
                'email': self.cleaned_data['email'],
                'home_address': self.cleaned_data['home_address'],
                'hospital_name': self.cleaned_data['hospital_name'],
                'hospital_id': self.cleaned_data.get('hospital_id', ''),
                'department': self.cleaned_data.get('department', ''),
                'specialization': final_specialization,
                'custom_specialization': custom_specialization if final_specialization == 'other' else '',
                'assigned_village': self.cleaned_data.get('assigned_village', ''),
            }
            
            # Add doctor-specific fields if user is doctor
            if self.cleaned_data['user_type'] == 'doctor':
                profile_data['license_number'] = self.cleaned_data.get('license_number', '')
                profile_data['years_of_experience'] = self.cleaned_data.get('years_of_experience', 0)
                profile_data['availability_status'] = self.cleaned_data.get('availability_status', 'available')
                profile_data['consultation_capacity'] = 20
                profile_data['success_rate'] = 0
                profile_data['avg_response_time'] = 0
                profile_data['patient_rating'] = 0
            
            profile = UserProfile.objects.create(**profile_data)
        
        return user


class UserEditForm(forms.ModelForm):
    """Form for editing existing users"""
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
        }


class UserProfileForm(forms.ModelForm):
    """Form for editing user profile with doctor fields"""
    
    specialization = forms.ChoiceField(
        choices=UserProfile.SPECIALIZATION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'edit_specialization'}),
        required=False
    )
    custom_specialization = forms.CharField(
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Enter your specialization'}),
        required=False
    )
    
    class Meta:
        model = UserProfile
        fields = [
            'user_type', 'status', 'phone_number', 'gender',
            'home_address', 'department', 'assigned_village', 
            'hospital_name', 'hospital_id',
            'license_number', 'years_of_experience',
            'availability_status',
            'can_create_patients', 'can_edit_patients', 'can_delete_patients',
            'can_create_referrals', 'can_edit_referrals', 'can_view_reports',
            'can_manage_users'
        ]
        widgets = {
            'phone_number': forms.TextInput(attrs={'class': 'form-control'}),
            'home_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'department': forms.TextInput(attrs={'class': 'form-control'}),
            'assigned_village': forms.TextInput(attrs={'class': 'form-control'}),
            'user_type': forms.Select(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'hospital_name': forms.Select(attrs={'class': 'form-control'}),
            'hospital_id': forms.TextInput(attrs={'class': 'form-control'}),
            'gender': forms.Select(attrs={'class': 'form-control'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control'}),
            'years_of_experience': forms.NumberInput(attrs={'class': 'form-control'}),
            'availability_status': forms.Select(attrs={'class': 'form-control'}),
            'can_create_patients': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_edit_patients': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_delete_patients': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_create_referrals': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_edit_referrals': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_view_reports': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'can_manage_users': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        specialization = cleaned_data.get('specialization')
        custom_specialization = cleaned_data.get('custom_specialization')
        
        if specialization == 'other' and not custom_specialization:
            self.add_error('custom_specialization', 'Please specify your specialization')
        
        return cleaned_data
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Handle specialization
        specialization = self.cleaned_data.get('specialization')
        custom_specialization = self.cleaned_data.get('custom_specialization')
        
        if specialization == 'other' and custom_specialization:
            profile.specialization = 'other'
            profile.custom_specialization = custom_specialization
        else:
            profile.specialization = specialization
            profile.custom_specialization = ''
        
        if commit:
            profile.save()
        
        return profile