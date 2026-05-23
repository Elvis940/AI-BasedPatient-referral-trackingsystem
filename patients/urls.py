from django.urls import path
from . import views

app_name = 'patients'

urlpatterns = [
    path('register/', views.register_patient, name='register_patient'),
    path('all/', views.all_patients, name='all_patients'),
    path('<int:patient_id>/', views.view_patient, name='view_patient'),
    path('<int:patient_id>/edit/', views.edit_patient, name='edit_patient'),
    path('<int:patient_id>/delete/', views.delete_patient, name='delete_patient'),
]