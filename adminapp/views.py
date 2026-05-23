from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.core.mail import send_mail
from django.conf import settings
from referrals.notification_utils import send_approval_notifications, send_rejection_notifications
from patients.models import Patient
from referrals.models import LostPatient, OverdueFollowUp, PatientCommunication, Referral, ReferralActivity
from ai_assessment.models import SymptomAssessment
from user_management.models import UserProfile


def home(request):
    """Home page view"""
    return render(request, 'adminapp/home/home.html')


def user_login(request):
    """Unified login page for all user types (Admin, Doctor, CHW)"""
    
    # If user is already logged in, redirect to their appropriate dashboard
    if request.user.is_authenticated:
        if request.user.is_staff or request.user.is_superuser:
            return redirect('adminapp:admin_dashboard')
        elif hasattr(request.user, 'profile'):
            if request.user.profile.user_type == 'doctor':
                return redirect('doctor:dashboard')
            elif request.user.profile.user_type == 'chw':
                return redirect('chw:dashboard')
        return redirect('home')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember_me')
        
        # Authenticate user
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            auth_login(request, user)
            
            # Set session expiry based on remember me
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)  # 2 weeks
            
            # Redirect based on user type
            if user.is_staff or user.is_superuser:
                messages.success(request, f'Welcome Admin, {user.get_full_name() or user.username}!')
                return redirect('adminapp:admin_dashboard')
            elif hasattr(user, 'profile'):
                if user.profile.user_type == 'doctor':
                    messages.success(request, f'Welcome Dr. {user.get_full_name() or user.username}!')
                    return redirect('doctor:dashboard')
                elif user.profile.user_type == 'chw':
                    messages.success(request, f'Welcome {user.get_full_name() or user.username}!')
                    return redirect('chw:dashboard')
            else:
                messages.error(request, 'User profile not found. Please contact administrator.')
                return redirect('user_login')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'adminapp/auth/login.html')


def admin_logout(request):
    """Admin logout view"""
    auth_logout(request)
    messages.info(request, 'You have been successfully logged out.')
    return redirect('login')  # This matches the URL name in adminapp/urls.py


@login_required
@staff_member_required
def admin_dashboard(request):
    """Admin dashboard view with real data"""
    
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # ========== PATIENT STATISTICS ==========
    total_patients = Patient.objects.count()
    new_patients_week = Patient.objects.filter(registered_at__date__gte=week_ago).count()
    new_patients_month = Patient.objects.filter(registered_at__date__gte=month_ago).count()
    
    # ========== REFERRAL STATISTICS ==========
    total_referrals = Referral.objects.count()
    active_referrals = Referral.objects.filter(status__in=['pending_admin', 'approved', 'accepted', 'in_progress']).count()
    completed_referrals = Referral.objects.filter(status='completed').count()
    lost_patients = Referral.objects.filter(status='cancelled').count()
    pending_admin_referrals = Referral.objects.filter(status='pending_admin').count()
    
    # Referrals by urgency
    emergency_referrals = Referral.objects.filter(urgency='emergency').count()
    urgent_referrals = Referral.objects.filter(urgency='urgent').count()
    non_urgent_referrals = Referral.objects.filter(urgency='non_urgent').count()
    
    # New referrals today
    today_referrals = Referral.objects.filter(created_at__date=today).count()
    
    # ========== USER STATISTICS ==========
    total_users = User.objects.filter(is_superuser=False).count()
    total_doctors = UserProfile.objects.filter(user_type='doctor', status='active').count()
    total_chws = UserProfile.objects.filter(user_type='chw', status='active').count()
    active_users = UserProfile.objects.filter(status='active').count()
    pending_users = UserProfile.objects.filter(status='pending').count()
    
    # ========== COMMUNICATIONS STATISTICS ==========
    from referrals.models import PatientCommunication
    total_communications = PatientCommunication.objects.count()
    unread_communications = PatientCommunication.objects.filter(is_read=False).count()
    action_required_comms = PatientCommunication.objects.filter(requires_action=True, action_taken=False).count()
    high_priority_comms = PatientCommunication.objects.filter(priority='high', is_read=False).count()
    
    # Recent communications (last 5)
    recent_comms = PatientCommunication.objects.select_related(
        'referral', 'referral__patient', 'from_user', 'to_user'
    ).order_by('-created_at')[:5]
    
    communications_list = []
    for comm in recent_comms:
        communications_list.append({
            'id': comm.id,
            'doctor': comm.from_user.get_full_name() or comm.from_user.username,
            'chw': comm.to_user.get_full_name() or comm.to_user.username,
            'patient': comm.referral.patient.full_name,
            'subject': comm.subject,
            'priority': comm.priority,
            'requires_action': comm.requires_action and not comm.action_taken,
            'created_at': comm.created_at,
            'is_read': comm.is_read,
        })
    
    # ========== LOST PATIENTS ==========
    from referrals.models import LostPatient
    lost_patients_list = LostPatient.objects.filter(recovered=False).select_related('patient', 'referral')[:5]
    total_lost_count = LostPatient.objects.filter(recovered=False).count()
    
    lost_patients_data = []
    for lost in lost_patients_list:
        lost_patients_data.append({
            'id': lost.id,
            'patient_name': lost.patient.full_name,
            'patient_id': lost.patient.patient_id,
            'reason': lost.get_reason_display(),
            'lost_date': lost.lost_date,
            'referral_code': lost.referral.referral_code,
        })
    
    # ========== OVERDUE FOLLOW-UPS ==========
    from referrals.models import OverdueFollowUp
    overdue_followups = OverdueFollowUp.objects.filter(
        scheduled_date__lt=timezone.now(),
        status__in=['pending', 'notified']
    ).select_related('patient', 'referral').order_by('scheduled_date')[:5]
    
    total_overdue = OverdueFollowUp.objects.filter(
        scheduled_date__lt=timezone.now(),
        status__in=['pending', 'notified']
    ).count()
    
    overdue_data = []
    for overdue in overdue_followups:
        days_overdue = (timezone.now() - overdue.scheduled_date).days
        overdue_data.append({
            'id': overdue.id,
            'patient_name': overdue.patient.full_name,
            'patient_id': overdue.patient.patient_id,
            'follow_up_type': overdue.get_follow_up_type_display(),
            'scheduled_date': overdue.scheduled_date,
            'overdue_days': days_overdue,
            'status': overdue.status,
        })
    
    # ========== RECENT ACTIVITY ==========
    recent_referrals = Referral.objects.select_related('patient', 'chw', 'doctor').order_by('-created_at')[:5]
    
    activities = []
    for ref in recent_referrals:
        activities.append({
            'type': 'referral',
            'description': f'Patient {ref.patient.full_name} referred to {ref.get_specialist_display()}',
            'time': ref.created_at,
            'user': ref.chw.get_full_name() if ref.chw else 'System',
            'status': ref.get_status_display(),
        })
    
    # ========== TOP PERFORMING CHWs ==========
    top_chws = User.objects.filter(
        profile__user_type='chw', profile__status='active'
    ).annotate(
        referral_count=Count('referrals_made')
    ).order_by('-referral_count')[:5]
    
    top_chws_data = []
    for chw in top_chws:
        top_chws_data.append({
            'name': chw.get_full_name() or chw.username,
            'referral_count': chw.referral_count,
        })
    
    # ========== DAILY PATIENT TRENDS (Last 30 days) ==========
    daily_data = []
    for i in range(29, -1, -1):
        date = today - timedelta(days=i)
        count = Patient.objects.filter(registered_at__date=date).count()
        daily_data.append({
            'date': date,
            'day': date.strftime('%d'),
            'month': date.strftime('%b'),
            'day_name': date.strftime('%a'),
            'count': count
        })
    
    daily_labels = [f"{d['day']} {d['month']}" for d in daily_data]
    daily_counts = [d['count'] for d in daily_data]
    
    peak_day_count = max(daily_counts) if daily_counts else 0
    peak_day_index = daily_counts.index(peak_day_count) if daily_counts else -1
    peak_day = daily_labels[peak_day_index] if peak_day_index >= 0 else 'N/A'
    avg_daily = round(sum(daily_counts) / len(daily_counts), 1) if daily_counts else 0
    
    context = {
        'user': request.user,
        
        # Patient Stats
        'total_patients': total_patients,
        'new_patients_week': new_patients_week,
        'new_patients_month': new_patients_month,
        
        # Referral Stats
        'total_referrals': total_referrals,
        'active_referrals': active_referrals,
        'completed_referrals': completed_referrals,
        'lost_patients': lost_patients,
        'pending_admin_referrals': pending_admin_referrals,
        'emergency_referrals': emergency_referrals,
        'urgent_referrals': urgent_referrals,
        'non_urgent_referrals': non_urgent_referrals,
        'today_referrals': today_referrals,
        
        # User Stats
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_chws': total_chws,
        'active_users': active_users,
        'pending_users': pending_users,
        
        # Communication Stats
        'total_communications': total_communications,
        'unread_communications': unread_communications,
        'action_required_comms': action_required_comms,
        'high_priority_comms': high_priority_comms,
        'recent_communications': communications_list,
        
        # Lost Patients
        'lost_patients_list': lost_patients_data,
        'total_lost_count': total_lost_count,
        
        # Overdue Follow-ups
        'overdue_followups': overdue_data,
        'total_overdue': total_overdue,
        
        # Recent Activity
        'recent_activities': activities,
        
        # Top CHWs
        'top_chws': top_chws_data,
        
        # Daily data for chart
        'daily_labels': daily_labels,
        'daily_counts': daily_counts,
        'peak_day_count': peak_day_count,
        'peak_day': peak_day,
        'avg_daily': avg_daily,
    }
    
    return render(request, 'adminapp/dashboard/dashboard.html', context)


@login_required
@staff_member_required
def admin_all_referrals(request):
    """Admin view to see all referrals with approve/reject actions"""
    
    # Get all referrals
    referrals = Referral.objects.all().select_related('patient', 'chw', 'doctor').order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        referrals = referrals.filter(status=status_filter)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        referrals = referrals.filter(
            Q(referral_code__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__patient_id__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(referrals, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Counts for tabs
    pending_count = Referral.objects.filter(status='pending_admin').count()
    approved_count = Referral.objects.filter(status='approved').count()
    rejected_count = Referral.objects.filter(status='rejected').count()
    active_count = Referral.objects.filter(status__in=['accepted', 'in_progress']).count()
    completed_count = Referral.objects.filter(status='completed').count()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'pending_count': pending_count,
        'approved_count': approved_count,
        'rejected_count': rejected_count,
        'active_count': active_count,
        'completed_count': completed_count,
    }
    return render(request, 'adminapp/referrals/all_referrals.html', context)


@login_required
@staff_member_required
def admin_review_referral(request, referral_id):
    """Admin view to review a single referral before decision"""
    
    referral = get_object_or_404(Referral, id=referral_id)
    
    # Get ALL doctors registered in the system (regardless of specialization)
    from django.contrib.auth.models import User
    from user_management.models import UserProfile
    
    all_doctors = User.objects.filter(
        profile__user_type='doctor',
        profile__status='active',
        is_active=True
    ).select_related('profile').order_by('profile__specialization', 'first_name')
    
    context = {
        'referral': referral,
        'all_doctors': all_doctors,
    }
    return render(request, 'adminapp/referrals/review_referral.html', context)


@login_required
@staff_member_required
def admin_approve_referral(request, referral_id):
    """Admin approves a referral and assigns a doctor"""
    
    referral = get_object_or_404(Referral, id=referral_id)
    
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        
        if not doctor_id:
            messages.error(request, 'Please select a doctor to assign to this referral.')
            return redirect('adminapp:admin_review_referral', referral_id=referral.id)
        
        referral.doctor_id = doctor_id
        referral.status = 'approved'
        referral.approved_by = request.user
        referral.approved_at = timezone.now()
        referral.save()
        
        # Log activity
        ReferralActivity.objects.create(
            referral=referral,
            activity_type='approved',
            performed_by=request.user,
            description=f"Referral approved by Admin {request.user.username} and assigned to Dr. {referral.doctor.get_full_name()}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send notifications (email + dashboard) to CHW and Doctor
        send_approval_notifications(referral)
        
        messages.success(request, f'Referral { referral.referral_code } has been approved. Notifications sent to CHW and Doctor.')
        return redirect('adminapp:admin_all_referrals')
    
    return redirect('adminapp:admin_review_referral', referral_id=referral.id)


@login_required
@staff_member_required
def admin_reject_referral(request, referral_id):
    """Admin rejects a referral with reason"""
    
    referral = get_object_or_404(Referral, id=referral_id)
    
    if request.method == 'POST':
        rejection_reason = request.POST.get('rejection_reason', '').strip()
        
        if not rejection_reason:
            messages.error(request, 'Please provide a reason for rejection.')
            return redirect('adminapp:admin_review_referral', referral_id=referral.id)
        
        referral.status = 'rejected'
        referral.rejection_reason = rejection_reason
        referral.rejected_by = request.user
        referral.rejected_at = timezone.now()
        referral.save()
        
        # Log activity
        ReferralActivity.objects.create(
            referral=referral,
            activity_type='rejected',
            performed_by=request.user,
            description=f"Referral rejected by Admin {request.user.username}. Reason: {rejection_reason}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        # Send notifications (email + dashboard) to CHW only
        send_rejection_notifications(referral, rejection_reason)
        
        messages.success(request, f'Referral {referral.referral_code} has been rejected. CHW has been notified.')
        return redirect('adminapp:admin_all_referrals')
    
    return redirect('adminapp:admin_review_referral', referral_id=referral.id)


def send_doctor_notification_email(referral):
    """Send email notification to doctor about approved referral"""
    
    subject = f'New Referral Assigned - {referral.referral_code}'
    
    message = f"""
    Dear Dr. {referral.doctor.get_full_name()},
    
    A new referral has been approved and assigned to you.
    
    Referral Details:
    ---------------
    Referral Code: {referral.referral_code}
    Patient Name: {referral.patient.full_name}
    Patient ID: {referral.patient.patient_id}
    Urgency: {referral.get_urgency_display()}
    Specialist: {referral.get_specialist_display()}
    
    CHW Notes: {referral.notes if referral.notes else 'No additional notes'}
    
    Please login to your dashboard to view the full details and schedule an appointment.
    
    Login: http://127.0.0.1:8000/doctor/dashboard/
    
    Best regards,
    J.J. Dossen Hospital Administration
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [referral.doctor.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending email to doctor: {e}")


def send_chw_rejection_email(referral, rejection_reason):
    """Send email notification to CHW about rejected referral"""
    
    subject = f'Referral Rejected - {referral.referral_code}'
    
    message = f"""
    Dear {referral.chw.get_full_name()},
    
    Your referral has been reviewed and rejected by the administrator.
    
    Referral Details:
    ---------------
    Referral Code: {referral.referral_code}
    Patient Name: {referral.patient.full_name}
    Patient ID: {referral.patient.patient_id}
    
    Rejection Reason:
    ----------------
    {rejection_reason}
    
    Please login to your dashboard to view the details and make necessary corrections.
    
    Login: http://127.0.0.1:8000/chw/dashboard/
    
    Best regards,
    J.J. Dossen Hospital Administration
    """
    
    try:
        send_mail(
            subject,
            message,
            settings.DEFAULT_FROM_EMAIL,
            [referral.chw.email],
            fail_silently=False,
        )
    except Exception as e:
        print(f"Error sending email to CHW: {e}")


@login_required
@staff_member_required
def admin_pending_count_api(request):
    """API endpoint to get pending referrals count for admin badge"""
    count = Referral.objects.filter(status='pending_admin').count()
    return JsonResponse({'count': count})

@login_required
@staff_member_required
def admin_patient_tracking(request, patient_id):
    """Admin view to track any patient's progress"""
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    # Get all referrals for this patient (admin sees all)
    referrals = Referral.objects.filter(patient=patient).order_by('-created_at')
    
    # Get all activities for these referrals
    from referrals.models import ReferralActivity
    activities = ReferralActivity.objects.filter(referral__in=referrals).order_by('-timestamp')[:20]
    
    # Calculate summary statistics
    total_referrals = referrals.count()
    completed_referrals = referrals.filter(status='completed').count()
    emergency_count = referrals.filter(urgency='emergency').count()
    
    # Get all CHWs and doctors involved
    chws = set([ref.chw for ref in referrals if ref.chw])
    doctors = set([ref.doctor for ref in referrals if ref.doctor])
    
    context = {
        'patient': patient,
        'referrals': referrals,
        'activities': activities,
        'total_referrals': total_referrals,
        'completed_referrals': completed_referrals,
        'emergency_count': emergency_count,
        'chws': chws,
        'doctors': doctors,
    }
    return render(request, 'adminapp/tracking/patient_tracking.html', context)

# adminapp/views.py - Add these views

@login_required
@staff_member_required
def lost_patients(request):
    """Admin view for lost patients"""
    
    lost_patients = LostPatient.objects.filter(recovered=False).select_related('patient', 'referral')
    
    # Filter by reason
    reason_filter = request.GET.get('reason', '')
    if reason_filter:
        lost_patients = lost_patients.filter(reason=reason_filter)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        lost_patients = lost_patients.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__patient_id__icontains=search)
        )
    
    # Statistics
    total_lost = lost_patients.count()
    lost_by_reason = {}
    for reason, label in LostPatient.LOST_REASONS:
        lost_by_reason[reason] = LostPatient.objects.filter(reason=reason, recovered=False).count()
    
    paginator = Paginator(lost_patients, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_lost': total_lost,
        'lost_by_reason': lost_by_reason,
        'reason_filter': reason_filter,
        'search': search,
    }
    return render(request, 'adminapp/tracking/lost_patients.html', context)


@login_required
@staff_member_required
def mark_patient_recovered(request, lost_id):
    """Mark a lost patient as recovered"""
    
    lost_patient = get_object_or_404(LostPatient, id=lost_id)
    
    if request.method == 'POST':
        lost_patient.recovered = True
        lost_patient.recovered_date = timezone.now()
        lost_patient.save()
        
        # Create notification for CHW
        from referrals.models import UserNotification
        UserNotification.objects.create(
            user=lost_patient.referral.chw,
            notification_type='referral_created',
            title='Patient Recovered',
            message=f"Patient {lost_patient.patient.full_name} has been marked as recovered. Please follow up."
        )
        
        messages.success(request, f'Patient {lost_patient.patient.full_name} marked as recovered.')
        return redirect('adminapp:lost_patients')
    
    context = {
        'lost_patient': lost_patient,
    }
    return render(request, 'adminapp/tracking/mark_recovered.html', context)


@login_required
@staff_member_required
def overdue_followups(request):
    """Admin view for overdue follow-ups"""
    
    today = timezone.now()
    
    # Get all overdue follow-ups
    overdue = OverdueFollowUp.objects.filter(
        scheduled_date__lt=today,
        status__in=['pending', 'notified']
    ).select_related('patient', 'referral').order_by('scheduled_date')
    
    # Calculate overdue days
    for item in overdue:
        item.overdue_days = (today - item.scheduled_date).days
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        overdue = overdue.filter(follow_up_type=type_filter)
    
    # Statistics
    total_overdue = overdue.count()
    by_type = {}
    for ftype, label in OverdueFollowUp.FOLLOW_UP_TYPES:
        by_type[ftype] = OverdueFollowUp.objects.filter(
            follow_up_type=ftype,
            scheduled_date__lt=today,
            status__in=['pending', 'notified']
        ).count()
    
    paginator = Paginator(overdue, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_overdue': total_overdue,
        'by_type': by_type,
        'type_filter': type_filter,
    }
    return render(request, 'adminapp/tracking/overdue_followups.html', context)


@login_required
@staff_member_required
def resolve_overdue(request, overdue_id):
    """Resolve an overdue follow-up"""
    
    overdue = get_object_or_404(OverdueFollowUp, id=overdue_id)
    
    if request.method == 'POST':
        overdue.status = 'resolved'
        overdue.resolved_at = timezone.now()
        overdue.save()
        
        messages.success(request, f'Follow-up for {overdue.patient.full_name} marked as resolved.')
        return redirect('adminapp:overdue_followups')
    
    context = {
        'overdue': overdue,
    }
    return render(request, 'adminapp/tracking/resolve_overdue.html', context)


@login_required
@staff_member_required
def send_reminder_to_chw(request, overdue_id):
    """Send reminder to CHW about overdue follow-up"""
    
    overdue = get_object_or_404(OverdueFollowUp, id=overdue_id)
    
    if request.method == 'POST':
        # Create communication for CHW
        PatientCommunication.objects.create(
            referral=overdue.referral,
            from_user=request.user,
            to_user=overdue.referral.chw,
            communication_type='follow_up_needed',
            priority='high',
            subject=f'URGENT: Overdue Follow-up for {overdue.patient.full_name}',
            message=f"Patient is overdue for {overdue.follow_up_type} by {overdue.overdue_days} days. Original scheduled date: {overdue.scheduled_date.strftime('%Y-%m-%d')}. Please contact patient immediately.",
            requires_action=True
        )
        
        overdue.status = 'notified'
        overdue.notification_sent = True
        overdue.save()
        
        # Send email
        if overdue.referral.chw.email:
            send_mail(
                subject=f'Overdue Follow-up Alert: {overdue.patient.full_name}',
                message=f"Patient {overdue.patient.full_name} is overdue for {overdue.follow_up_type} by {overdue.overdue_days} days. Please contact them immediately.",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[overdue.referral.chw.email],
                fail_silently=True
            )
        
        messages.success(request, f'Reminder sent to CHW {overdue.referral.chw.get_full_name()}')
        return redirect('adminapp:overdue_followups')
    
    context = {
        'overdue': overdue,
    }
    return render(request, 'adminapp/tracking/send_reminder.html', context)

# adminapp/views.py - Add these API endpoints

@login_required
@staff_member_required
def lost_patients_count_api(request):
    """API endpoint to get lost patients count for badge"""
    count = LostPatient.objects.filter(recovered=False).count()
    return JsonResponse({'count': count})


@login_required
@staff_member_required
def overdue_count_api(request):
    """API endpoint to get overdue follow-ups count for badge"""
    today = timezone.now()
    count = OverdueFollowUp.objects.filter(
        scheduled_date__lt=today,
        status__in=['pending', 'notified']
    ).count()
    return JsonResponse({'count': count})

@login_required
@staff_member_required
def all_communications(request):
    """View all doctor-CHW communications"""
    
    from referrals.models import PatientCommunication
    
    communications = PatientCommunication.objects.select_related(
        'referral', 'referral__patient', 'from_user', 'to_user'
    ).order_by('-created_at')
    
    # Filter by priority
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        communications = communications.filter(priority=priority_filter)
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter:
        communications = communications.filter(communication_type=type_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'read':
        communications = communications.filter(is_read=True)
    elif status_filter == 'unread':
        communications = communications.filter(is_read=False)
    elif status_filter == 'action_required':
        communications = communications.filter(requires_action=True, action_taken=False)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        communications = communications.filter(
            Q(referral__patient__first_name__icontains=search) |
            Q(referral__patient__last_name__icontains=search) |
            Q(from_user__first_name__icontains=search) |
            Q(from_user__last_name__icontains=search) |
            Q(to_user__first_name__icontains=search) |
            Q(to_user__last_name__icontains=search) |
            Q(subject__icontains=search)
        )
    
    # Statistics
    total_count = communications.count()
    unread_count = PatientCommunication.objects.filter(is_read=False).count()
    action_required_count = PatientCommunication.objects.filter(requires_action=True, action_taken=False).count()
    high_priority_count = PatientCommunication.objects.filter(priority='high').count()
    
    # Pagination
    paginator = Paginator(communications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'total_count': total_count,
        'unread_count': unread_count,
        'action_required_count': action_required_count,
        'high_priority_count': high_priority_count,
        'priority_filter': priority_filter,
        'type_filter': type_filter,
        'status_filter': status_filter,
        'search': search,
    }
    return render(request, 'adminapp/tracking/communications.html', context)


@login_required
@staff_member_required
def communication_detail_api(request, comm_id):
    """API endpoint to get communication details"""
    
    from referrals.models import PatientCommunication
    
    comm = get_object_or_404(PatientCommunication, id=comm_id)
    
    return JsonResponse({
        'id': comm.id,
        'doctor_name': comm.from_user.get_full_name() or comm.from_user.username,
        'chw_name': comm.to_user.get_full_name() or comm.to_user.username,
        'patient_name': comm.referral.patient.full_name,
        'patient_id': comm.referral.patient.patient_id,
        'subject': comm.subject,
        'message': comm.message,
        'priority_display': comm.get_priority_display(),
        'type_display': comm.get_communication_type_display(),
        'created_at': comm.created_at.strftime('%Y-%m-%d %H:%M:%S'),
        'read_at': comm.read_at.strftime('%Y-%m-%d %H:%M:%S') if comm.read_at else None,
        'action_taken': comm.action_taken,
    })


@login_required
@staff_member_required
def send_communication_reminder(request, comm_id):
    """Send reminder to CHW about pending action"""
    
    from referrals.models import PatientCommunication
    from django.core.mail import send_mail
    
    comm = get_object_or_404(PatientCommunication, id=comm_id)
    
    if comm.to_user.email:
        send_mail(
            subject=f'REMINDER: Action Required - {comm.subject}',
            message=f"Dear {comm.to_user.get_full_name()},\n\nThis is a reminder from Admin regarding patient {comm.referral.patient.full_name}.\n\nSubject: {comm.subject}\n\nMessage from Doctor: {comm.message}\n\nPlease log in to your dashboard and take the required action.\n\nThank you,\nJ.J. Dossen Hospital Administration",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[comm.to_user.email],
            fail_silently=True
        )
    
    return JsonResponse({'success': True})


@login_required
@staff_member_required
def export_communications(request):
    """Export communications to CSV"""
    
    import csv
    from django.http import HttpResponse
    from referrals.models import PatientCommunication
    
    communications = PatientCommunication.objects.select_related(
        'referral', 'referral__patient', 'from_user', 'to_user'
    ).order_by('-created_at')
    
    # Apply same filters as main view
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        communications = communications.filter(priority=priority_filter)
    
    type_filter = request.GET.get('type', '')
    if type_filter:
        communications = communications.filter(communication_type=type_filter)
    
    status_filter = request.GET.get('status', '')
    if status_filter == 'read':
        communications = communications.filter(is_read=True)
    elif status_filter == 'unread':
        communications = communications.filter(is_read=False)
    
    search = request.GET.get('search', '')
    if search:
        communications = communications.filter(
            Q(referral__patient__first_name__icontains=search) |
            Q(referral__patient__last_name__icontains=search) |
            Q(subject__icontains=search)
        )
    
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="communications_export.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Date', 'Doctor', 'CHW', 'Patient', 'Type', 'Priority', 'Subject', 'Status', 'Action Taken'])
    
    for comm in communications:
        writer.writerow([
            comm.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            comm.from_user.get_full_name() or comm.from_user.username,
            comm.to_user.get_full_name() or comm.to_user.username,
            comm.referral.patient.full_name,
            comm.get_communication_type_display(),
            comm.get_priority_display(),
            comm.subject,
            'Read' if comm.is_read else 'Unread',
            'Yes' if comm.action_taken else 'No'
        ])
    
    return response