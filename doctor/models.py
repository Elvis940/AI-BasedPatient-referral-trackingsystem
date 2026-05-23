from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient
from referrals.models import Referral

class Prescription(models.Model):
    """Doctor's prescription for a patient"""
    
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('expired', 'Expired'),
    )
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='prescriptions')
    referral = models.ForeignKey(Referral, on_delete=models.SET_NULL, null=True, blank=True, related_name='prescriptions')
    
    # Prescription Details
    diagnosis = models.TextField()
    medications = models.TextField(help_text="Medication name, dosage, frequency")
    instructions = models.TextField(blank=True, help_text="Additional instructions for patient")
    duration_days = models.IntegerField(default=7)
    
    # Vital Signs at time of prescription
    blood_pressure = models.CharField(max_length=20, blank=True)
    temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    pulse_rate = models.IntegerField(null=True, blank=True)
    weight = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Prescription for {self.patient.full_name} - Dr. {self.doctor.get_full_name()}"
    
    class Meta:
        ordering = ['-created_at']