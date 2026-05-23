from django.urls import path
from . import views

app_name = 'chw'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patient-tracking/<int:patient_id>/', views.patient_tracking, name='patient_tracking'),
    path('send-message/<int:referral_id>/', views.send_patient_message, name='send_patient_message'),
     path('communications/', views.chw_communications, name='chw_communications'),
    path('mark-read/<int:comm_id>/', views.mark_communication_read, name='mark_communication_read'),
    path('acknowledge-report/<int:report_id>/', views.acknowledge_patient_report, name='acknowledge_report'),
     path('communications/', views.chw_communications, name='chw_communications'),
    path('mark-communication-read/<int:comm_id>/', views.mark_communication_read, name='mark_communication_read'),
    path('mark-all-read/', views.mark_all_communications_read, name='mark_all_read'),
    path('take-action/<int:comm_id>/', views.take_action_on_communication, name='take_action'),
    path('api/unread-count/', views.unread_count_api, name='unread_count_api'),
]