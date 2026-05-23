from django.urls import path
from . import views

app_name = 'referrals'

urlpatterns = [
    path('', views.referral_list, name='referral_list'),
    path('list/', views.referral_list, name='referral_list'),
    path('<int:referral_id>/', views.referral_detail, name='referral_detail'),
    path('<int:referral_id>/delete/', views.delete_referral, name='delete_referral'),
    path('stats/', views.referral_stats, name='referral_stats'),
    path('create-from-assessment/<int:assessment_id>/', views.create_referral_from_assessment, name='create_from_assessment'),
    path('<int:referral_id>/update-status/', views.update_referral_status, name='update_referral_status'),

    path('api/notifications/', views.notifications_api, name='notifications_api'),
path('api/notifications/<int:notification_id>/read/', views.mark_notification_read, name='mark_notification_read'),
path('api/notifications/read-all/', views.mark_all_notifications_read, name='mark_all_notifications_read'),
]