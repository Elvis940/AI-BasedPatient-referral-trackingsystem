from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient

class SymptomAssessment(models.Model):
    """Store AI symptom assessments"""
    
    URGENCY_CHOICES = (
        ('emergency', 'Emergency - Immediate Action'),
        ('urgent', 'Urgent - Within 24 Hours'),
        ('non_urgent', 'Non-Urgent - Within 1-2 Weeks'),
    )
    
    SPECIALIST_CHOICES = (
        ('cardiology', 'Cardiology (Heart)'),
        ('pediatrics', 'Pediatrics (Children)'),
        ('ophthalmology', 'Ophthalmology (Eyes)'),
        ('neurology', 'Neurology (Brain/Nerves)'),
        ('gynecology', 'Gynecology (Women\'s Health)'),
        ('orthopedics', 'Orthopedics (Bones/Joints)'),
        ('general_medicine', 'General Medicine'),
        ('emergency', 'Emergency Department'),
        ('psychiatry', 'Psychiatry (Mental Health)'),
    )
    
    # Link to patient
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='assessments')
    assessed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='assessments')
    
    # Current Symptoms
    primary_complaint = models.CharField(max_length=200)
    symptom_duration = models.CharField(max_length=50, help_text="e.g., 2 hours, 3 days")
    severity_score = models.IntegerField(help_text="1-10 scale (10 = worst)")
    associated_symptoms = models.TextField(blank=True)
    symptom_progression = models.CharField(max_length=20, choices=(
        ('worsening', 'Getting Worse'),
        ('same', 'Staying the Same'),
        ('improving', 'Getting Better'),
    ), default='same')
    
    # Physical Exam Findings
    consciousness = models.CharField(max_length=20, choices=(
        ('alert', 'Alert and Oriented'),
        ('confused', 'Confused'),
        ('unresponsive', 'Unresponsive'),
    ), default='alert')
    breathing_status = models.CharField(max_length=20, choices=(
        ('normal', 'Normal'),
        ('labored', 'Labored'),
        ('wheezing', 'Wheezing'),
        ('absent', 'Absent'),
    ), default='normal')
    skin_condition = models.CharField(max_length=50, blank=True)
    hydration_status = models.CharField(max_length=20, choices=(
        ('normal', 'Normal'),
        ('dry_mouth', 'Dry Mouth'),
        ('sunken_eyes', 'Sunken Eyes'),
    ), default='normal')
    
    # Current Vitals
    current_temperature = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)
    current_bp_systolic = models.IntegerField(null=True, blank=True)
    current_bp_diastolic = models.IntegerField(null=True, blank=True)
    current_pulse = models.IntegerField(null=True, blank=True)
    respiratory_rate = models.IntegerField(null=True, blank=True)
    oxygen_saturation = models.IntegerField(null=True, blank=True)
    
    # AI Predictions
    ai_urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    ai_specialist = models.CharField(max_length=30, choices=SPECIALIST_CHOICES)
    ai_confidence = models.IntegerField(help_text="Confidence percentage 0-100")
    ai_reasoning = models.TextField(blank=True, help_text="AI's reasoning for the recommendation")
    
    # Warning Signs Identified
    warning_signs = models.TextField(blank=True)
    
    # Recommended Actions
    recommended_action = models.TextField(blank=True)
    
    # CHW Feedback
    chw_agreed = models.BooleanField(default=False)
    chw_override = models.CharField(max_length=50, blank=True, null=True)
    chw_notes = models.TextField(blank=True)
    selected_doctor_id = models.IntegerField(null=True, blank=True)
    
    # Tracking
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.ai_urgency} - {self.created_at.date()}"
    
    class Meta:
        ordering = ['-created_at']