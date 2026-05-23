from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Patient
from .forms import PatientRegistrationForm
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

@login_required
def register_patient(request):
    """Register a new patient"""
    
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST)
        if form.is_valid():
            patient = form.save(commit=False)
            patient.registered_by = request.user
            patient.save()
            
            messages.success(request, f'Patient {patient.full_name} registered successfully! Patient ID: {patient.patient_id}')
            return redirect('patients:view_patient', patient_id=patient.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientRegistrationForm()
    
    return render(request, 'chw/patients/register.html', {'form': form})

@login_required
def all_patients(request):
    """View all patients with search and filters"""
    
    search = request.GET.get('search', '')
    village = request.GET.get('village', '')
    
    patients = Patient.objects.all()
    
    if search:
        patients = patients.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(patient_id__icontains=search) |
            Q(phone_number__icontains=search)
        )
    
    if village:
        patients = patients.filter(village__icontains=village)
    
    paginator = Paginator(patients, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get unique villages for filter
    villages = Patient.objects.values_list('village', flat=True).distinct()
    
    context = {
        'page_obj': page_obj,
        'search': search,
        'village_filter': village,
        'villages': villages,
        'total_patients': Patient.objects.count(),
    }
    
    return render(request, 'chw/patients/all_patients.html', context)

@login_required
def view_patient(request, patient_id):
    """View patient details"""
    
    patient = get_object_or_404(Patient, id=patient_id)
    return render(request, 'chw/patients/view_patient.html', {'patient': patient})

@login_required
def edit_patient(request, patient_id):
    """Edit patient information"""
    
    patient = get_object_or_404(Patient, id=patient_id)
    
    if request.method == 'POST':
        form = PatientRegistrationForm(request.POST, instance=patient)
        if form.is_valid():
            form.save()
            messages.success(request, f'Patient {patient.full_name} updated successfully!')
            return redirect('patients:view_patient', patient_id=patient.id)
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PatientRegistrationForm(instance=patient)
    
    return render(request, 'chw/patients/edit_patient.html', {'form': form, 'patient': patient})

@login_required
@require_http_methods(["POST"])
def delete_patient(request, patient_id):
    """Delete a patient with AJAX support"""
    
    try:
        patient = get_object_or_404(Patient, id=patient_id)
        patient_name = patient.full_name
        patient.delete()
        
        # Check if it's an AJAX request
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': f'Patient {patient_name} has been deleted successfully.'
            })
        else:
            messages.success(request, f'Patient {patient_name} has been deleted successfully.')
            return redirect('patients:all_patients')
            
    except Exception as e:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
        else:
            messages.error(request, f'Error deleting patient: {str(e)}')
            return redirect('patients:all_patients')