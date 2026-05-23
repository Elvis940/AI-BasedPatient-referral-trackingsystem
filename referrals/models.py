from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from patients.models import Patient
from ai_assessment.models import SymptomAssessment

class Referral(models.Model):
    """Patient referral from CHW to Doctor"""
    
    URGENCY_CHOICES = (
        ('emergency', 'Emergency - Immediate'),
        ('urgent', 'Urgent - Within 24 Hours'),
        ('non_urgent', 'Non-Urgent - Within 1-2 Weeks'),
    )
    
    STATUS_CHOICES = (
        ('pending_admin', 'Pending Admin Approval'),  # NEW: Waiting for admin
        ('approved', 'Approved - Awaiting Doctor'),   # NEW: Admin approved
        ('rejected', 'Rejected by Admin'),            # NEW: Admin rejected
        ('accepted', 'Accepted by Doctor'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    )
    
    # Patient Information
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='referrals')
    chw = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='referrals_made')
    doctor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='referrals_received')
    
    # Assessment Link
    assessment = models.ForeignKey(SymptomAssessment, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Referral Details
    referral_code = models.CharField(max_length=20, unique=True, editable=False)
    urgency = models.CharField(max_length=20, choices=URGENCY_CHOICES)
    specialist = models.CharField(max_length=50)
    notes = models.TextField(blank=True)
    
    # Admin Approval Fields (NEW)
    rejection_reason = models.TextField(blank=True, null=True)  # Why admin rejected
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_referrals')
    approved_at = models.DateTimeField(null=True, blank=True)
    rejected_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='rejected_referrals')
    rejected_at = models.DateTimeField(null=True, blank=True)
    
    # Status Tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending_admin')
    status_updated_at = models.DateTimeField(auto_now=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    scheduled_date = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    # Add these fields to Referral model
    chw_notification_sent = models.BooleanField(default=False)
    doctor_notification_sent = models.BooleanField(default=False)
    
    # Tracking Fields
    check_in_time = models.DateTimeField(null=True, blank=True)
    check_out_time = models.DateTimeField(null=True, blank=True)
    treatment_start_date = models.DateTimeField(null=True, blank=True)
    treatment_end_date = models.DateTimeField(null=True, blank=True)
    
    # Follow-up
    follow_up_required = models.BooleanField(default=False)
    follow_up_date = models.DateTimeField(null=True, blank=True)
    
    def save(self, *args, **kwargs):
        if not self.referral_code:
            import random
            import string
            year = timezone.now().year
            random_chars = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            self.referral_code = f"REF-{year}-{random_chars}"
        super().save(*args, **kwargs)
    
    def get_specialist_display(self):
        specialist_map = {
            'cardiology': 'Cardiology',
            'pediatrics': 'Pediatrics',
            'ophthalmology': 'Ophthalmology',
            'neurology': 'Neurology',
            'gynecology': 'Gynecology',
            'orthopedics': 'Orthopedics',
            'general_medicine': 'General Medicine',
            'emergency': 'Emergency',
            'psychiatry': 'Psychiatry',
            'hospital': 'J.J. Dossen Hospital',  # NEW: Hospital fallback
            'general_practice': 'General Practice',
            'emergency_medicine': 'Emergency Medicine',
        }
        return specialist_map.get(self.specialist, self.specialist.replace('_', ' ').title())
    
    def get_urgency_display(self):
        urgency_map = dict(self.URGENCY_CHOICES)
        return urgency_map.get(self.urgency, self.urgency)
    
    def get_status_display(self):
        status_map = dict(self.STATUS_CHOICES)
        return status_map.get(self.status, self.status)
    
    def is_pending_admin(self):
        return self.status == 'pending_admin'
    
    def is_rejected(self):
        return self.status == 'rejected'
    
    def is_approved(self):
        return self.status == 'approved'
    
    @property
    def is_checked_in(self):
        return self.check_in_time is not None
    
    @property
    def is_checked_out(self):
        return self.check_out_time is not None
    
    def __str__(self):
        return f"{self.referral_code} - {self.patient.full_name} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']

class Medication(models.Model):
    """Medications prescribed to a patient"""
    
    MEDICATION_STATUS = (
        ('active', 'Active'),
        ('completed', 'Completed'),
        ('discontinued', 'Discontinued'),
        ('pending', 'Pending'),
    )
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='medications')
    prescribed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='prescribed_medications')
    
    medication_name = models.CharField(max_length=200)
    dosage = models.CharField(max_length=100, help_text="e.g., 500mg")
    frequency = models.CharField(max_length=100, help_text="e.g., Twice daily, Every 8 hours")
    duration_days = models.IntegerField(default=7)
    
    instructions = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=MEDICATION_STATUS, default='active')
    
    prescribed_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.medication_name} - {self.referral.patient.full_name}"
    
    class Meta:
        ordering = ['-prescribed_at']


class ReferralActivity(models.Model):
    """Track referral activities and status changes"""
    
    ACTIVITY_TYPES = (
        ('created', 'Referral Created'),
        ('viewed', 'Referral Viewed'),
        ('pending_admin', 'Pending Admin Approval'),
        ('approved', 'Approved by Admin'),
        ('rejected', 'Rejected by Admin'),
        ('accepted', 'Accepted by Doctor'),
        ('started', 'Treatment Started'),
        ('in_progress', 'Treatment In Progress'),
        ('completed', 'Treatment Completed'),
        ('cancelled', 'Referral Cancelled'),
        ('rejected', 'Referral Rejected'),
        ('rescheduled', 'Appointment Rescheduled'),
    )
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='activities')
    activity_type = models.CharField(max_length=20, choices=ACTIVITY_TYPES)
    performed_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    description = models.TextField(blank=True)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def get_activity_type_display(self):
        activity_map = dict(self.ACTIVITY_TYPES)
        return activity_map.get(self.activity_type, self.activity_type)
    
    def __str__(self):
        return f"{self.referral.referral_code} - {self.activity_type} - {self.timestamp}"
    
    class Meta:
        ordering = ['-timestamp']

class PatientMessage(models.Model):
    """Messages sent to patients (SMS/Email)"""
    
    MESSAGE_CHANNELS = (
        ('sms', 'SMS'),
        ('email', 'Email'),
    )
    
    MESSAGE_STATUS = (
        ('pending', 'Pending'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('delivered', 'Delivered'),
    )
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='messages')
    sent_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    channel = models.CharField(max_length=10, choices=MESSAGE_CHANNELS, default='sms')
    subject = models.CharField(max_length=200, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, choices=MESSAGE_STATUS, default='pending')
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Message to {self.referral.patient.full_name} via {self.channel}"
    
    class Meta:
        ordering = ['-created_at']


class PatientAlert(models.Model):
    """Automated alerts for missed appointments, etc."""
    
    ALERT_TYPES = (
        ('missed_checkin', 'Missed Check-in'),
        ('missed_followup', 'Missed Follow-up'),
        ('medication_reminder', 'Medication Reminder'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('treatment_delay', 'Treatment Delay'),
    )
    
    SEVERITY_CHOICES = (
        ('high', 'High - Immediate Attention'),
        ('medium', 'Medium'),
        ('low', 'Low'),
    )
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=50, choices=ALERT_TYPES)
    severity = models.CharField(max_length=10, choices=SEVERITY_CHOICES, default='medium')
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.get_alert_type_display()} - {self.referral.patient.full_name}"
    
    class Meta:
        ordering = ['-created_at']



class UserNotification(models.Model):
    """Store notifications for users (CHW, Doctor)"""
    
    NOTIFICATION_TYPES = (
        ('referral_approved', 'Referral Approved'),
        ('referral_rejected', 'Referral Rejected'),
        ('referral_created', 'Referral Created'),
        ('appointment_reminder', 'Appointment Reminder'),
        ('message_received', 'Message Received'),
    )
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, null=True, blank=True, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"
    
    class Meta:
        ordering = ['-created_at']

# referrals/models.py - Add these new models

class PatientCommunication(models.Model):
    """Communication between Doctor and CHW about patients"""
    
    COMMUNICATION_TYPES = (
        ('missed_appointment', 'Missed Appointment'),
        ('treatment_update', 'Treatment Update'),
        ('medication_issue', 'Medication Issue'),
        ('follow_up_needed', 'Follow-up Needed'),
        ('emergency_alert', 'Emergency Alert'),
        ('general', 'General Message'),
    )
    
    PRIORITY_CHOICES = (
        ('high', 'High Priority'),
        ('medium', 'Medium Priority'),
        ('low', 'Low Priority'),
    )
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='communications')
    from_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='sent_communications')
    to_user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='received_communications')
    communication_type = models.CharField(max_length=50, choices=COMMUNICATION_TYPES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='medium')
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)
    requires_action = models.BooleanField(default=False)
    action_taken = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.communication_type} - {self.referral.patient.full_name}"


class PatientReport(models.Model):
    """Doctor's report about patient for CHW tracking"""
    
    REPORT_TYPES = (
        ('missed_appointment', 'Missed Appointment'),
        ('treatment_non_compliance', 'Treatment Non-Compliance'),
        ('adverse_reaction', 'Adverse Reaction'),
        ('needs_follow_up', 'Needs Follow-up'),
        ('referred_back', 'Referred Back to CHW'),
        ('discharged', 'Discharged'),
    )
    
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='reports')
    doctor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='patient_reports')
    report_type = models.CharField(max_length=50, choices=REPORT_TYPES)
    title = models.CharField(max_length=200)
    description = models.TextField()
    recommendations = models.TextField(blank=True)
    action_required = models.BooleanField(default=False)
    acknowledged_by_chw = models.BooleanField(default=False)
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.report_type} - {self.referral.patient.full_name}"


class LostPatient(models.Model):
    """Track patients lost to follow-up"""
    
    LOST_REASONS = (
        ('no_contact', 'No Contact'),
        ('moved_away', 'Moved Away'),
        ('refused_treatment', 'Refused Treatment'),
        ('transferred', 'Transferred to Another Facility'),
        ('deceased', 'Deceased'),
        ('other', 'Other'),
    )
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='lost_records')
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='lost_record')
    lost_date = models.DateTimeField(default=timezone.now)
    reason = models.CharField(max_length=50, choices=LOST_REASONS)
    notes = models.TextField()
    chw_notified = models.BooleanField(default=False)
    doctor_notified = models.BooleanField(default=False)
    recovered = models.BooleanField(default=False)
    recovered_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-lost_date']
    
    def __str__(self):
        return f"{self.patient.full_name} - Lost on {self.lost_date.date()}"


class OverdueFollowUp(models.Model):
    """Track overdue follow-up appointments"""
    
    FOLLOW_UP_TYPES = (
        ('appointment', 'Scheduled Appointment'),
        ('medication_check', 'Medication Check'),
        ('test_result', 'Test Result Review'),
        ('treatment_evaluation', 'Treatment Evaluation'),
    )
    
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='overdue_followups')
    referral = models.ForeignKey(Referral, on_delete=models.CASCADE, related_name='overdue_followups')
    follow_up_type = models.CharField(max_length=50, choices=FOLLOW_UP_TYPES)
    scheduled_date = models.DateTimeField()
    overdue_days = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='pending')  # pending, notified, resolved, escalated
    notification_sent = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['scheduled_date']
    
    def __str__(self):
        return f"{self.patient.full_name} - Overdue {self.overdue_days} days"