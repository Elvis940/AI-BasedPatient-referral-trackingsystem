from django.urls import path
from . import views

app_name = 'ai_assessment'

urlpatterns = [
    path('symptom-checker/<int:patient_id>/', views.symptom_checker, name='symptom_checker'),
    path('result/<int:assessment_id>/', views.assessment_result, name='assessment_result'),
    path('history/<int:patient_id>/', views.assessment_history, name='assessment_history'),  # This is the correct name
       path('all/', views.all_assessments, name='all_assessments'),  # Add this
       path('<int:assessment_id>/delete/', views.delete_assessment, name='delete_assessment'),  # Add this
]