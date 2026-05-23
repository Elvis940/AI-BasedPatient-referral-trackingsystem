from django import forms
from .models import SymptomAssessment

class SymptomAssessmentForm(forms.ModelForm):
    """Form for CHW to enter current symptoms"""
    
    class Meta:
        model = SymptomAssessment
        fields = [
            'primary_complaint', 'symptom_duration', 'severity_score',
            'associated_symptoms', 'symptom_progression',
            'consciousness', 'breathing_status', 'skin_condition',
            'hydration_status', 'current_temperature', 'current_bp_systolic',
            'current_bp_diastolic', 'current_pulse', 'respiratory_rate',
            'oxygen_saturation'
        ]
        widgets = {
            'primary_complaint': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., Chest pain, High fever, Difficulty breathing'
            }),
            'symptom_duration': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'e.g., 2 hours, 3 days'
            }),
            'severity_score': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 1, 'max': 10,
                'placeholder': '1 (mild) to 10 (severe)'
            }),
            'associated_symptoms': forms.Textarea(attrs={
                'class': 'form-control', 
                'rows': 2,
                'placeholder': 'List any other symptoms (comma-separated)'
            }),
            'symptom_progression': forms.Select(attrs={'class': 'form-control'}),
            'consciousness': forms.Select(attrs={'class': 'form-control'}),
            'breathing_status': forms.Select(attrs={'class': 'form-control'}),
            'skin_condition': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Pale, Sweaty, Rash present'
            }),
            'hydration_status': forms.Select(attrs={'class': 'form-control'}),
            'current_temperature': forms.NumberInput(attrs={
                'class': 'form-control', 
                'step': '0.1',
                'placeholder': '°C'
            }),
            'current_bp_systolic': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Systolic (top number)'
            }),
            'current_bp_diastolic': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Diastolic (bottom number)'
            }),
            'current_pulse': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Beats per minute'
            }),
            'respiratory_rate': forms.NumberInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Breaths per minute'
            }),
            'oxygen_saturation': forms.NumberInput(attrs={
                'class': 'form-control', 
                'min': 0, 'max': 100,
                'placeholder': 'Percentage'
            }),
        }
    
    def clean_severity_score(self):
        score = self.cleaned_data.get('severity_score')
        if score and (score < 1 or score > 10):
            raise forms.ValidationError('Severity score must be between 1 and 10')
        return score