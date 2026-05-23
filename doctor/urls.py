from django.urls import path
from . import views

app_name = 'doctor'

urlpatterns = [
    path('dashboard/', views.dashboard, name='dashboard'),
    path('patients/', views.my_patients, name='my_patients'),
    path('patient-history/<int:patient_id>/', views.patient_history, name='patient_history'),
    path('referrals/pending/', views.pending_referrals, name='pending_referrals'),
    path('referrals/completed/', views.completed_referrals, name='completed_referrals'),
    path('referrals/all/', views.all_referrals, name='all_referrals'),
    path('referrals/view/<int:referral_id>/', views.view_referral, name='view_referral'),
    path('referrals/<int:referral_id>/check-in/', views.patient_check_in, name='patient_check_in'),
    path('referrals/<int:referral_id>/check-out/', views.patient_check_out, name='patient_check_out'),
    path('referrals/<int:referral_id>/prescribe/', views.prescribe_medication, name='prescribe_medication'),
    path('referrals/<int:referral_id>/complete-treatment/', views.complete_treatment, name='complete_treatment'),
    path('prescriptions/write/', views.write_prescription, name='write_prescription'),
    path('prescriptions/write/<int:patient_id>/', views.write_prescription, name='write_prescription_for_patient'),
    path('prescriptions/history/', views.prescription_history, name='prescription_history'),
    path('prescriptions/list/', views.prescription_list, name='prescription_list'),  # NEW
    path('prescriptions/<int:prescription_id>/', views.prescription_detail, name='prescription_detail'),  # NEW
    path('prescriptions/<int:prescription_id>/edit/', views.prescription_edit, name='prescription_edit'),  # NEW
    path('prescriptions/<int:prescription_id>/delete/', views.prescription_delete, name='prescription_delete'),  # NEW
    path('prescriptions/<int:prescription_id>/clear/', views.prescription_clear, name='prescription_clear'),  # NEW
    path('prescriptions/<int:prescription_id>/print/', views.prescription_print, name='prescription_print'),  # NEW
    path('schedule/today/', views.appointments_today, name='appointments_today'),
    path('schedule/', views.schedule, name='schedule'),
    path('api/pending-count/', views.pending_count_api, name='pending_count_api'),
    path('api/active-prescriptions-count/', views.active_prescriptions_count_api, name='active_prescriptions_count_api'),
    path('tracking/patient/<int:patient_id>/', views.doctor_patient_tracking, name='doctor_patient_tracking'),

    path('report-missed/<int:referral_id>/', views.report_missed_appointment, name='report_missed_appointment'),
    path('send-chw-update/<int:referral_id>/', views.send_patient_update_to_chw, name='send_patient_update_to_chw'),
    path('communications/', views.doctor_communications, name='doctor_communications'),
]