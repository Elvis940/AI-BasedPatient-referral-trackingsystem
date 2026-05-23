from django.core.mail import send_mail
from django.conf import settings

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
        return True
    except Exception as e:
        print(f"Error sending email to doctor: {e}")
        return False


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
        return True
    except Exception as e:
        print(f"Error sending email to CHW: {e}")
        return False


def send_chw_approval_notification(referral):
    """Send email to CHW when referral is approved"""
    
    subject = f'Referral Approved - {referral.referral_code}'
    
    message = f"""
    Dear {referral.chw.get_full_name()},
    
    Your referral has been approved by the administrator!
    
    Referral Details:
    ---------------
    Referral Code: {referral.referral_code}
    Patient Name: {referral.patient.full_name}
    
    The doctor has been notified and will contact the patient shortly.
    
    You can track the progress from your dashboard.
    
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
        return True
    except Exception as e:
        print(f"Error sending email to CHW: {e}")
        return False