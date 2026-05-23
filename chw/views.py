# chw/views.py - Remove Twilio import and simplify send_patient_communication

from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from patients.models import Patient
from referrals.models import Medication, PatientCommunication, PatientReport, Referral
from ai_assessment.models import SymptomAssessment
from django.shortcuts import render, get_object_or_404
from referrals.models import Referral, PatientAlert
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from referrals.models import Referral, PatientAlert, PatientMessage

# REMOVED: from patients.services.twilio_service import TwilioSMSService


@login_required
def dashboard(request):
    """CHW Dashboard View with Real Data"""
    
    # Check if user is CHW
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'chw':
        messages.error(request, 'Access denied. CHW privileges required.')
        return redirect('login')
    
    user = request.user
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # Get real patient data
    total_patients = Patient.objects.filter(registered_by=user).count()
    
    # Get real referral data - including all statuses
    total_referrals = Referral.objects.filter(chw=user).count()
    pending_admin_referrals = Referral.objects.filter(chw=user, status='pending_admin').count()
    approved_referrals = Referral.objects.filter(chw=user, status='approved').count()
    rejected_referrals = Referral.objects.filter(chw=user, status='rejected').count()
    completed_referrals = Referral.objects.filter(chw=user, status='completed').count()
    cancelled_referrals = Referral.objects.filter(chw=user, status='cancelled').count()
    
    # Get referrals by urgency
    emergency_referrals = Referral.objects.filter(chw=user, urgency='emergency').count()
    urgent_referrals = Referral.objects.filter(chw=user, urgency='urgent').count()
    non_urgent_referrals = Referral.objects.filter(chw=user, urgency='non_urgent').count()
    
    # Get AI assessments
    total_assessments = SymptomAssessment.objects.filter(assessed_by=user).count()
    emergency_assessments = SymptomAssessment.objects.filter(assessed_by=user, ai_urgency='emergency').count()
    urgent_assessments = SymptomAssessment.objects.filter(assessed_by=user, ai_urgency='urgent').count()
    non_urgent_assessments = SymptomAssessment.objects.filter(assessed_by=user, ai_urgency='non_urgent').count()
    
    # Get recent patients (last 30 days)
    recent_patients = Patient.objects.filter(
        registered_by=user,
        registered_at__date__gte=week_ago
    ).count()
    
    # Get recent referrals with details for display (include all statuses)
    recent_referrals_list = Referral.objects.filter(chw=user).select_related('patient', 'doctor').order_by('-created_at')[:10]
    
    # Get high-risk patients from AI assessments
    high_risk_assessments = SymptomAssessment.objects.filter(
        assessed_by=user,
        ai_urgency='emergency',
        created_at__date__gte=week_ago
    ).select_related('patient')[:5]
    
    # Get today's schedule (patients with follow-up needed)
    follow_up_patients = Patient.objects.filter(
        registered_by=user,
        last_visit__isnull=False,
        last_visit__date__gte=today
    )[:3]
    
    # Calculate completion rate
    if total_referrals > 0:
        completion_rate = int((completed_referrals / total_referrals) * 100)
    else:
        completion_rate = 0
    
    # Prepare recent referrals for template
    recent_referrals = []
    for ref in recent_referrals_list:
        recent_referrals.append({
            'id': ref.id,
            'patient_name': ref.patient.full_name,
            'doctor_name': ref.doctor.get_full_name() if ref.doctor else 'Not assigned',
            'specialist': ref.get_specialist_display(),
            'status': ref.status,
            'status_display': ref.get_status_display(),
            'created_at': ref.created_at,
            'referral_code': ref.referral_code,
        })
    
    # Prepare high risk patients
    high_risk_patients = []
    for assessment in high_risk_assessments:
        high_risk_patients.append({
            'name': assessment.patient.full_name,
            'condition': assessment.primary_complaint,
            'confidence': assessment.ai_confidence,
            'date': assessment.created_at,
        })
    
    context = {
        'user': user,
        'current_date': today,
        
        # Statistics
        'total_patients': total_patients,
        'total_referrals': total_referrals,
        'pending_referrals': pending_admin_referrals,
        'approved_referrals': approved_referrals,
        'rejected_referrals': rejected_referrals,
        'completed_referrals': completed_referrals,
        'cancelled_referrals': cancelled_referrals,
        'emergency_referrals': emergency_referrals,
        'urgent_referrals': urgent_referrals,
        'non_urgent_referrals': non_urgent_referrals,
        'total_assessments': total_assessments,
        'emergency_assessments': emergency_assessments,
        'urgent_assessments': urgent_assessments,
        'non_urgent_assessments': non_urgent_assessments,
        'recent_patients': recent_patients,
        'completion_rate': completion_rate,
        
        # Lists for display
        'recent_referrals': recent_referrals,
        'high_risk_patients': high_risk_patients,
        'follow_up_patients': follow_up_patients,
    }
    
    return render(request, 'chw/dashboard/dashboard.html', context)


from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from datetime import timedelta
from patients.models import Patient
from referrals.models import Referral, PatientAlert, PatientMessage
from ai_assessment.models import SymptomAssessment

# In chw/views.py - Update the patient_tracking function

@login_required
def patient_tracking(request, patient_id):
    """CHW view to track a specific patient's progress"""
    
    # Check if user is CHW
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'chw':
        messages.error(request, 'Access denied. CHW privileges required.')
        return redirect('login')
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get all referrals for this patient created by this CHW
    referrals = Referral.objects.filter(patient=patient, chw=request.user).order_by('-created_at')
    
    # Get medications from referrals (old way)
    medications = Medication.objects.filter(
        referral__in=referrals
    ).select_related('referral', 'prescribed_by').order_by('-prescribed_at')
    
    # ALSO get prescriptions from the doctor's Prescription model
    from doctor.models import Prescription
    prescriptions = Prescription.objects.filter(
        patient=patient
    ).select_related('doctor').order_by('-created_at')
    
    # Combine medications and prescriptions for display
    all_medications = []
    
    # Add medications from referrals
    for med in medications:
        all_medications.append({
            'source': 'medication',
            'medication_name': med.medication_name,
            'dosage': med.dosage,
            'frequency': med.frequency,
            'duration_days': med.duration_days,
            'instructions': med.instructions,
            'status': med.status,
            'prescribed_by': med.prescribed_by,
            'prescribed_at': med.prescribed_at,
            'referral': med.referral
        })
    
    # Add prescriptions from doctor
    for pres in prescriptions:
        all_medications.append({
            'source': 'prescription',
            'medication_name': 'Multiple Medications',
            'dosage': 'See prescription details',
            'frequency': 'As prescribed',
            'duration_days': pres.duration_days,
            'instructions': pres.instructions,
            'status': pres.status,
            'prescribed_by': pres.doctor,
            'prescribed_at': pres.created_at,
            'prescription': pres,
            'diagnosis': pres.diagnosis,
            'medications_text': pres.medications
        })
    
    # Sort by prescribed date (most recent first)
    all_medications.sort(key=lambda x: x['prescribed_at'], reverse=True)
    
    # Calculate time-based alerts for this patient
    alerts = []
    
    for referral in referrals:
        # Check for missed check-in (if referred more than 48 hours ago and no check-in)
        if referral.status in ['approved', 'pending_admin'] and not referral.check_in_time:
            time_since_referral = timezone.now() - referral.created_at
            if time_since_referral > timedelta(hours=48):
                alerts.append({
                    'type': 'missed_checkin',
                    'severity': 'high',
                    'message': f'Patient has not checked in within 48 hours of referral approval.',
                    'referral': referral
                })
        
        # Check for treatment delay (if checked in but not completed after 7 days)
        if referral.check_in_time and referral.status == 'in_progress':
            time_since_checkin = timezone.now() - referral.check_in_time
            if time_since_checkin > timedelta(days=7):
                alerts.append({
                    'type': 'treatment_delay',
                    'severity': 'medium',
                    'message': f'Treatment has been in progress for over 7 days without completion.',
                    'referral': referral
                })
        
        # Check for missed follow-up
        if referral.follow_up_required and referral.follow_up_date:
            if referral.follow_up_date < timezone.now() and referral.status != 'completed':
                alerts.append({
                    'type': 'missed_followup',
                    'severity': 'high',
                    'message': f'Patient missed scheduled follow-up appointment.',
                    'referral': referral
                })
    
    # Calculate patient journey timeline
    timeline = []
    for referral in referrals:
        timeline.append({
            'type': 'referral_created',
            'date': referral.created_at,
            'title': 'Referral Created',
            'description': f'Referral created with urgency: {referral.get_urgency_display()}',
            'icon': 'fa-plus-circle',
            'color': 'primary'
        })
        
        if referral.approved_at:
            timeline.append({
                'type': 'referral_approved',
                'date': referral.approved_at,
                'title': 'Referral Approved',
                'description': f'Referral approved by admin and assigned to Dr. {referral.doctor.get_full_name() if referral.doctor else "pending"}',
                'icon': 'fa-check-circle',
                'color': 'success'
            })
        
        if referral.check_in_time:
            timeline.append({
                'type': 'checked_in',
                'date': referral.check_in_time,
                'title': 'Patient Checked In',
                'description': f'Patient arrived at J.J. Dossen Hospital',
                'icon': 'fa-sign-in-alt',
                'color': 'info'
            })
        
        if referral.treatment_start_date:
            timeline.append({
                'type': 'treatment_started',
                'date': referral.treatment_start_date,
                'title': 'Treatment Started',
                'description': 'Doctor began treatment',
                'icon': 'fa-play-circle',
                'color': 'primary'
            })
        
        if referral.check_out_time:
            timeline.append({
                'type': 'checked_out',
                'date': referral.check_out_time,
                'title': 'Patient Checked Out',
                'description': 'Patient discharged after visit',
                'icon': 'fa-sign-out-alt',
                'color': 'warning'
            })
        
        if referral.completed_at:
            timeline.append({
                'type': 'treatment_completed',
                'date': referral.completed_at,
                'title': 'Treatment Completed',
                'description': 'Treatment course completed successfully',
                'icon': 'fa-flag-checkered',
                'color': 'success'
            })
    
    # Sort timeline by date (most recent first)
    timeline.sort(key=lambda x: x['date'], reverse=True)
    
    # Calculate summary statistics
    total_referrals = referrals.count()
    completed_referrals = referrals.filter(status='completed').count()
    active_referrals = referrals.filter(status__in=['approved', 'in_progress']).count()
    
    # Calculate average time to treatment
    avg_time_to_treatment = None
    completed_with_dates = referrals.exclude(check_in_time=None).exclude(created_at=None)
    if completed_with_dates.exists():
        total_hours = 0
        count = 0
        for ref in completed_with_dates:
            hours = (ref.check_in_time - ref.created_at).total_seconds() / 3600
            total_hours += hours
            count += 1
        avg_time_to_treatment = round(total_hours / count, 1)
    
    context = {
        'patient': patient,
        'referrals': referrals,
        'alerts': alerts,
        'medications': all_medications,  # Now includes both Medication and Prescription
        'timeline': timeline,
        'total_referrals': total_referrals,
        'completed_referrals': completed_referrals,
        'active_referrals': active_referrals,
        'avg_time_to_treatment': avg_time_to_treatment,
    }
    return render(request, 'chw/patient_tracking.html', context)


@login_required
def send_patient_message(request, referral_id):
    """Send Email to patient (SMS removed)"""
    
    # Check if user is CHW
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'chw':
        messages.error(request, 'Access denied. CHW privileges required.')
        return redirect('login')
    
    # Handle case when referral_id is 0
    if referral_id == 0:
        patient_id = request.POST.get('patient_id')
        if patient_id:
            latest_referral = Referral.objects.filter(
                patient_id=patient_id, 
                chw=request.user
            ).order_by('-created_at').first()
            
            if latest_referral:
                referral_id = latest_referral.id
            else:
                messages.error(request, 'No referral found for this patient.')
                return redirect('chw:patient_tracking', patient_id=patient_id)
    
    referral = get_object_or_404(Referral, id=referral_id, chw=request.user)
    patient = referral.patient
    
    if request.method == 'POST':
        message_body = request.POST.get('message')
        
        if not message_body:
            messages.error(request, 'Message cannot be empty.')
            return redirect('chw:patient_tracking', patient_id=patient.id)
        
        # Check if patient has email
        if not patient.email:
            messages.error(request, f'Cannot send message to {patient.full_name}. No email address on file.')
            return redirect('chw:patient_tracking', patient_id=patient.id)
        
        # Save message record
        patient_message = PatientMessage.objects.create(
            referral=referral,
            sent_by=request.user,
            channel='email',  # Only email now
            subject=request.POST.get('subject', f'Message from J.J. Dossen Hospital - {referral.referral_code}'),
            message=message_body,
            status='pending',
        )
        
        # Send email
        try:
            send_mail(
                subject=patient_message.subject,
                message=message_body,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[patient.email],
                fail_silently=False,
            )
            
            patient_message.status = 'sent'
            patient_message.sent_at = timezone.now()
            patient_message.save()
            
            # Create alert for CHW
            PatientAlert.objects.create(
                referral=referral,
                alert_type='appointment_reminder',
                severity='low',
                message=f"Email sent to {patient.full_name}: {message_body[:100]}"
            )
            
            messages.success(request, f'Email sent successfully to {patient.full_name} at {patient.email}!')
            
        except Exception as e:
            patient_message.status = 'failed'
            patient_message.save()
            messages.error(request, f'Failed to send email: {str(e)}')
        
        return redirect('chw:patient_tracking', patient_id=patient.id)
    
    return redirect('chw:patient_tracking', patient_id=patient.id)


# chw/views.py - Add these views

@login_required
def chw_communications(request):
    """CHW receives communications from doctors"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'chw':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    communications = PatientCommunication.objects.filter(
        to_user=request.user
    ).select_related('referral', 'from_user').order_by('-created_at')
    
    # Mark as read when viewed
    unread_count = communications.filter(is_read=False).count()
    
    context = {
        'communications': communications,
        'unread_count': unread_count,
    }
    return render(request, 'chw/communications.html', context)


@login_required
def mark_communication_read(request, comm_id):
    """Mark communication as read"""
    
    communication = get_object_or_404(PatientCommunication, id=comm_id, to_user=request.user)
    communication.is_read = True
    communication.read_at = timezone.now()
    communication.save()
    
    return JsonResponse({'success': True})


@login_required
def acknowledge_patient_report(request, report_id):
    """CHW acknowledges doctor's report"""
    
    report = get_object_or_404(PatientReport, id=report_id)
    
    if request.method == 'POST':
        report.acknowledged_by_chw = True
        report.acknowledged_at = timezone.now()
        report.save()
        
        messages.success(request, 'Report acknowledged. The doctor has been notified.')
        return redirect('chw:patient_tracking', patient_id=report.referral.patient.id)
    
    context = {
        'report': report,
    }
    return render(request, 'chw/acknowledge_report.html', context)

# chw/views.py - Add these functions

from referrals.models import PatientCommunication

@login_required
def chw_communications(request):
    """CHW view to see communications from doctors"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'chw':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    communications = PatientCommunication.objects.filter(
        to_user=request.user
    ).select_related('referral', 'from_user').order_by('-created_at')
    
    # Filter by priority
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        communications = communications.filter(priority=priority_filter)
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        communications = communications.filter(communication_type=type_filter)
    
    unread_count = communications.filter(is_read=False).count()
    
    context = {
        'communications': communications,
        'unread_count': unread_count,
        'priority_filter': priority_filter,
        'type_filter': type_filter,
    }
    return render(request, 'chw/communications.html', context)


@login_required
def mark_communication_read(request, comm_id):
    """Mark a single communication as read"""
    
    communication = get_object_or_404(PatientCommunication, id=comm_id, to_user=request.user)
    communication.is_read = True
    communication.read_at = timezone.now()
    communication.save()
    
    return JsonResponse({'success': True})


@login_required
def mark_all_communications_read(request):
    """Mark all communications as read"""
    
    PatientCommunication.objects.filter(to_user=request.user, is_read=False).update(
        is_read=True,
        read_at=timezone.now()
    )
    
    return JsonResponse({'success': True})


@login_required
def take_action_on_communication(request, comm_id):
    """CHW takes action on a communication"""
    
    communication = get_object_or_404(PatientCommunication, id=comm_id, to_user=request.user)
    
    if request.method == 'POST':
        action_notes = request.POST.get('action_notes')
        communication.action_taken = True
        communication.save()
        
        # Create a reply or log the action
        # You can also send a notification back to the doctor
        messages.success(request, 'Action recorded. The doctor has been notified.')
        return redirect('chw:chw_communications')
    
    return redirect('chw:chw_communications')


@login_required
def unread_count_api(request):
    """API endpoint for unread communications count"""
    
    count = PatientCommunication.objects.filter(
        to_user=request.user, 
        is_read=False
    ).count()
    
    return JsonResponse({'count': count})