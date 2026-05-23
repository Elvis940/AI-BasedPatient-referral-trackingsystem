from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import Referral, ReferralActivity, UserNotification
from patients.models import Patient
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from django.http import JsonResponse
from .notification_utils import get_unread_notifications_count, mark_notification_as_read, mark_all_notifications_as_read

@login_required
def referral_list(request):
    """List all referrals based on user role"""
    
    user = request.user
    
    # Determine which referrals to show based on user type
    if user.is_staff or user.is_superuser:
        # Admin sees all referrals
        referrals = Referral.objects.all()
    elif hasattr(user, 'profile'):
        if user.profile.user_type == 'chw':
            # CHW sees their own referrals
            referrals = Referral.objects.filter(chw=user)
        elif user.profile.user_type == 'doctor':
            # Doctor sees referrals assigned to them
            referrals = Referral.objects.filter(doctor=user)
        else:
            referrals = Referral.objects.none()
    else:
        referrals = Referral.objects.none()
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        referrals = referrals.filter(status=status_filter)
    
    # Filter by date range
    date_range = request.GET.get('date_range', '')
    today = timezone.now().date()
    
    if date_range == 'today':
        referrals = referrals.filter(created_at__date=today)
    elif date_range == 'week':
        week_ago = today - timedelta(days=7)
        referrals = referrals.filter(created_at__date__gte=week_ago)
    elif date_range == 'month':
        month_ago = today - timedelta(days=30)
        referrals = referrals.filter(created_at__date__gte=month_ago)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        referrals = referrals.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(referral_code__icontains=search)
        )
    
    context = {
        'referrals': referrals,
        'status_filter': status_filter,
        'date_range': date_range,
        'search': search,
        'total_count': referrals.count(),
    }
    return render(request, 'referrals/referral_list.html', context)

# In referrals/views.py - Update your referral_detail function

@login_required
def referral_detail(request, referral_id):
    """View referral details - stays in correct dashboard based on user type"""
    
    referral = get_object_or_404(Referral, id=referral_id)
    
    # Check if user has permission to view this referral
    user = request.user
    has_permission = False
    
    if user.is_staff or user.is_superuser:
        has_permission = True
    elif hasattr(user, 'profile'):
        if user.profile.user_type == 'chw' and referral.chw == user:
            has_permission = True
        elif user.profile.user_type == 'doctor' and referral.doctor == user:
            has_permission = True
    
    if not has_permission:
        messages.error(request, 'You do not have permission to view this referral.')
        if hasattr(user, 'profile'):
            if user.profile.user_type == 'chw':
                return redirect('referrals:referral_list')
            elif user.profile.user_type == 'doctor':
                return redirect('doctor:pending_referrals')
        return redirect('home')
    
    # Log activity
    ReferralActivity.objects.create(
        referral=referral,
        activity_type='viewed',
        performed_by=request.user,
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    # DEBUG: Print to console
    print("=" * 50)
    print(f"Referral ID: {referral.id}")
    print(f"Referral Code: {referral.referral_code}")
    
    # Get medications for this referral
    from referrals.models import Medication
    medications = Medication.objects.filter(referral=referral).order_by('-prescribed_at')
    
    # DEBUG: Print medication count
    print(f"Medications found: {medications.count()}")
    for med in medications:
        print(f"  - {med.medication_name} | Status: {med.status}")
    
    # Get prescriptions for this patient
    prescriptions = []
    if referral.doctor:
        try:
            from doctor.models import Prescription
            prescriptions = Prescription.objects.filter(
                patient=referral.patient,
                doctor=referral.doctor
            ).order_by('-created_at')
            print(f"Prescriptions found: {prescriptions.count()}")
        except ImportError:
            print("Prescription model not available")
    
    print("=" * 50)
    
    # Get available statuses based on user type
    available_statuses = []
    if hasattr(user, 'profile'):
        if user.profile.user_type == 'doctor':
            available_statuses = ['accepted', 'in_progress', 'completed', 'rejected']
        elif user.profile.user_type == 'chw':
            available_statuses = ['cancelled']
        elif user.is_staff:
            available_statuses = ['accepted', 'in_progress', 'completed', 'cancelled', 'rejected']
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        if new_status in available_statuses:
            old_status = referral.status
            referral.status = new_status
            if notes:
                referral.notes = notes
            if new_status == 'completed':
                referral.completed_at = timezone.now()
            referral.save()
            
            ReferralActivity.objects.create(
                referral=referral,
                activity_type=new_status,
                performed_by=request.user,
                description=notes,
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'Referral status updated to {new_status}!')
            return redirect('referrals:referral_detail', referral_id=referral.id)
    
    context = {
        'referral': referral,
        'medications': medications,  # Make sure this is passed
        'prescriptions': prescriptions,
        'available_statuses': available_statuses,
        'user_type': user.profile.user_type if hasattr(user, 'profile') else 'admin',
    }
    
    # DEBUG: Print context keys
    print(f"Context keys: {context.keys()}")
    print(f"Medications in context: {context['medications'].count()}")
    
    return render(request, 'referrals/referral_detail.html', context)

@login_required
def update_referral_status(request, referral_id):
    """Update referral status via POST"""
    
    referral = get_object_or_404(Referral, id=referral_id)
    user = request.user
    
    # Check permission
    has_permission = False
    if user.is_staff or user.is_superuser:
        has_permission = True
    elif hasattr(user, 'profile'):
        if user.profile.user_type == 'doctor' and referral.doctor == user:
            has_permission = True
        elif user.profile.user_type == 'chw' and referral.chw == user:
            has_permission = True
    
    if not has_permission:
        messages.error(request, 'You do not have permission to update this referral.')
        return redirect('referrals:referral_detail', referral_id=referral.id)
    
    if request.method == 'POST':
        new_status = request.POST.get('status')
        notes = request.POST.get('notes', '')
        
        old_status = referral.status
        referral.status = new_status
        if notes:
            referral.notes = notes
        if new_status == 'completed':
            referral.completed_at = timezone.now()
        referral.save()
        
        ReferralActivity.objects.create(
            referral=referral,
            activity_type=new_status,
            performed_by=request.user,
            description=notes,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'Referral status updated to {new_status}!')
    
    # Redirect based on user type
    if hasattr(user, 'profile') and user.profile.user_type == 'doctor':
        return redirect('doctor:pending_referrals')
    else:
        return redirect('referrals:referral_detail', referral_id=referral.id)


@login_required
def create_referral_from_assessment(request, assessment_id):
    """Create referral from an AI assessment"""
    
    from ai_assessment.models import SymptomAssessment
    
    assessment = get_object_or_404(SymptomAssessment, id=assessment_id)
    
    if request.method == 'POST':
        doctor_id = request.POST.get('doctor_id')
        
        referral = Referral.objects.create(
            patient=assessment.patient,
            chw=request.user,
            doctor_id=doctor_id,
            assessment=assessment,
            urgency=assessment.ai_urgency,
            specialist=assessment.ai_specialist,
            notes=request.POST.get('notes', '')
        )
        
        ReferralActivity.objects.create(
            referral=referral,
            activity_type='created',
            performed_by=request.user,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        messages.success(request, f'Referral created successfully! Code: {referral.referral_code}')
        return redirect('referrals:referral_detail', referral_id=referral.id)
    
    return redirect('ai_assessment:assessment_result', assessment_id=assessment_id)


@login_required
def delete_referral(request, referral_id):
    """Delete a referral with confirmation"""
    
    referral = get_object_or_404(Referral, id=referral_id)
    
    # Check permissions - only CHW who created it or admin can delete
    user = request.user
    can_delete = False
    
    if user.is_staff or user.is_superuser:
        can_delete = True
    elif hasattr(user, 'profile') and user.profile.user_type == 'chw':
        if referral.chw == user:
            can_delete = True
    
    if not can_delete:
        messages.error(request, 'You do not have permission to delete this referral.')
        return redirect('referrals:referral_detail', referral_id=referral.id)
    
    if request.method == 'POST':
        referral_code = referral.referral_code
        
        # Log activity before deletion
        ReferralActivity.objects.create(
            referral=referral,
            activity_type='cancelled',
            performed_by=request.user,
            description=f'Referral deleted by {request.user.username}',
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        referral.delete()
        messages.success(request, f'Referral {referral_code} has been deleted successfully.')
        return redirect('referrals:referral_list')
    
    return render(request, 'referrals/delete_referral.html', {'referral': referral})


@login_required
def referral_stats(request):
    """Referral statistics dashboard"""
    
    user = request.user
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    # Base queryset based on user type
    if user.is_staff or user.is_superuser:
        referrals = Referral.objects.all()
    elif hasattr(user, 'profile'):
        if user.profile.user_type == 'chw':
            referrals = Referral.objects.filter(chw=user)
        elif user.profile.user_type == 'doctor':
            referrals = Referral.objects.filter(doctor=user)
        else:
            referrals = Referral.objects.none()
    else:
        referrals = Referral.objects.none()
    
    # Statistics
    total_referrals = referrals.count()
    pending_referrals = referrals.filter(status='pending').count()
    completed_referrals = referrals.filter(status='completed').count()
    cancelled_referrals = referrals.filter(status='cancelled').count()
    
    # Daily stats
    today_referrals = referrals.filter(created_at__date=today).count()
    week_referrals = referrals.filter(created_at__date__gte=week_ago).count()
    month_referrals = referrals.filter(created_at__date__gte=month_ago).count()
    
    # Referrals by urgency
    emergency_count = referrals.filter(urgency='emergency').count()
    urgent_count = referrals.filter(urgency='urgent').count()
    non_urgent_count = referrals.filter(urgency='non_urgent').count()
    
    # Referrals by specialist
    specialist_counts = referrals.values('specialist').annotate(count=Count('id')).order_by('-count')
    
    # Referrals by month (last 6 months)
    monthly_data = []
    for i in range(6):
        month_date = today - timedelta(days=30*i)
        month_start = month_date.replace(day=1)
        if i == 0:
            month_end = today
        else:
            next_month = month_start.replace(day=28) + timedelta(days=4)
            month_end = next_month - timedelta(days=next_month.day)
        
        count = referrals.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end
        ).count()
        
        monthly_data.append({
            'month': month_start.strftime('%B %Y'),
            'count': count
        })
    
    context = {
        'total_referrals': total_referrals,
        'pending_referrals': pending_referrals,
        'completed_referrals': completed_referrals,
        'cancelled_referrals': cancelled_referrals,
        'today_referrals': today_referrals,
        'week_referrals': week_referrals,
        'month_referrals': month_referrals,
        'emergency_count': emergency_count,
        'urgent_count': urgent_count,
        'non_urgent_count': non_urgent_count,
        'specialist_counts': specialist_counts,
        'monthly_data': monthly_data,
    }
    return render(request, 'referrals/referral_stats.html', context)


@login_required
@require_http_methods(["GET"])
def notifications_api(request):
    """API endpoint to get user notifications"""
    notifications = UserNotification.objects.filter(user=request.user)[:20]
    data = {
        'unread_count': get_unread_notifications_count(request.user),
        'notifications': [
            {
                'id': n.id,
                'title': n.title,
                'message': n.message,
                'type': n.notification_type,
                'is_read': n.is_read,
                'created_at': n.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'referral_id': n.referral.id if n.referral else None
            }
            for n in notifications
        ]
    }
    return JsonResponse(data)


@login_required
@require_http_methods(["POST"])
def mark_notification_read(request, notification_id):
    """Mark a single notification as read"""
    if mark_notification_as_read(notification_id, request.user):
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=400)


@login_required
@require_http_methods(["POST"])
def mark_all_notifications_read(request):
    """Mark all notifications as read"""
    mark_all_notifications_as_read(request.user)
    return JsonResponse({'success': True})