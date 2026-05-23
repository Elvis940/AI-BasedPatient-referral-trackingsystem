from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import date

class Patient(models.Model):
    """Patient model for J.J. Dossen Hospital"""
    
    # Gender Choices
    GENDER_CHOICES = (
        ('M', 'Male'),
        ('F', 'Female'),
        ('O', 'Other'),
    )
    
    # Marital Status Choices
    MARITAL_CHOICES = (
        ('single', 'Single'),
        ('married', 'Married'),
        ('divorced', 'Divorced'),
        ('widowed', 'Widowed'),
        ('other', 'Other'),
    )
    
    # Pregnancy Status - Only for females
    PREGNANCY_CHOICES = (
        ('yes', 'Yes'),
        ('no', 'No'),
        ('na', 'Not Applicable'),
    )
    
    # 1. Personal Information
    patient_id = models.CharField(max_length=20, unique=True, editable=False)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField()
    age = models.IntegerField(editable=False)
    phone_number = models.CharField(max_length=20)  # Increased from 15 to 20
    email = models.EmailField(blank=True, null=True, help_text="Patient's email address for communication")
    national_id = models.CharField(max_length=20, blank=True, null=True)
    marital_status = models.CharField(max_length=20, choices=MARITAL_CHOICES, default='single')
    
    # 2. Address Information
    village = models.CharField(max_length=100)
    cell = models.CharField(max_length=100)
    sector = models.CharField(max_length=100)
    district = models.CharField(max_length=100)
    landmark = models.CharField(max_length=200, blank=True, null=True)
    
    # 3. Emergency Contact
    emergency_name = models.CharField(max_length=200)
    emergency_relationship = models.CharField(max_length=100)
    emergency_phone = models.CharField(max_length=20)
    
    # 4. Basic Health Information
    weight_kg = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    blood_pressure_systolic = models.IntegerField(null=True, blank=True)
    blood_pressure_diastolic = models.IntegerField(null=True, blank=True)
    temperature_c = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    pulse_rate = models.IntegerField(null=True, blank=True)
    
    # 5. Medical History
    known_conditions = models.TextField(blank=True)
    current_medications = models.TextField(blank=True)
    allergies = models.TextField(blank=True)
    past_surgeries = models.TextField(blank=True)
    
    # 6. Special Conditions
    is_pregnant = models.CharField(max_length=3, choices=PREGNANCY_CHOICES, default='na')
    
    # System Fields
    registered_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='registered_patients')
    registered_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_visit = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        # Calculate age from date of birth
        if self.date_of_birth:
            today = date.today()
            self.age = today.year - self.date_of_birth.year - (
                (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
            )
        
        # Generate patient ID if not exists
        if not self.patient_id:
            last_patient = Patient.objects.all().order_by('-id').first()
            if last_patient:
                last_id = int(last_patient.patient_id.split('-')[-1])
                new_id = last_id + 1
            else:
                new_id = 1
            self.patient_id = f"JJD-{new_id:05d}"
        
        # If patient is not female, set pregnancy to 'na'
        if self.gender != 'F':
            self.is_pregnant = 'na'
        
        super().save(*args, **kwargs)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    @property
    def bmi(self):
        """Calculate BMI"""
        if self.weight_kg and self.height_cm:
            height_m = self.height_cm / 100
            bmi = self.weight_kg / (height_m ** 2)
            return round(bmi, 1)
        return None
    
    @property
    def blood_pressure_display(self):
        if self.blood_pressure_systolic and self.blood_pressure_diastolic:
            return f"{self.blood_pressure_systolic}/{self.blood_pressure_diastolic}"
        return "Not recorded"
    
    def __str__(self):
        return f"{self.patient_id} - {self.full_name}"
    
    class Meta:
        db_table = 'patients'
        ordering = ['-registered_at']


class PatientVisit(models.Model):
    """Track patient visits and follow-ups"""
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='visits')
    visit_date = models.DateTimeField(auto_now_add=True)
    symptoms = models.TextField()
    diagnosis = models.TextField(blank=True)
    treatment = models.TextField(blank=True)
    referred_to = models.CharField(max_length=200, blank=True)
    referred_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    notes = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.visit_date}"
    
    class Meta:
        db_table = 'patient_visits'
        ordering = ['-visit_date']