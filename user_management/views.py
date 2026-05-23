from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from django.contrib.auth.models import User
from django.db.models import Q
from django.core.paginator import Paginator
from django.utils import timezone
from .models import UserProfile, UserActivityLog, UserActivationLog
from .forms import UserCreateForm, UserEditForm, UserProfileForm
from .utils import send_user_credentials_email, send_account_activated_email

@login_required
@staff_member_required
def all_users(request):
    """View all users with filters and search"""
    
    # Auto-activate pending accounts that are older than 2 minutes
    pending_users = UserProfile.objects.filter(status='pending')
    for profile in pending_users:
        if profile.should_auto_activate():
            profile.activate()
            # Log auto-activation
            UserActivationLog.objects.create(
                user=profile.user,
                activated_by=None,
                activation_type='auto',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            # Send activation email
            send_account_activated_email(profile.user)
            messages.info(request, f"User {profile.user.username} was automatically activated.")
    
    # Get filter parameters
    search = request.GET.get('search', '')
    user_type = request.GET.get('user_type', '')
    status = request.GET.get('status', '')
    
    # Base queryset - exclude superusers (admins)
    users = User.objects.filter(is_superuser=False).select_related('profile').all()
    
    # Apply filters
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search) |
            Q(profile__chw_id__icontains=search) |
            Q(profile__doctor_id__icontains=search)
        )
    
    if user_type:
        users = users.filter(profile__user_type=user_type)
    
    if status:
        users = users.filter(profile__status=status)
    
    # Pagination
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get statistics
    total_users = User.objects.filter(is_superuser=False).count()
    total_doctors = User.objects.filter(profile__user_type='doctor', is_superuser=False).count()
    total_chws = User.objects.filter(profile__user_type='chw', is_superuser=False).count()
    active_users = User.objects.filter(profile__status='active', is_superuser=False).count()
    pending_users_count = User.objects.filter(profile__status='pending', is_superuser=False).count()
    
    context = {
        'page_obj': page_obj,
        'total_users': total_users,
        'total_doctors': total_doctors,
        'total_chws': total_chws,
        'active_users': active_users,
        'pending_users': pending_users_count,
        'search': search,
        'user_type_filter': user_type,
        'status_filter': status,
    }
    
    return render(request, 'adminapp/user_management/all_users.html', context)

@login_required
@staff_member_required
def add_user(request):
    """Add a new user"""
    
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            password = form.cleaned_data['password']
            
            # Send credentials email
            email_sent = send_user_credentials_email(user, password, request)
            
            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                activity_type='create',
                description=f"Created new user: {user.username} ({user.profile.get_user_type_display()})",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            if email_sent:
                messages.success(request, f'User {user.username} created successfully! Credentials have been sent to {user.email}')
            else:
                messages.warning(request, f'User {user.username} created but email could not be sent. Please check email settings.')
            
            return redirect('user_management:all_users')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserCreateForm()
    
    return render(request, 'adminapp/user_management/add_user.html', {'form': form})
@login_required
@staff_member_required
def view_user(request, user_id):
    """View user details"""
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    # Log activity
    UserActivityLog.objects.create(
        user=request.user,
        activity_type='view',
        description=f"Viewed user details: {user.username}",
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return render(request, 'adminapp/user_management/view_user.html', {'user_obj': user})

@login_required
@staff_member_required
def edit_user(request, user_id):
    """Edit user details"""
    
    user = get_object_or_404(User.objects.select_related('profile'), id=user_id)
    
    if request.method == 'POST':
        user_form = UserEditForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile = profile_form.save(commit=False)
            
            # Handle specialization
            specialization = profile_form.cleaned_data.get('specialization')
            custom_specialization = profile_form.cleaned_data.get('custom_specialization')
            
            if specialization == 'other' and custom_specialization:
                profile.specialization = 'other'
                profile.custom_specialization = custom_specialization
            else:
                profile.specialization = specialization
                profile.custom_specialization = ''
            
            profile.save()
            
            # Log activity
            UserActivityLog.objects.create(
                user=request.user,
                activity_type='update',
                description=f"Updated user: {user.username}",
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, f'User {user.username} updated successfully!')
            return redirect('user_management:view_user', user_id=user.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        user_form = UserEditForm(instance=user)
        profile_form = UserProfileForm(instance=user.profile)
    
    context = {
        'user_obj': user,
        'user_form': user_form,
        'profile_form': profile_form,
    }
    
    return render(request, 'adminapp/user_management/edit_user.html', context)

@login_required
@staff_member_required
def delete_user(request, user_id):
    """Delete a user with confirmation"""
    
    user = get_object_or_404(User, id=user_id)
    
    # Prevent deleting yourself
    if user.id == request.user.id:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_management:all_users')
    
    if request.method == 'POST':
        username = user.username
        
        # Log activity before deletion
        UserActivityLog.objects.create(
            user=request.user,
            activity_type='delete',
            description=f"Deleted user: {username}",
            ip_address=request.META.get('REMOTE_ADDR')
        )
        
        user.delete()
        messages.success(request, f'User {username} has been permanently deleted.')
        return redirect('user_management:all_users')
    
    return render(request, 'adminapp/user_management/delete_user.html', {'user_obj': user})

@login_required
@staff_member_required
def toggle_user_status(request, user_id):
    """Activate or deactivate a user with confirmation message"""
    
    user = get_object_or_404(User, id=user_id)
    
    if user.id == request.user.id:
        messages.error(request, 'You cannot change your own status.')
        return redirect('user_management:all_users')
    
    old_status = user.profile.status
    status_msg = ''
    activation_type = None
    
    if user.profile.status == 'active':
        user.profile.status = 'inactive'
        status_msg = 'deactivated'
        messages.success(request, f'User {user.username} has been deactivated.')
    elif user.profile.status == 'inactive':
        user.profile.status = 'active'
        status_msg = 'activated'
        activation_type = 'manual'
        messages.success(request, f'User {user.username} has been activated successfully!')
    elif user.profile.status == 'pending':
        user.profile.status = 'active'
        status_msg = 'activated'
        activation_type = 'manual'
        messages.success(request, f'User {user.username} has been activated successfully!')
    else:
        user.profile.status = 'active'
        status_msg = 'activated'
        activation_type = 'manual'
        messages.success(request, f'User {user.username} has been activated successfully!')
    
    user.profile.save()
    
    # Log activation if applicable
    if activation_type and status_msg == 'activated':
        UserActivationLog.objects.create(
            user=user,
            activated_by=request.user,
            activation_type=activation_type,
            ip_address=request.META.get('REMOTE_ADDR')
        )
        # Send activation email
        email_sent = send_account_activated_email(user, request.user)
        if not email_sent:
            messages.warning(request, f'User activated but activation email could not be sent.')
    
    # Log activity
    UserActivityLog.objects.create(
        user=request.user,
        activity_type='update',
        description=f"{status_msg.capitalize()} user: {user.username}",
        ip_address=request.META.get('REMOTE_ADDR')
    )
    
    return redirect('user_management:all_users')

@login_required
@staff_member_required
def roles_permissions(request):
    """Manage user roles and permissions"""
    
    users = User.objects.select_related('profile').filter(
        profile__user_type__in=['doctor', 'chw']
    ).order_by('profile__user_type', 'username')
    
    # Group users by type
    doctors = users.filter(profile__user_type='doctor')
    chws = users.filter(profile__user_type='chw')
    
    context = {
        'doctors': doctors,
        'chws': chws,
    }
    
    return render(request, 'adminapp/user_management/roles_permissions.html', context)


from django.core.mail import send_mail
from django.conf import settings

def test_email(request):
    """Test email functionality"""
    try:
        send_mail(
            'Test Email from J.J. Dossen System',
            'This is a test email to verify SMTP configuration.',
            settings.DEFAULT_FROM_EMAIL,
            ['harmonelvis78@gmail.com'],  # Your test email
            fail_silently=False,
        )
        messages.success(request, 'Test email sent successfully!')
    except Exception as e:
        messages.error(request, f'Email failed: {str(e)}')
    return redirect('user_management:all_users')