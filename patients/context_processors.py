from .models import Patient

def patient_count(request):
    """Add patient count to all templates"""
    if request.user.is_authenticated:
        # For CHW users, count their registered patients
        if hasattr(request.user, 'profile') and request.user.profile.user_type == 'chw':
            count = Patient.objects.filter(registered_by=request.user).count()
        else:
            count = Patient.objects.count()
        return {'total_patients_count': count}
    return {'total_patients_count': 0}