from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import UserNotification, Referral

def send_chw_notification_email(referral, subject, message):
    """Send email notification to CHW"""
    if referral.chw and referral.chw.email:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[referral.chw.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Error sending email to CHW: {e}")
            return False
    return False


def send_doctor_notification_email(referral, subject, message):
    """Send email notification to Doctor (only on approval)"""
    if referral.doctor and referral.doctor.email:
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[referral.doctor.email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Error sending email to Doctor: {e}")
            return False
    return False


def create_dashboard_notification(user, referral, notification_type, title, message):
    """Create a dashboard notification for user"""
    UserNotification.objects.create(
        user=user,
        referral=referral,
        notification_type=notification_type,
        title=title,
        message=message,
        is_read=False
    )


def send_approval_notifications(referral):
    """Send all notifications when referral is approved"""
    
    # 1. Send email to CHW
    chw_subject = f'Referral Approved - {referral.referral_code}'
    chw_message = f"""
    Dear {referral.chw.get_full_name()},
    
    Your referral has been APPROVED by the administrator.
    
    Referral Details:
    ---------------
    Referral Code: {referral.referral_code}
    Patient Name: {referral.patient.full_name}
    Patient ID: {referral.patient.patient_id}
    Urgency: {referral.get_urgency_display()}
    Specialist: {referral.get_specialist_display()}
    
    Assigned Doctor: Dr. {referral.doctor.get_full_name() if referral.doctor else 'To be assigned'}
    
    You can track the progress from your dashboard.
    
    Best regards,
    J.J. Dossen Hospital Administration
    """
    send_chw_notification_email(referral, chw_subject, chw_message)
    
    # 2. Create dashboard notification for CHW
    create_dashboard_notification(
        user=referral.chw,
        referral=referral,
        notification_type='referral_approved',
        title=f'Referral Approved - {referral.referral_code}',
        message=f'Your referral for {referral.patient.full_name} has been approved and assigned to Dr. {referral.doctor.get_full_name() if referral.doctor else "a doctor"}'
    )
    
    # 3. Send email to Doctor (only if doctor exists)
    if referral.doctor:
        doctor_subject = f'New Referral Assigned - {referral.referral_code}'
        doctor_message = f"""
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
        
        Please login to your dashboard to view the full details.
        
        Login: http://127.0.0.1:8000/doctor/dashboard/
        
        Best regards,
        J.J. Dossen Hospital Administration
        """
        send_doctor_notification_email(referral, doctor_subject, doctor_message)
        
        # 4. Create dashboard notification for Doctor
        create_dashboard_notification(
            user=referral.doctor,
            referral=referral,
            notification_type='referral_approved',
            title=f'New Referral Assigned - {referral.referral_code}',
            message=f'New referral for {referral.patient.full_name} has been assigned to you. Urgency: {referral.get_urgency_display()}'
        )
    
    # Mark notifications as sent
    referral.chw_notification_sent = True
    if referral.doctor:
        referral.doctor_notification_sent = True
    referral.save()


def send_rejection_notifications(referral, rejection_reason):
    """Send all notifications when referral is rejected"""
    
    # 1. Send email to CHW
    chw_subject = f'Referral Rejected - {referral.referral_code}'
    chw_message = f"""
    Dear {referral.chw.get_full_name()},
    
    Your referral has been REJECTED by the administrator.
    
    Referral Details:
    ---------------
    Referral Code: {referral.referral_code}
    Patient Name: {referral.patient.full_name}
    Patient ID: {referral.patient.patient_id}
    
    Rejection Reason:
    ----------------
    {rejection_reason}
    
    Please login to your dashboard to view the details and make necessary corrections.
    
    Best regards,
    J.J. Dossen Hospital Administration
    """
    send_chw_notification_email(referral, chw_subject, chw_message)
    
    # 2. Create dashboard notification for CHW
    create_dashboard_notification(
        user=referral.chw,
        referral=referral,
        notification_type='referral_rejected',
        title=f'Referral Rejected - {referral.referral_code}',
        message=f'Your referral for {referral.patient.full_name} was rejected. Reason: {rejection_reason}'
    )
    
    # No email to doctor on rejection
    referral.chw_notification_sent = True
    referral.save()


def get_unread_notifications_count(user):
    """Get count of unread notifications for a user"""
    return UserNotification.objects.filter(user=user, is_read=False).count()


def mark_notification_as_read(notification_id, user):
    """Mark a specific notification as read"""
    try:
        notification = UserNotification.objects.get(id=notification_id, user=user)
        notification.is_read = True
        notification.save()
        return True
    except UserNotification.DoesNotExist:
        return False


def mark_all_notifications_as_read(user):
    """Mark all notifications as read for a user"""
    UserNotification.objects.filter(user=user, is_read=False).update(is_read=True)