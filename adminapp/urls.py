from django.urls import path, include
from . import views

app_name = 'adminapp'

urlpatterns = [
    # Home page
    path('', views.home, name='home'),
    
    # Unified Login
    path('login/', views.user_login, name='login'),
    # Remove the custom logout - use Django's built-in instead
    # path('logout/', views.admin_logout, name='logout'),  # DELETE THIS LINE
    
    # Admin Dashboard
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    
    # User Management
  
    path('', include('user_management.urls')),
     path('lost-patients/', views.lost_patients, name='lost_patients'),
    path('lost-patients/count-api/', views.lost_patients_count_api, name='lost_patients_count_api'),
    path('lost-patients/mark-recovered/<int:lost_id>/', views.mark_patient_recovered, name='mark_patient_recovered'),
    path('overdue-followups/', views.overdue_followups, name='overdue_followups'),
    path('overdue-followups/count-api/', views.overdue_count_api, name='overdue_count_api'),
    path('overdue-followups/resolve/<int:overdue_id>/', views.resolve_overdue, name='resolve_overdue'),
    path('overdue-followups/send-reminder/<int:overdue_id>/', views.send_reminder_to_chw, name='send_reminder_to_chw'),
    
    # Admin Referral Management
    path('referrals/', views.admin_all_referrals, name='admin_all_referrals'),
    path('referrals/<int:referral_id>/review/', views.admin_review_referral, name='admin_review_referral'),
    path('referrals/<int:referral_id>/approve/', views.admin_approve_referral, name='admin_approve_referral'),
    path('referrals/<int:referral_id>/reject/', views.admin_reject_referral, name='admin_reject_referral'),
    path('tracking/patient/<int:patient_id>/', views.admin_patient_tracking, name='admin_patient_tracking'),
    # API endpoint for pending count
    path('api/referrals/pending-count/', views.admin_pending_count_api, name='admin_pending_count_api'),

    path('communications/', views.all_communications, name='all_communications'),
path('communications/<int:comm_id>/detail/', views.communication_detail_api, name='communication_detail_api'),
path('communications/<int:comm_id>/send-reminder/', views.send_communication_reminder, name='send_communication_reminder'),
path('communications/export/', views.export_communications, name='export_communications'),


]