import re
from django.contrib.auth.models import User
from user_management.models import UserProfile
from patients.models import Patient
from .models import SymptomAssessment

class AIPredictionService:
    """AI prediction service for symptom assessment"""
    
    # Medical urgency keywords and their weights
    URGENCY_KEYWORDS = {
        'emergency': {
            'keywords': [
                'chest pain', 'heart attack', 'cardiac', 'severe chest pain',
                'difficulty breathing', 'cant breathe', 'shortness of breath',
                'unconscious', 'passed out', 'fainted', 'seizure', 'convulsion',
                'severe bleeding', 'hemorrhage', 'stroke', 'facial droop',
                'slurred speech', 'suicidal', 'self harm', 'anaphylaxis',
                'swelling face', 'pregnancy bleeding', 'pregnant pain'
            ],
            'score': 10
        },
        'urgent': {
            'keywords': [
                'high fever', 'fever 40', 'severe headache', 'migraine',
                'vomiting', 'dehydration', 'fracture', 'broken bone',
                'eye pain', 'vision changes', 'infection', 'wound infection',
                'moderate fever'
            ],
            'score': 5
        },
        'non_urgent': {
            'keywords': [
                'mild fever', 'low grade fever', 'mild cough', 'common cold',
                'runny nose', 'mild pain', 'routine check', 'check up',
                'slight headache', 'mild joint pain', 'fatigue', 'tiredness'
            ],
            'score': 1
        }
    }
    
    # Specialist mapping
    SPECIALIST_KEYWORDS = {
        'cardiology': ['chest pain', 'heart', 'palpitations', 'cardiac', 'bp high', 'hypertension', 'irregular heartbeat'],
        'pediatrics': ['child', 'baby', 'infant', 'pediatric', 'kid', 'toddler'],
        'gynecology': ['pregnancy', 'pregnant', 'menstrual', 'vaginal', 'obstetric', 'women health', 'pelvic pain'],
        'ophthalmology': ['eye pain', 'vision changes', 'blurred vision', 'floaters', 'flashes', 'red eye', 'light sensitivity'],
        'neurology': ['severe headache', 'seizure', 'stroke', 'facial droop', 'numbness', 'tingling', 'confusion', 'memory loss'],
        'orthopedics': ['fracture', 'bone', 'joint pain', 'swelling', 'sprain', 'muscle', 'back pain', 'limited motion'],
        'psychiatry': ['anxiety', 'depression', 'suicidal', 'hallucination', 'mental', 'panic attack', 'insomnia'],
        'general_medicine': ['fever', 'cough', 'cold', 'flu', 'malaise', 'fatigue', 'body aches', 'nausea', 'diarrhea']
    }
    
    @classmethod
    def assess_urgency(cls, symptoms_text, severity_score, vitals):
        """
        Determine urgency level based on symptoms, severity, and vitals
        
        Returns:
            tuple: (urgency_level, confidence_score, reasoning_list)
        """
        text = symptoms_text.lower()
        scores = {'emergency': 0, 'urgent': 0, 'non_urgent': 0}
        reasons = []
        
        # ========== SPECIAL RULE: Mild symptoms with low severity = NON-URGENT ==========
        mild_keywords = ['mild', 'slight', 'minor', 'little', 'low grade', 'routine', 'check up', 'checkup']
        is_mild = any(keyword in text for keyword in mild_keywords)
        
        # Check for non-urgent keywords first (highest priority)
        for urgency, data in cls.URGENCY_KEYWORDS.items():
            if urgency == 'non_urgent':
                for keyword in data['keywords']:
                    if keyword in text:
                        scores['non_urgent'] += 10
                        reasons.append(f"Non-urgent indicator: '{keyword}'")
                        break
        
        # Check for emergency keywords
        for keyword in cls.URGENCY_KEYWORDS['emergency']['keywords']:
            if keyword in text:
                scores['emergency'] += 10
                reasons.append(f"Emergency indicator: '{keyword}'")
                break
        
        # Check for urgent keywords
        for keyword in cls.URGENCY_KEYWORDS['urgent']['keywords']:
            if keyword in text:
                scores['urgent'] += 5
                reasons.append(f"Urgent indicator: '{keyword}'")
                break
        
        # Severity score impact - FIXED for mild cases
        if severity_score >= 8:
            scores['emergency'] += 15
            reasons.append(f"High severity score ({severity_score}/10)")
        elif severity_score >= 5:
            scores['urgent'] += 8
            reasons.append(f"Moderate severity score ({severity_score}/10)")
        else:
            # Low severity (1-4) strongly suggests non-urgent
            scores['non_urgent'] += 15
            reasons.append(f"Low severity score ({severity_score}/10) indicates non-urgent")
        
        # Special override: If it's a mild case with low severity, force NON-URGENT
        if is_mild and severity_score <= 4:
            reasons.append("MILD CASE DETECTED: Low severity mild symptoms - NON-URGENT")
            return 'non_urgent', 85, reasons[:3]
        
        # Vital signs impact
        if vitals:
            temp = vitals.get('temperature_c', 0)
            if temp and temp >= 39.5:
                scores['emergency'] += 10
                reasons.append(f"High temperature ({temp}°C)")
            elif temp and temp >= 38.5:
                scores['urgent'] += 5
                reasons.append(f"Elevated temperature ({temp}°C)")
            elif temp and temp <= 37.5:
                scores['non_urgent'] += 3
                reasons.append(f"Normal temperature ({temp}°C)")
            
            bp_systolic = vitals.get('bp_systolic', 0)
            if bp_systolic and bp_systolic >= 180:
                scores['emergency'] += 10
                reasons.append(f"Very high BP ({bp_systolic})")
            elif bp_systolic and bp_systolic >= 160:
                scores['urgent'] += 5
                reasons.append(f"High BP ({bp_systolic})")
            elif bp_systolic and 100 <= bp_systolic <= 130:
                scores['non_urgent'] += 3
                reasons.append(f"Normal BP ({bp_systolic})")
            
            oxygen = vitals.get('oxygen_saturation', 0)
            if oxygen and oxygen <= 90:
                scores['emergency'] += 15
                reasons.append(f"Low oxygen ({oxygen}%)")
            elif oxygen and oxygen <= 94:
                scores['urgent'] += 5
                reasons.append(f"Low oxygen ({oxygen}%)")
            elif oxygen and oxygen >= 97:
                scores['non_urgent'] += 3
                reasons.append(f"Normal oxygen ({oxygen}%)")
            
            pulse = vitals.get('pulse_rate', 0)
            if pulse and pulse >= 130:
                scores['emergency'] += 8
                reasons.append(f"Very high pulse ({pulse} bpm)")
            elif pulse and pulse >= 110:
                scores['urgent'] += 4
                reasons.append(f"High pulse ({pulse} bpm)")
            elif pulse and 60 <= pulse <= 90:
                scores['non_urgent'] += 2
                reasons.append(f"Normal pulse ({pulse} bpm)")
        
        # Determine final urgency
        # Emergency override - if any emergency keyword found, it's emergency
        if scores['emergency'] >= 10:
            confidence = min(95, 70 + scores['emergency'])
            return 'emergency', confidence, reasons[:3]
        
        # Urgent check
        if scores['urgent'] >= 8:
            confidence = min(90, 65 + scores['urgent'])
            return 'urgent', confidence, reasons[:3]
        
        # Default to non-urgent
        confidence = min(85, 60 + scores['non_urgent'])
        return 'non_urgent', max(confidence, 65), reasons[:3]
    
    @classmethod
    def recommend_specialist(cls, symptoms_text, patient_age, patient_gender, vitals):
        """
        Recommend specialist based on symptoms and patient data
        
        Returns:
            tuple: (specialist, reasoning)
        """
        text = symptoms_text.lower()
        scores = {}
        
        # Check keyword matches
        for specialist, keywords in cls.SPECIALIST_KEYWORDS.items():
            score = 0
            for keyword in keywords:
                if keyword in text:
                    score += 1
            if score > 0:
                scores[specialist] = score
        
        # Age-based adjustments
        if patient_age < 12:
            scores['pediatrics'] = scores.get('pediatrics', 0) + 5
            scores['general_medicine'] = scores.get('general_medicine', 0) - 2
        
        # Gender-based adjustments
        if patient_gender == 'F':
            if 'pregnancy' in text or 'pregnant' in text:
                scores['gynecology'] = scores.get('gynecology', 0) + 8
        
        # Vital-based adjustments
        if vitals:
            bp = vitals.get('bp_systolic', 0)
            if bp and bp >= 140:
                scores['cardiology'] = scores.get('cardiology', 0) + 3
            
            temp = vitals.get('temperature_c', 0)
            if temp and temp >= 38.5:
                scores['general_medicine'] = scores.get('general_medicine', 0) + 2
        
        # Mild symptoms default to general medicine
        if 'mild' in text or 'routine' in text or 'check up' in text:
            scores['general_medicine'] = scores.get('general_medicine', 0) + 5
        
        # Get top specialist
        if scores:
            top_specialist = max(scores, key=scores.get)
            top_score = scores[top_specialist]
            
            # Don't recommend specialist with very low score
            if top_score >= 1:
                return top_specialist, f"Symptoms match {top_specialist} pattern"
        
        return 'general_medicine', "General symptoms - general medicine consult recommended"
    
    @classmethod
    def calculate_confidence(cls, urgency_score, max_possible=100):
        """Calculate confidence percentage"""
        confidence = min(98, int((urgency_score / max_possible) * 100))
        return max(50, confidence)
    
    @classmethod
    def generate_recommendation_text(cls, urgency, specialist, confidence):
        """Generate human-readable recommendation text"""
        
        specialist_display = dict(SymptomAssessment.SPECIALIST_CHOICES).get(specialist, specialist)
        
        if urgency == 'emergency':
            return f"🚨 EMERGENCY: Patient requires immediate ambulance to J.J. Dossen Hospital. Notify {specialist_display}. Confidence: {confidence}%"
        elif urgency == 'urgent':
            return f"⚠️ URGENT: Refer patient to {specialist_display} at J.J. Dossen Hospital within 24 hours. Confidence: {confidence}%"
        else:
            return f"📋 NON-URGENT: Schedule appointment with {specialist_display} within 1-2 weeks. Confidence: {confidence}%"