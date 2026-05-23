from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

class UserProfile(models.Model):
    """Extended user profile with additional fields"""
    
    USER_TYPES = (
        ('doctor', 'Doctor'),
        ('chw', 'Community Health Worker'),
    )
    
    STATUS_CHOICES = (
        ('pending', 'Pending Activation'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('suspended', 'Suspended'),
    )
    
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    HOSPITAL_CHOICES = (
        ('jj_dossen', 'J.J. Dossen Memorial Hospital'),
        ('other', 'Other'),
    )
    
    # Medical Specializations for Doctors
    SPECIALIZATION_CHOICES = (
        ('general_practice', 'General Practice'),
        ('cardiology', 'Cardiology'),
        ('pediatrics', 'Pediatrics'),
        ('gynecology', 'Gynecology & Obstetrics'),
        ('ophthalmology', 'Ophthalmology (Eyes)'),
        ('orthopedics', 'Orthopedics'),
        ('neurology', 'Neurology'),
        ('dermatology', 'Dermatology'),
        ('psychiatry', 'Psychiatry'),
        ('radiology', 'Radiology'),
        ('surgery', 'Surgery'),
        ('anesthesiology', 'Anesthesiology'),
        ('emergency_medicine', 'Emergency Medicine'),
        ('internal_medicine', 'Internal Medicine'),
        ('family_medicine', 'Family Medicine'),
        ('dentistry', 'Dentistry'),
        ('ent', 'Ear, Nose & Throat (ENT)'),
        ('urology', 'Urology'),
        ('nephrology', 'Nephrology'),
        ('endocrinology', 'Endocrinology'),
        ('pulmonology', 'Pulmonology'),
        ('rheumatology', 'Rheumatology'),
        ('infectious_disease', 'Infectious Disease'),
        ('oncology', 'Oncology'),
        ('hematology', 'Hematology'),
        ('other', 'Other (Specify)'),
    )
    
    # Availability Status Choices
    AVAILABILITY_CHOICES = (
        ('available', 'Available'),
        ('busy', 'Busy'),
        ('on_leave', 'On Leave'),
        ('off_duty', 'Off Duty'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='chw')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Personal Information
    chw_id = models.CharField(max_length=20, blank=True, unique=True, null=True)
    doctor_id = models.CharField(max_length=20, blank=True, unique=True, null=True)
    
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, blank=True)
    
    phone_number = models.CharField(max_length=15, blank=True)
    email = models.EmailField(blank=True)
    home_address = models.TextField(blank=True)
    
    # Hospital Information
    hospital_name = models.CharField(max_length=100, choices=HOSPITAL_CHOICES, default='jj_dossen')
    hospital_id = models.CharField(max_length=20, blank=True)
    
    # Professional Information (Doctor only)
    department = models.CharField(max_length=100, blank=True)
    specialization = models.CharField(max_length=100, choices=SPECIALIZATION_CHOICES, blank=True)
    custom_specialization = models.CharField(max_length=100, blank=True, help_text="Enter custom specialization if 'Other' is selected")
    
    # CHW only
    assigned_village = models.CharField(max_length=100, blank=True)
    
    # Doctor Professional Details (Simplified)
    license_number = models.CharField(max_length=50, blank=True, null=True, help_text="Medical license number")
    years_of_experience = models.IntegerField(default=0)
    availability_status = models.CharField(max_length=20, choices=AVAILABILITY_CHOICES, default='available')
    
    # Performance Metrics (for AI and referrals)
    success_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    avg_response_time = models.IntegerField(default=0)
    patient_rating = models.DecimalField(max_digits=3, decimal_places=2, default=0.00)
    consultation_capacity = models.IntegerField(default=20)
    
    # System Information
    activation_token = models.CharField(max_length=100, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(blank=True, null=True)
    last_activity = models.DateTimeField(null=True, blank=True)
    
    # Permissions
    can_create_patients = models.BooleanField(default=True)
    can_edit_patients = models.BooleanField(default=True)
    can_delete_patients = models.BooleanField(default=False)
    can_create_referrals = models.BooleanField(default=True)
    can_edit_referrals = models.BooleanField(default=True)
    can_view_reports = models.BooleanField(default=False)
    can_manage_users = models.BooleanField(default=False)
    
    @property
    def full_specialization(self):
        """Return the full specialization name (including custom if other)"""
        if self.specialization == 'other' and self.custom_specialization:
            return self.custom_specialization
        return dict(self.SPECIALIZATION_CHOICES).get(self.specialization, self.specialization)
    
    def save(self, *args, **kwargs):
        # Generate ID based on user type if not provided
        if not self.chw_id and self.user_type == 'chw':
            last_chw = UserProfile.objects.filter(user_type='chw').order_by('-id').first()
            if last_chw and last_chw.chw_id:
                last_num = int(last_chw.chw_id[1:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.chw_id = f"P{new_num:03d}"
        
        if not self.doctor_id and self.user_type == 'doctor':
            last_doctor = UserProfile.objects.filter(user_type='doctor').order_by('-id').first()
            if last_doctor and last_doctor.doctor_id:
                last_num = int(last_doctor.doctor_id[1:])
                new_num = last_num + 1
            else:
                new_num = 1
            self.doctor_id = f"D{new_num:03d}"
        
        super().save(*args, **kwargs)
    
    def activate(self):
        """Activate user account"""
        self.status = 'active'
        self.activated_at = timezone.now()
        self.save()
    
    def is_pending_activation(self):
        """Check if account is pending activation"""
        return self.status == 'pending'
    
    def should_auto_activate(self):
        """Check if account should be auto-activated (after 2 minutes)"""
        if self.status == 'pending':
            time_created = self.created_at
            time_now = timezone.now()
            if time_now - time_created > timedelta(minutes=2):
                return True
        return False
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_user_type_display()}"
    
    class Meta:
        db_table = 'user_profiles'
        ordering = ['-created_at']
        verbose_name = 'User Profile'
        verbose_name_plural = 'User Profiles'


class UserActivityLog(models.Model):
    """Log all user activities"""
    
    ACTIVITY_TYPES = (
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('create', 'Create'),
        ('update', 'Update'),
        ('delete', 'Delete'),
        ('view', 'View'),
        ('export', 'Export'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    description = models.TextField()
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.activity_type} - {self.timestamp}"
    
    class Meta:
        db_table = 'user_activity_logs'
        ordering = ['-timestamp']
        verbose_name_plural = 'User Activity Logs'


class UserActivationLog(models.Model):
    """Track user activation events"""
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activation_logs')
    activated_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='activated_users')
    activated_at = models.DateTimeField(auto_now_add=True)
    activation_type = models.CharField(max_length=20, choices=[('auto', 'Automatic'), ('manual', 'Manual')])
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    
    def __str__(self):
        return f"{self.user.username} activated by {self.activated_by or 'Auto'} at {self.activated_at}"
    
    class Meta:
        db_table = 'user_activation_logs'
        ordering = ['-activated_at']