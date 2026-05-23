from django.core.mail import EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
import logging

logger = logging.getLogger(__name__)

def send_user_credentials_email(user, password, request):
    """Send email with credentials to new user"""
    
    try:
        profile = user.profile
        
        subject = f"Welcome to J.J. Dossen Patient Tracking System - Your Account Credentials"
        
        login_url = request.build_absolute_uri('/login/')
        
        context = {
            'user': user,
            'profile': profile,
            'password': password,
            'hospital_name': 'J.J. Dossen Memorial Hospital',
            'login_url': login_url,
            'support_email': 'support@jjdossen.org',
        }
        
        html_message = render_to_string('adminapp/email/credentials_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Use a clean from_email address
        from_email = settings.DEFAULT_FROM_EMAIL
        
        email = EmailMultiAlternatives(
            subject,
            plain_message,
            from_email,
            [user.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        print(f"Credentials email sent successfully to {user.email}")
        return True
        
    except Exception as e:
        print(f"Error sending credentials email to {user.email}: {str(e)}")
        logger.error(f"Email error: {str(e)}")
        return False


def send_account_activated_email(user, activated_by=None):
    """Send email notification when account is activated"""
    
    try:
        subject = f"Your J.J. Dossen Account Has Been Activated"
        
        context = {
            'user': user,
            'profile': user.profile,
            'activated_by': activated_by,
            'login_url': '/login/',
        }
        
        html_message = render_to_string('adminapp/email/activation_email.html', context)
        plain_message = strip_tags(html_message)
        
        # Use a clean from_email address
        from_email = settings.DEFAULT_FROM_EMAIL
        
        email = EmailMultiAlternatives(
            subject,
            plain_message,
            from_email,
            [user.email],
        )
        email.attach_alternative(html_message, "text/html")
        email.send(fail_silently=False)
        
        print(f"Activation email sent successfully to {user.email}")
        return True
        
    except Exception as e:
        print(f"Error sending activation email to {user.email}: {str(e)}")
        logger.error(f"Activation email error: {str(e)}")
        return False