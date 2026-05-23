from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from datetime import datetime, timedelta
from django.db.models import Q, Count
from django.core.paginator import Paginator
from django.utils import timezone
from django.http import JsonResponse
from django.core.mail import send_mail
from django.conf import settings
from referrals.models import LostPatient, PatientCommunication, PatientReport, Referral, ReferralActivity, Medication, PatientAlert, PatientMessage
from patients.models import Patient
from ai_assessment.models import SymptomAssessment
from .models import Prescription
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q

from django.urls import reverse



# ========== HELPER FUNCTIONS ==========

def send_chw_notification(referral, message):
    """Send notification to the CHW about patient status"""
    
    # Create an alert in the system
    PatientAlert.objects.create(
        referral=referral,
        alert_type='appointment_reminder',
        severity='medium',
        message=message,
    )
    
    # Send email to CHW if they have email
    if referral.chw and referral.chw.email:
        try:
            send_mail(
                subject=f'Patient Update: {referral.patient.full_name}',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[referral.chw.email],
                fail_silently=True,
            )
        except:
            pass


def create_medication_reminders(referral, medication):
    """Create medication reminder alerts"""
    
    PatientAlert.objects.create(
        referral=referral,
        alert_type='medication_reminder',
        severity='low',
        message=f"Medication reminder: Take {medication.medication_name} ({medication.dosage}) - {medication.frequency} for {medication.duration_days} days.",
    )


def send_patient_communication(referral, channel, message):
    """Send SMS or Email to patient"""
    
    patient = referral.patient
    success = False
    
    if channel == 'email' and patient.email:
        try:
            send_mail(
                subject=f'Message from J.J. Dossen Hospital - {referral.referral_code}',
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[patient.email],
                fail_silently=False,
            )
            success = True
        except Exception as e:
            print(f"Email error: {e}")
            success = False
    
    elif channel == 'sms' and patient.phone_number:
        # For SMS, you'll need Twilio or another SMS service
        # This is a placeholder - configure your SMS provider
        try:
            # Example with Twilio (uncomment and configure)
            # client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            # client.messages.create(
            #     body=message,
            #     from_=settings.TWILIO_PHONE_NUMBER,
            #     to=patient.phone_number
            # )
            print(f"SMS to {patient.phone_number}: {message}")
            success = True
        except Exception as e:
            print(f"SMS error: {e}")
            success = False
    
    return success


# ========== MAIN DASHBOARD ==========

@login_required
def doctor_patient_tracking(request, patient_id):
    """Doctor view to track patient progress"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get only referrals assigned to this doctor
    referrals = Referral.objects.filter(patient=patient, doctor=request.user).order_by('-created_at')
    
    # Get medications prescribed by this doctor
    from .models import Prescription
    prescriptions = Prescription.objects.filter(patient=patient, doctor=request.user).order_by('-created_at')
    
    context = {
        'patient': patient,
        'referrals': referrals,
        'prescriptions': prescriptions,
    }
    return render(request, 'doctor/dashboard/patient_tracking.html', context)


@login_required
def dashboard(request):
    """Doctor Dashboard View with Real Data"""
    
    # Check if user is Doctor
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor privileges required.')
        return redirect('login')
    
    user = request.user
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    # Get doctor's specialization
    doctor_specialization = user.profile.full_specialization
    
    # ========== REFERRAL STATISTICS ==========
    total_referrals = Referral.objects.filter(doctor=user).count()
    pending_referrals = Referral.objects.filter(doctor=user, status='pending').count()
    accepted_referrals = Referral.objects.filter(doctor=user, status='accepted').count()
    in_progress_referrals = Referral.objects.filter(doctor=user, status='in_progress').count()
    completed_referrals = Referral.objects.filter(doctor=user, status='completed').count()
    
    emergency_referrals = Referral.objects.filter(doctor=user, urgency='emergency').count()
    urgent_referrals = Referral.objects.filter(doctor=user, urgency='urgent').count()
    recent_referrals_count = Referral.objects.filter(doctor=user, created_at__date__gte=week_ago).count()
    
    # ========== PATIENT STATISTICS ==========
    total_patients = Referral.objects.filter(doctor=user).values('patient').distinct().count()
    patients_seen = Referral.objects.filter(doctor=user, status='completed').values('patient').distinct().count()
    
    # ========== COMPLETION RATE ==========
    completion_rate = int((completed_referrals / total_referrals) * 100) if total_referrals > 0 else 0
    
    # ========== REFERRALS LISTS ==========
    pending_list = Referral.objects.filter(doctor=user, status='pending').select_related('patient', 'chw').order_by('-created_at')[:10]
    in_progress_list = Referral.objects.filter(doctor=user, status='in_progress').select_related('patient', 'chw').order_by('-created_at')[:10]
    completed_list = Referral.objects.filter(doctor=user, status='completed').select_related('patient', 'chw').order_by('-completed_at')[:5]
    emergency_list = Referral.objects.filter(doctor=user, urgency='emergency').select_related('patient', 'chw').order_by('-created_at')[:5]
    
    context = {
        'user': user,
        'doctor_specialization': doctor_specialization,
        'current_date': today,
        'total_referrals': total_referrals,
        'pending_referrals': pending_referrals,
        'accepted_referrals': accepted_referrals,
        'in_progress_referrals': in_progress_referrals,
        'completed_referrals': completed_referrals,
        'emergency_referrals': emergency_referrals,
        'urgent_referrals': urgent_referrals,
        'recent_referrals_count': recent_referrals_count,
        'total_patients': total_patients,
        'patients_seen': patients_seen,
        'completion_rate': completion_rate,
        'pending_list': pending_list,
        'in_progress_list': in_progress_list,
        'completed_list': completed_list,
        'emergency_list': emergency_list,
    }
    
    return render(request, 'doctor/dashboard/dashboard.html', context)


# ========== PATIENT TRACKING VIEWS ==========

@login_required
def patient_check_in(request, referral_id):
    """Mark patient as checked in"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    referral = get_object_or_404(Referral, id=referral_id, doctor=request.user)
    
    if request.method == 'POST':
        referral.check_in_time = timezone.now()
        referral.status = 'in_progress'
        referral.treatment_start_date = timezone.now()
        referral.save()
        
        # Create activity log
        ReferralActivity.objects.create(
            referral=referral,
            activity_type='started',
            performed_by=request.user,
            description=f"Patient checked in at {timezone.now().strftime('%H:%M')}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send notification to CHW
        send_chw_notification(referral, f"Patient {referral.patient.full_name} has checked in for treatment.")
        
        messages.success(request, f'Patient {referral.patient.full_name} checked in successfully!')
        return redirect('doctor:view_referral', referral_id=referral.id)
    
    return redirect('doctor:view_referral', referral_id=referral.id)


@login_required
def patient_check_out(request, referral_id):
    """Mark patient as checked out"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    referral = get_object_or_404(Referral, id=referral_id, doctor=request.user)
    
    if request.method == 'POST':
        referral.check_out_time = timezone.now()
        referral.save()
        
        ReferralActivity.objects.create(
            referral=referral,
            activity_type='completed',
            performed_by=request.user,
            description=f"Patient checked out at {timezone.now().strftime('%H:%M')}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send notification to CHW
        send_chw_notification(referral, f"Patient {referral.patient.full_name} has completed their visit and checked out.")
        
        messages.success(request, f'Patient {referral.patient.full_name} checked out successfully!')
        return redirect('doctor:view_referral', referral_id=referral.id)
    
    return redirect('doctor:view_referral', referral_id=referral.id)


# In doctor/views.py - Update the prescribe_medication function

@login_required
def prescribe_medication(request, referral_id):
    """Prescribe medication to a patient"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    referral = get_object_or_404(Referral, id=referral_id, doctor=request.user)
    
    if request.method == 'POST':
        # Create Medication record (for referrals app)
        medication = Medication.objects.create(
            referral=referral,
            prescribed_by=request.user,
            medication_name=request.POST.get('medication_name'),
            dosage=request.POST.get('dosage'),
            frequency=request.POST.get('frequency'),
            duration_days=int(request.POST.get('duration_days', 7)),
            instructions=request.POST.get('instructions', ''),
        )
        
        # ALSO create Prescription record (for doctor app)
        from .models import Prescription
        prescription = Prescription.objects.create(
            patient=referral.patient,
            doctor=request.user,
            referral=referral,
            diagnosis=request.POST.get('diagnosis', ''),
            medications=f"{request.POST.get('medication_name')} - {request.POST.get('dosage')}, {request.POST.get('frequency')} for {request.POST.get('duration_days', 7)} days",
            instructions=request.POST.get('instructions', ''),
            duration_days=int(request.POST.get('duration_days', 7)),
            status='active'
        )
        
        ReferralActivity.objects.create(
            referral=referral,
            activity_type='started',
            performed_by=request.user,
            description=f"Prescribed {medication.medication_name} ({medication.dosage}) - {medication.frequency}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Create medication reminder alerts
        create_medication_reminders(referral, medication)
        
        messages.success(request, f'Medication prescribed successfully!')
        return redirect('doctor:view_referral', referral_id=referral.id)
    
    return redirect('doctor:view_referral', referral_id=referral.id)


@login_required
def complete_treatment(request, referral_id):
    """Mark treatment as completed"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    referral = get_object_or_404(Referral, id=referral_id, doctor=request.user)
    
    if request.method == 'POST':
        referral.status = 'completed'
        referral.completed_at = timezone.now()
        referral.treatment_end_date = timezone.now()
        referral.save()
        
        # Update all active medications to completed
        Medication.objects.filter(referral=referral, status='active').update(status='completed', completed_at=timezone.now())
        
        ReferralActivity.objects.create(
            referral=referral,
            activity_type='completed',
            performed_by=request.user,
            description="Treatment completed",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send notification to CHW
        send_chw_notification(referral, f"Treatment for {referral.patient.full_name} has been marked as COMPLETED.")
        
        messages.success(request, f'Treatment for {referral.patient.full_name} marked as completed!')
        return redirect('doctor:view_referral', referral_id=referral.id)
    
    return redirect('doctor:view_referral', referral_id=referral.id)


# ========== PATIENT VIEWS ==========

@login_required
def my_patients(request):
    """Show all patients referred to this doctor"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    # Get unique patients from referrals
    patient_ids = Referral.objects.filter(doctor=request.user).values_list('patient_id', flat=True).distinct()
    patients = Patient.objects.filter(id__in=patient_ids).order_by('-registered_at')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        patients = patients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(patient_id__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(patients, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get referral counts for each patient
    for patient in page_obj:
        patient.referral_count = Referral.objects.filter(doctor=request.user, patient=patient).count()
        patient.last_referral = Referral.objects.filter(doctor=request.user, patient=patient).order_by('-created_at').first()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'total_patients': patients.count(),
    }
    return render(request, 'doctor/dashboard/my_patients.html', context)


@login_required
def patient_history(request, patient_id):
    """View complete medical history of a patient"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get all referrals for this patient with this doctor
    referrals = Referral.objects.filter(patient=patient, doctor=request.user).order_by('-created_at')
    
    # Get all AI assessments for this patient
    assessments = SymptomAssessment.objects.filter(patient=patient).order_by('-created_at')
    
    # Get all prescriptions for this patient
    prescriptions = Prescription.objects.filter(patient=patient, doctor=request.user).order_by('-created_at')
    
    context = {
        'patient': patient,
        'referrals': referrals,
        'assessments': assessments,
        'prescriptions': prescriptions,
    }
    return render(request, 'doctor/dashboard/patient_history.html', context)


# ========== REFERRAL VIEWS ==========

@login_required
def pending_referrals(request):
    """Show all pending referrals for this doctor"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor privileges required.')
        return redirect('login')
    
    referrals = Referral.objects.filter(
        doctor=request.user, 
        status='pending'
    ).select_related('patient', 'chw').order_by('-created_at')
    
    # Search
    search = request.GET.get('search', '')
    if search:
        referrals = referrals.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(referral_code__icontains=search)
        )
    
    paginator = Paginator(referrals, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'title': 'Pending Referrals',
        'status_filter': 'pending',
    }
    return render(request, 'doctor/dashboard/referrals_list.html', context)


@login_required
def completed_referrals(request):
    """Show all completed referrals for this doctor"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor privileges required.')
        return redirect('login')
    
    referrals = Referral.objects.filter(
        doctor=request.user, 
        status='completed'
    ).select_related('patient', 'chw').order_by('-completed_at')
    
    search = request.GET.get('search', '')
    if search:
        referrals = referrals.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(referral_code__icontains=search)
        )
    
    paginator = Paginator(referrals, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'title': 'Completed Referrals',
        'status_filter': 'completed',
    }
    return render(request, 'doctor/dashboard/referrals_list.html', context)


@login_required
def all_referrals(request):
    """Show all referrals for this doctor"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor privileges required.')
        return redirect('login')
    
    referrals = Referral.objects.filter(doctor=request.user).select_related('patient', 'chw').order_by('-created_at')
    
    # Filters
    status_filter = request.GET.get('status', '')
    urgency_filter = request.GET.get('urgency', '')
    search = request.GET.get('search', '')
    
    if status_filter:
        referrals = referrals.filter(status=status_filter)
    if urgency_filter:
        referrals = referrals.filter(urgency=urgency_filter)
    if search:
        referrals = referrals.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(referral_code__icontains=search)
        )
    
    paginator = Paginator(referrals, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'urgency_filter': urgency_filter,
        'title': 'All Referrals',
    }
    return render(request, 'doctor/dashboard/referrals_list.html', context)


@login_required
def view_referral(request, referral_id):
    """Doctor view for viewing referral details"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied. Doctor privileges required.')
        return redirect('login')
    
    referral = get_object_or_404(Referral, id=referral_id, doctor=request.user)
    
    context = {
        'referral': referral,
        'user': request.user,
    }
    return render(request, 'doctor/dashboard/view_referral.html', context)


# ========== PRESCRIPTION VIEWS ==========

@login_required
def write_prescription(request, patient_id=None):
    """Write a new prescription for a patient"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    patient = None
    prescription = None
    
    if patient_id:
        patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        patient = get_object_or_404(Patient, id=patient_id)
        
        prescription = Prescription.objects.create(
            patient=patient,
            doctor=request.user,
            diagnosis=request.POST.get('diagnosis'),
            medications=request.POST.get('medications'),
            instructions=request.POST.get('instructions', ''),
            duration_days=int(request.POST.get('duration_days', 7)),
            blood_pressure=request.POST.get('blood_pressure', ''),
            temperature=request.POST.get('temperature') or None,
            pulse_rate=request.POST.get('pulse_rate') or None,
            weight=request.POST.get('weight') or None,
            follow_up_required=request.POST.get('follow_up_required') == 'on',
        )
        
        messages.success(request, f'Prescription written for {patient.full_name}')
        
        # Return with prescription data for printing
        recent_patients = Patient.objects.filter(
            id__in=Referral.objects.filter(doctor=request.user).values_list('patient_id', flat=True)
        ).distinct()[:10]
        
        context = {
            'patient': patient,
            'recent_patients': recent_patients,
            'prescription': prescription,
        }
        return render(request, 'doctor/dashboard/write_prescription.html', context)
    
    # Get recent patients for quick selection
    recent_patients = Patient.objects.filter(
        id__in=Referral.objects.filter(doctor=request.user).values_list('patient_id', flat=True)
    ).distinct()[:10]
    
    context = {
        'patient': patient,
        'recent_patients': recent_patients,
        'prescription': None,
    }
    return render(request, 'doctor/dashboard/write_prescription.html', context)


@login_required
def prescription_history(request):
    """Show all prescriptions written by this doctor"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    prescriptions = Prescription.objects.filter(doctor=request.user).select_related('patient').order_by('-created_at')
    
    search = request.GET.get('search', '')
    if search:
        prescriptions = prescriptions.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(diagnosis__icontains=search)
        )
    
    paginator = Paginator(prescriptions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'total_prescriptions': prescriptions.count(),
    }
    return render(request, 'doctor/dashboard/prescription_history.html', context)


# ========== SCHEDULE VIEWS ==========

@login_required
def appointments_today(request):
    """Show today's appointments"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    today = timezone.now().date()
    
    # Get referrals scheduled for today
    appointments = Referral.objects.filter(
        doctor=request.user,
        scheduled_date__date=today
    ).select_related('patient').order_by('scheduled_date')
    
    context = {
        'appointments': appointments,
        'today': today,
    }
    return render(request, 'doctor/dashboard/appointments.html', context)


@login_required
def schedule(request):
    """Show doctor's schedule/calendar"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    # Get upcoming appointments
    upcoming = Referral.objects.filter(
        doctor=request.user,
        scheduled_date__gte=timezone.now(),
        status__in=['accepted', 'in_progress']
    ).select_related('patient').order_by('scheduled_date')[:20]
    
    context = {
        'upcoming': upcoming,
    }
    return render(request, 'doctor/dashboard/schedule.html', context)


# ========== API VIEWS ==========

@login_required
def pending_count_api(request):
    """API endpoint to get pending referrals count for doctor"""
    if hasattr(request.user, 'profile') and request.user.profile.user_type == 'doctor':
        count = Referral.objects.filter(doctor=request.user, status='pending').count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})


@login_required
def prescription_list(request):
    """List all prescriptions for the logged-in doctor"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    # Get all prescriptions by this doctor
    prescriptions = Prescription.objects.filter(doctor=request.user).select_related('patient').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        prescriptions = prescriptions.filter(status=status_filter)
    
    # Search by patient name
    search = request.GET.get('search', '')
    if search:
        prescriptions = prescriptions.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__patient_id__icontains=search) |
            Q(diagnosis__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(prescriptions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Counts for tabs
    active_count = prescriptions.filter(status='active').count()
    completed_count = prescriptions.filter(status='completed').count()
    cancelled_count = prescriptions.filter(status='cancelled').count()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'active_count': active_count,
        'completed_count': completed_count,
        'cancelled_count': cancelled_count,
        'total_count': prescriptions.count(),
    }
    return render(request, 'doctor/dashboard/prescription_list.html', context)


@login_required
def prescription_detail(request, prescription_id):
    """View a single prescription"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    prescription = get_object_or_404(Prescription, id=prescription_id, doctor=request.user)
    
    context = {
        'prescription': prescription,
    }
    return render(request, 'doctor/dashboard/prescription_detail.html', context)


@login_required
def prescription_edit(request, prescription_id):
    """Edit a prescription"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    prescription = get_object_or_404(Prescription, id=prescription_id, doctor=request.user)
    
    if request.method == 'POST':
        prescription.diagnosis = request.POST.get('diagnosis')
        prescription.medications = request.POST.get('medications')
        prescription.instructions = request.POST.get('instructions', '')
        prescription.duration_days = int(request.POST.get('duration_days', 7))
        prescription.blood_pressure = request.POST.get('blood_pressure', '')
        prescription.temperature = request.POST.get('temperature') or None
        prescription.pulse_rate = request.POST.get('pulse_rate') or None
        prescription.weight = request.POST.get('weight') or None
        prescription.follow_up_required = request.POST.get('follow_up_required') == 'on'
        prescription.save()
        
        messages.success(request, f'Prescription for {prescription.patient.full_name} updated successfully!')
        return redirect('doctor:prescription_detail', prescription_id=prescription.id)
    
    context = {
        'prescription': prescription,
    }
    return render(request, 'doctor/dashboard/prescription_edit.html', context)


@login_required
def prescription_delete(request, prescription_id):
    """Delete a prescription"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    prescription = get_object_or_404(Prescription, id=prescription_id, doctor=request.user)
    
    if request.method == 'POST':
        patient_name = prescription.patient.full_name
        prescription.delete()
        messages.success(request, f'Prescription for {patient_name} has been deleted.')
        return redirect('doctor:prescription_list')
    
    context = {
        'prescription': prescription,
    }
    return render(request, 'doctor/dashboard/prescription_delete.html', context)


@login_required
def prescription_clear(request, prescription_id):
    """Mark prescription as completed (move to history)"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    prescription = get_object_or_404(Prescription, id=prescription_id, doctor=request.user)
    
    if request.method == 'POST':
        prescription.status = 'completed'
        prescription.completed_at = timezone.now()
        prescription.save()
        messages.success(request, f'Prescription for {prescription.patient.full_name} has been cleared/completed.')
        return redirect('doctor:prescription_list')
    
    return redirect('doctor:prescription_detail', prescription_id=prescription.id)


@login_required
def prescription_print(request, prescription_id):
    """Print/download prescription as PDF"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    prescription = get_object_or_404(Prescription, id=prescription_id, doctor=request.user)
    
    context = {
        'prescription': prescription,
        'user': request.user,
    }
    return render(request, 'doctor/dashboard/prescription_print.html', context)


@login_required
def active_prescriptions_count_api(request):
    """API endpoint to get active prescriptions count for doctor"""
    if hasattr(request.user, 'profile') and request.user.profile.user_type == 'doctor':
        count = Prescription.objects.filter(doctor=request.user, status='active').count()
        return JsonResponse({'count': count})
    return JsonResponse({'count': 0})


# doctor/views.py - Add these new views

@login_required
def report_missed_appointment(request, referral_id):
    """Doctor reports a missed appointment to CHW"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    referral = get_object_or_404(Referral, id=referral_id, doctor=request.user)
    
    if request.method == 'POST':
        # Create patient report
        report = PatientReport.objects.create(
            referral=referral,
            doctor=request.user,
            report_type='missed_appointment',
            title=request.POST.get('title', 'Missed Appointment'),
            description=request.POST.get('description'),
            recommendations=request.POST.get('recommendations', ''),
            action_required=True
        )
        
        # Create communication
        communication = PatientCommunication.objects.create(
            referral=referral,
            from_user=request.user,
            to_user=referral.chw,
            communication_type='missed_appointment',
            priority='high',
            subject=f'Missed Appointment: {referral.patient.full_name}',
            message=f"Patient {referral.patient.full_name} missed their scheduled appointment on {referral.scheduled_date.strftime('%Y-%m-%d') if referral.scheduled_date else 'today'}. Please contact the patient to reschedule.\n\nDetails: {request.POST.get('description')}",
            requires_action=True
        )
        
        # Check if this patient should be marked as lost
        missed_count = PatientReport.objects.filter(
            referral=referral,
            report_type='missed_appointment',
            created_at__gte=timezone.now() - timedelta(days=30)
        ).count()
        
        if missed_count >= 2:
            # Mark as lost patient
            LostPatient.objects.create(
                patient=referral.patient,
                referral=referral,
                reason='no_contact',
                notes=f"Patient missed {missed_count} appointments in the last 30 days",
                chw_notified=True
            )
            messages.warning(request, f'Patient has been marked as LOST due to multiple missed appointments.')
        
        messages.success(request, f'Missed appointment reported to CHW. They will contact the patient.')
        return redirect('doctor:view_referral', referral_id=referral.id)
    
    context = {
        'referral': referral,
    }
    return render(request, 'doctor/dashboard/report_missed_appointment.html', context)


# doctor/views.py - Update the send_patient_update_to_chw function

@login_required
def send_patient_update_to_chw(request, referral_id):
    """Doctor sends treatment update to CHW"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    referral = get_object_or_404(Referral, id=referral_id, doctor=request.user)
    
    if request.method == 'POST':
        communication = PatientCommunication.objects.create(
            referral=referral,
            from_user=request.user,
            to_user=referral.chw,
            communication_type=request.POST.get('communication_type', 'treatment_update'),
            priority=request.POST.get('priority', 'medium'),
            subject=request.POST.get('subject'),
            message=request.POST.get('message'),
            requires_action=request.POST.get('requires_action') == 'on'
        )
        
        # Send email notification to CHW
        if referral.chw.email:
            send_mail(
                subject=f'Patient Update: {referral.patient.full_name} - {communication.subject}',
                message=f"Doctor: {request.user.get_full_name()}\n\n{communication.message}\n\nPlease log in to your dashboard for more details.\n\nLogin: http://127.0.0.1:8000/chw/dashboard/",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[referral.chw.email],
                fail_silently=True
            )
        
        messages.success(request, f'Update sent to CHW {referral.chw.get_full_name()}')
        return redirect('doctor:view_referral', referral_id=referral.id)
    
    context = {
        'referral': referral,
    }
    return render(request, 'doctor/dashboard/send_chw_update.html', context)


@login_required
def doctor_communications(request):
    """Doctor's communication history with CHWs"""
    
    if not hasattr(request.user, 'profile') or request.user.profile.user_type != 'doctor':
        messages.error(request, 'Access denied.')
        return redirect('login')
    
    communications = PatientCommunication.objects.filter(
        from_user=request.user
    ).select_related('referral', 'to_user').order_by('-created_at')
    
    # Filter by type
    comm_type = request.GET.get('type', '')
    if comm_type:
        communications = communications.filter(communication_type=comm_type)
    
    paginator = Paginator(communications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'comm_type': comm_type,
    }
    return render(request, 'doctor/dashboard/communications.html', context)
