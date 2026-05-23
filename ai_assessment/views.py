from django.utils import timezone
import joblib
import pandas as pd
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.core.paginator import Paginator
from django.conf import settings
import os
from patients.models import Patient
from .models import SymptomAssessment
from .forms import SymptomAssessmentForm

# Load AI models at startup
MODEL_PATH = os.path.join(settings.BASE_DIR, 'ai_assessment', 'ml_models')

try:
    urgency_model = joblib.load(os.path.join(MODEL_PATH, 'urgency_model.pkl'))
    specialist_model = joblib.load(os.path.join(MODEL_PATH, 'specialist_model.pkl'))
    label_encoders = joblib.load(os.path.join(MODEL_PATH, 'label_encoders.pkl'))
    models_loaded = True
except:
    models_loaded = False
    print("⚠️ AI models not loaded. Run training script first.")


@login_required
def symptom_checker(request, patient_id):
    """Symptom checker page for a specific patient"""
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == 'POST':
        form = SymptomAssessmentForm(request.POST)
        if form.is_valid():
            assessment = form.save(commit=False)
            assessment.patient = patient
            assessment.assessed_by = request.user
            
            # ========== USE RULE-BASED SERVICE FOR URGENCY ==========
            from .services import AIPredictionService
            
            # Prepare symptoms text
            symptoms_text = f"{assessment.primary_complaint}. "
            if assessment.associated_symptoms:
                symptoms_text += f"Associated symptoms: {assessment.associated_symptoms}"
            
            # Prepare vitals dict
            vitals = {
                'temperature_c': float(assessment.current_temperature) if assessment.current_temperature else None,
                'bp_systolic': assessment.current_bp_systolic,
                'bp_diastolic': assessment.current_bp_diastolic,
                'pulse_rate': assessment.current_pulse,
                'respiratory_rate': assessment.respiratory_rate,
                'oxygen_saturation': assessment.oxygen_saturation,
            }
            
            # Calculate urgency using rule-based service
            urgency, confidence, reasons = AIPredictionService.assess_urgency(
                symptoms_text, assessment.severity_score, vitals
            )
            
            # Determine specialist
            specialist, specialist_reason = AIPredictionService.recommend_specialist(
                symptoms_text, patient.age, patient.gender, vitals
            )
            
            # Set AI predictions
            assessment.ai_urgency = urgency
            assessment.ai_specialist = specialist
            assessment.ai_confidence = confidence
            
            # Generate recommendation text
            if urgency == 'emergency':
                assessment.ai_recommendation = f"🚨 EMERGENCY: Patient requires immediate ambulance to J.J. Dossen Hospital. Notify {dict(SymptomAssessment.SPECIALIST_CHOICES).get(specialist, 'appropriate specialist')}. Confidence: {confidence}%"
            elif urgency == 'urgent':
                assessment.ai_recommendation = f"⚠️ URGENT: Refer patient to {dict(SymptomAssessment.SPECIALIST_CHOICES).get(specialist, 'appropriate specialist')} at J.J. Dossen Hospital within 24 hours. Confidence: {confidence}%"
            else:
                assessment.ai_recommendation = f"📋 NON-URGENT: Schedule appointment with {dict(SymptomAssessment.SPECIALIST_CHOICES).get(specialist, 'appropriate specialist')} within 1-2 weeks. Confidence: {confidence}%"
            
            # Generate warning signs and actions
            assessment.warning_signs = "\n".join(reasons[:3])
            assessment.recommended_action = f"Patient requires {urgency} care. Refer to {dict(SymptomAssessment.SPECIALIST_CHOICES).get(specialist, specialist)} department."
            
            assessment.save()
            return redirect('ai_assessment:assessment_result', assessment_id=assessment.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = SymptomAssessmentForm()
    
    # Pre-fill with patient's baseline vitals if available
    initial_data = {}
    if patient.blood_pressure_systolic:
        initial_data['current_bp_systolic'] = patient.blood_pressure_systolic
        initial_data['current_bp_diastolic'] = patient.blood_pressure_diastolic
    if patient.temperature_c:
        initial_data['current_temperature'] = patient.temperature_c
    if patient.pulse_rate:
        initial_data['current_pulse'] = patient.pulse_rate
    
    form = SymptomAssessmentForm(initial=initial_data)
    
    context = {
        'patient': patient,
        'form': form,
        'models_loaded': False  # Using rule-based instead of ML models
    }
    return render(request, 'ai_assessment/symptom_checker.html', context)


@login_required
def assessment_result(request, assessment_id):
    """Display AI assessment result and allow doctor selection"""
    
    assessment = get_object_or_404(SymptomAssessment, id=assessment_id)
    
    # ========== FORCE RECALCULATE URGENCY USING RULE-BASED SERVICE ==========
    # This ensures mild symptoms are correctly classified as NON-URGENT
    from .services import AIPredictionService
    
    # Prepare symptoms text
    symptoms_text = f"{assessment.primary_complaint}. "
    if assessment.associated_symptoms:
        symptoms_text += f"Associated symptoms: {assessment.associated_symptoms}"
    
    # Prepare vitals dict
    vitals = {
        'temperature_c': float(assessment.current_temperature) if assessment.current_temperature else None,
        'bp_systolic': assessment.current_bp_systolic,
        'bp_diastolic': assessment.current_bp_diastolic,
        'pulse_rate': assessment.current_pulse,
        'respiratory_rate': assessment.respiratory_rate,
        'oxygen_saturation': assessment.oxygen_saturation,
    }
    
    # Recalculate urgency using rule-based service (more accurate for mild cases)
    recalculated_urgency, recalculated_confidence, urgency_reasons = AIPredictionService.assess_urgency(
        symptoms_text, assessment.severity_score, vitals
    )
    
    # Update assessment with recalculated values
    assessment.ai_urgency = recalculated_urgency
    assessment.ai_confidence = recalculated_confidence
    assessment.save()
    
    # Map AI specialist to database specialization
    specialist_mapping = {
        'cardiology': 'cardiology',
        'pediatrics': 'pediatrics',
        'ophthalmology': 'ophthalmology',
        'neurology': 'neurology',
        'gynecology': 'gynecology',
        'orthopedics': 'orthopedics',
        'general_medicine': 'general_practice',
        'emergency': 'emergency_medicine',
        'psychiatry': 'psychiatry',
    }
    
    specialist_value = specialist_mapping.get(assessment.ai_specialist, 'general_practice')
    
    # ========== GET AVAILABLE DOCTORS ==========
    from user_management.models import UserProfile
    
    specialist_doctors = UserProfile.objects.filter(
        user_type='doctor',
        status='active',
        specialization=specialist_value
    ).select_related('user')
    
    available_doctors = []
    fallback_doctors = []
    external_referral = None
    
    if specialist_doctors.exists():
        for profile in specialist_doctors:
            available_doctors.append({
                'id': profile.user.id,
                'name': profile.user.get_full_name(),
                'specialization': profile.full_specialization,
                'years_experience': profile.years_of_experience,
                'consultation_fee': float(profile.consultation_fee) if profile.consultation_fee else 0,
                'availability_status': profile.availability_status,
                'office_location': profile.office_location or 'J.J. Dossen Hospital',
                'office_phone': profile.office_phone or profile.phone_number,
                'languages_spoken': profile.languages_spoken or 'English',
                'is_fallback': False,
            })
    else:
        # Get fallback doctors (General Medicine)
        fallback_profiles = UserProfile.objects.filter(
            user_type='doctor',
            status='active',
            specialization__in=['general_practice', 'emergency_medicine']
        ).select_related('user')[:3]
        
        for profile in fallback_profiles:
            fallback_doctors.append({
                'id': profile.user.id,
                'name': profile.user.get_full_name(),
                'specialization': profile.full_specialization,
                'years_experience': profile.years_of_experience,
                'consultation_fee': float(profile.consultation_fee) if profile.consultation_fee else 0,
                'availability_status': profile.availability_status,
                'office_location': profile.office_location or 'J.J. Dossen Hospital',
                'office_phone': profile.office_phone or profile.phone_number,
                'languages_spoken': profile.languages_spoken or 'English',
                'is_fallback': True,
                'fallback_reason': f'No {assessment.get_ai_specialist_display()} available. This doctor can provide initial assessment.'
            })
    
    if request.method == 'POST':
        # CHW confirms assessment and selects doctor
        chw_agreed = request.POST.get('chw_agreed') == 'true'
        assessment.chw_agreed = chw_agreed
        
        if not chw_agreed:
            assessment.chw_override = request.POST.get('chw_override')
            assessment.chw_notes = request.POST.get('chw_notes')
        
        selected_doctor_id = request.POST.get('selected_doctor_id')
        if selected_doctor_id:
            assessment.selected_doctor_id = selected_doctor_id
        
        assessment.completed_at = timezone.now()
        assessment.save()
        
        # Create referral
        from referrals.models import Referral
        referral = Referral.objects.create(
            patient=assessment.patient,
            chw=request.user,
            doctor_id=selected_doctor_id if selected_doctor_id else None,
            assessment=assessment,
            urgency=assessment.ai_urgency,
            specialist=assessment.ai_specialist,
            status='pending_admin',
            notes=assessment.chw_notes
        )
        
        messages.success(request, f'Referral #{referral.referral_code} created successfully! Waiting for admin approval.')
        return redirect('referrals:referral_detail', referral_id=referral.id)
    
    # Prepare display data
    urgency_display = dict(SymptomAssessment.URGENCY_CHOICES).get(assessment.ai_urgency, assessment.ai_urgency)
    specialist_display = dict(SymptomAssessment.SPECIALIST_CHOICES).get(assessment.ai_specialist, assessment.ai_specialist)
    
    urgency_colors = {
        'emergency': '#DC2626',
        'urgent': '#F59E0B',
        'non_urgent': '#10B981'
    }
    
    # Split warning signs and actions
    warning_list = assessment.warning_signs.split('\n') if assessment.warning_signs else []
    action_list = assessment.recommended_action.split('\n') if assessment.recommended_action else []
    
    context = {
        'assessment': assessment,
        'urgency_display': urgency_display,
        'specialist_display': specialist_display,
        'urgency_color': urgency_colors.get(assessment.ai_urgency, '#6B7280'),
        'warning_list': warning_list,
        'action_list': action_list,
        'available_doctors': available_doctors,
        'fallback_doctors': fallback_doctors,
        'external_referral': external_referral,
        'has_specialist': specialist_doctors.exists(),
    }
    return render(request, 'ai_assessment/assessment_result.html', context)


@login_required
def assessment_history(request, patient_id):
    """View all assessments for a patient"""
    
    patient = get_object_or_404(Patient, id=patient_id)
    assessments = patient.assessments.all()
    
    context = {
        'patient': patient,
        'assessments': assessments
    }
    return render(request, 'ai_assessment/history.html', context)


@login_required
def all_assessments(request):
    """View all AI assessments for the current CHW"""
    
    # Get all assessments created by the logged-in CHW
    assessments = SymptomAssessment.objects.filter(assessed_by=request.user).select_related('patient')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        assessments = assessments.filter(ai_urgency=status_filter)
    
    # Search by patient name
    search = request.GET.get('search', '')
    if search:
        assessments = assessments.filter(
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search) |
            Q(patient__patient_id__icontains=search)
        )
    
    # Order by most recent first
    assessments = assessments.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(assessments, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'status_filter': status_filter,
        'total_assessments': assessments.count(),
    }
    return render(request, 'ai_assessment/all_assessments.html', context)


@login_required
def delete_assessment(request, assessment_id):
    """Delete an AI assessment with confirmation"""
    
    assessment = get_object_or_404(SymptomAssessment, id=assessment_id, assessed_by=request.user)
    
    if request.method == 'POST':
        patient_name = assessment.patient.full_name
        assessment.delete()
        messages.success(request, f'Assessment for {patient_name} has been deleted successfully.')
        return redirect('ai_assessment:all_assessments')
    
    return render(request, 'ai_assessment/delete_assessment.html', {'assessment': assessment})


@login_required
def get_doctors_api(request, specialist):
    """API endpoint to get available doctors by specialization"""
    
    from user_management.models import UserProfile
    
    specialist_mapping = {
        'cardiology': 'cardiology',
        'pediatrics': 'pediatrics',
        'ophthalmology': 'ophthalmology',
        'neurology': 'neurology',
        'gynecology': 'gynecology',
        'orthopedics': 'orthopedics',
        'general_medicine': 'general_practice',
        'emergency': 'emergency_medicine',
        'psychiatry': 'psychiatry',
    }
    
    specialist_value = specialist_mapping.get(specialist, 'general_practice')
    
    doctors = UserProfile.objects.filter(
        user_type='doctor',
        status='active',
        specialization=specialist_value
    ).select_related('user')
    
    doctor_list = []
    for doctor in doctors:
        doctor_list.append({
            'id': doctor.user.id,
            'name': doctor.user.get_full_name(),
            'specialization': doctor.full_specialization,
            'available': doctor.availability_status == 'available',
        })
    
    return JsonResponse({'doctors': doctor_list})