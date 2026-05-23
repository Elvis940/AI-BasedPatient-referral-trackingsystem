import json
import random
from datetime import datetime, timedelta

def generate_complete_dataset(total_samples=15000):
    """Generate a comprehensive realistic dataset"""
    
    # Define possible values
    villages = ["Koffa Village", "Zaway Town", "Gbarnga City", "Kpatawee", "Totota", 
                "Salala", "Kokoyah", "Belefanai", "Gboveh", "Panta", "Belle Yellah", 
                "Gbartala", "Gbatala", "Gbondi", "Gonye", "Kpaai", "Kpala", "Maimu"]
    
    districts = ["Gbarnga", "Bong", "Lower Bong", "Upper Bong", "Sanoyea", "Fuamah", "Jorquelleh", "Panta", "Salala", "Suakoko"]
    
    # Define condition-specific symptom patterns
    condition_patterns = {
        "cardiology_emergency": {
            "age_range": (45, 80),
            "symptoms": ["chest pain", "shortness of breath", "palpitations", "sweating", "nausea"],
            "urgency": "emergency",
            "specialist": "cardiology",
            "severity_range": (8, 10),
            "bp_systolic_range": (160, 200),
            "pulse_range": (100, 140),
            "oxygen_range": (85, 95)
        },
        "cardiology_urgent": {
            "age_range": (35, 70),
            "symptoms": ["chest discomfort", "fatigue", "irregular heartbeat", "dizziness"],
            "urgency": "urgent",
            "specialist": "cardiology",
            "severity_range": (5, 7),
            "bp_systolic_range": (140, 160),
            "pulse_range": (85, 110),
            "oxygen_range": (95, 99)
        },
        "pediatrics_emergency": {
            "age_range": (0, 12),
            "symptoms": ["high fever", "seizure", "difficulty breathing", "vomiting", "lethargy"],
            "urgency": "emergency",
            "specialist": "pediatrics",
            "severity_range": (8, 10),
            "temperature_range": (39.0, 41.0),
            "pulse_range": (120, 160),
            "oxygen_range": (90, 96)
        },
        "pediatrics_urgent": {
            "age_range": (0, 12),
            "symptoms": ["fever", "cough", "diarrhea", "ear pain", "rash"],
            "urgency": "urgent",
            "specialist": "pediatrics",
            "severity_range": (5, 7),
            "temperature_range": (38.0, 39.5),
            "pulse_range": (100, 130),
            "oxygen_range": (96, 99)
        },
        "neurology_emergency": {
            "age_range": (40, 80),
            "symptoms": ["severe headache", "confusion", "weakness", "speech difficulty", "loss of consciousness"],
            "urgency": "emergency",
            "specialist": "neurology",
            "severity_range": (8, 10),
            "bp_systolic_range": (170, 210),
            "pulse_range": (90, 120),
            "oxygen_range": (94, 98)
        },
        "neurology_urgent": {
            "age_range": (25, 70),
            "symptoms": ["headache", "numbness", "tingling", "dizziness", "memory problems"],
            "urgency": "urgent",
            "specialist": "neurology",
            "severity_range": (5, 7),
            "bp_systolic_range": (130, 160),
            "pulse_range": (70, 95),
            "oxygen_range": (97, 99)
        },
        "gynecology_emergency": {
            "age_range": (15, 45),
            "symptoms": ["pelvic pain", "vaginal bleeding", "fainting", "dizziness", "pregnancy complications"],
            "urgency": "emergency",
            "specialist": "gynecology",
            "severity_range": (8, 10),
            "bp_systolic_range": (90, 110),
            "pulse_range": (110, 140),
            "oxygen_range": (95, 99)
        },
        "gynecology_urgent": {
            "age_range": (15, 50),
            "symptoms": ["irregular periods", "pelvic discomfort", "discharge", "painful intercourse"],
            "urgency": "urgent",
            "specialist": "gynecology",
            "severity_range": (5, 7),
            "bp_systolic_range": (110, 130),
            "pulse_range": (70, 90),
            "oxygen_range": (98, 100)
        },
        "ophthalmology_urgent": {
            "age_range": (20, 70),
            "symptoms": ["eye pain", "redness", "blurred vision", "light sensitivity", "discharge"],
            "urgency": "urgent",
            "specialist": "ophthalmology",
            "severity_range": (6, 8),
            "bp_systolic_range": (110, 140),
            "pulse_range": (70, 95),
            "oxygen_range": (97, 100)
        },
        "orthopedics_urgent": {
            "age_range": (18, 70),
            "symptoms": ["joint pain", "swelling", "limited motion", "injury", "fracture suspected"],
            "urgency": "urgent",
            "specialist": "orthopedics",
            "severity_range": (6, 8),
            "bp_systolic_range": (110, 145),
            "pulse_range": (80, 105),
            "oxygen_range": (97, 100)
        },
        "general_medicine_non_urgent": {
            "age_range": (18, 70),
            "symptoms": ["fever", "cough", "body aches", "fatigue", "mild diarrhea"],
            "urgency": "non_urgent",
            "specialist": "general_medicine",
            "severity_range": (3, 5),
            "temperature_range": (37.5, 38.5),
            "pulse_range": (70, 100),
            "oxygen_range": (97, 100)
        },
        "psychiatry_emergency": {
            "age_range": (18, 65),
            "symptoms": ["suicidal thoughts", "hallucinations", "aggression", "severe anxiety", "self-harm"],
            "urgency": "emergency",
            "specialist": "psychiatry",
            "severity_range": (9, 10),
            "bp_systolic_range": (110, 145),
            "pulse_range": (90, 120),
            "oxygen_range": (97, 100)
        },
        "psychiatry_urgent": {
            "age_range": (18, 65),
            "symptoms": ["depression", "anxiety", "insomnia", "panic attacks", "mood swings"],
            "urgency": "urgent",
            "specialist": "psychiatry",
            "severity_range": (6, 8),
            "bp_systolic_range": (110, 135),
            "pulse_range": (75, 95),
            "oxygen_range": (98, 100)
        }
    }
    
    # Known conditions list
    known_conditions_list = [
        [], ["hypertension"], ["diabetes"], ["asthma"], 
        ["hypertension", "diabetes"], ["hypertension", "asthma"],
        ["diabetes", "asthma"], ["hypertension", "diabetes", "asthma"],
        ["heart_disease"], ["hypertension", "heart_disease"],
        ["diabetes", "heart_disease"], ["epilepsy"], ["depression"],
        ["anxiety"], ["depression", "anxiety"], ["hiv"], ["tb"]
    ]
    
    samples = []
    sample_id = 1
    
    # Calculate samples per pattern
    patterns_per_type = len(condition_patterns)
    samples_per_pattern = total_samples // patterns_per_type
    
    for pattern_name, pattern in condition_patterns.items():
        for _ in range(samples_per_pattern):
            # Generate age
            age = random.randint(pattern["age_range"][0], pattern["age_range"][1])
            
            # Generate gender based on pattern
            if pattern["specialist"] == "gynecology":
                gender = "F"
            else:
                gender = random.choice(["M", "F"])
            
            # Select primary symptom
            primary_symptom = random.choice(pattern["symptoms"])
            
            # Generate associated symptoms
            num_associated = random.randint(1, 3)
            associated = random.sample(pattern["symptoms"], min(num_associated, len(pattern["symptoms"])))
            if primary_symptom in associated:
                associated.remove(primary_symptom)
            
            # Generate severity
            severity = random.randint(pattern["severity_range"][0], pattern["severity_range"][1])
            
            # Generate duration
            if pattern["urgency"] == "emergency":
                duration_hours = random.randint(1, 12)
            elif pattern["urgency"] == "urgent":
                duration_hours = random.randint(12, 72)
            else:
                duration_hours = random.randint(72, 336)
            
            # Generate vitals
            vitals = {
                "temperature_c": round(random.uniform(36.5, 39.5), 1),
                "bp_systolic": random.randint(110, 150),
                "bp_diastolic": random.randint(70, 90),
                "pulse_rate": random.randint(70, 100),
                "respiratory_rate": random.randint(14, 22),
                "oxygen_saturation": random.randint(95, 100)
            }
            
            # Override with pattern-specific vitals
            if "temperature_range" in pattern:
                vitals["temperature_c"] = round(random.uniform(pattern["temperature_range"][0], pattern["temperature_range"][1]), 1)
            if "bp_systolic_range" in pattern:
                vitals["bp_systolic"] = random.randint(pattern["bp_systolic_range"][0], pattern["bp_systolic_range"][1])
            if "pulse_range" in pattern:
                vitals["pulse_rate"] = random.randint(pattern["pulse_range"][0], pattern["pulse_range"][1])
            if "oxygen_range" in pattern:
                vitals["oxygen_saturation"] = random.randint(pattern["oxygen_range"][0], pattern["oxygen_range"][1])
            
            # Physical exam based on urgency
            if pattern["urgency"] == "emergency":
                consciousness = random.choice(["alert", "confused"])
                breathing = random.choice(["labored", "wheezing"])
            else:
                consciousness = "alert"
                breathing = "normal"
            
            # Generate outcome confidence
            confidence = random.randint(85, 98) if pattern["urgency"] != "non_urgent" else random.randint(70, 85)
            
            # Generate location
            village = random.choice(villages)
            district = random.choice(districts)
            
            # Calculate distance based on village
            distance = round(random.uniform(1, 25), 1)
            
            # Create sample
            sample = {
                "id": sample_id,
                "patient_demographics": {
                    "age": age,
                    "gender": gender,
                    "known_conditions": random.choice(known_conditions_list),
                    "pregnancy_status": "pregnant" if gender == "F" and random.choice([True, False]) and pattern["specialist"] == "gynecology" else "not_pregnant",
                    "location": {
                        "village": village,
                        "district": district,
                        "distance_to_hospital_km": distance
                    }
                },
                "symptoms": {
                    "primary_complaint": primary_symptom,
                    "severity": severity,
                    "duration_hours": duration_hours,
                    "associated_symptoms": associated,
                    "progression": random.choice(["worsening", "same", "improving"]),
                    "triggers": random.sample(["exertion", "stress", "cold", "food", "medication", "none"], random.randint(0, 2))
                },
                "vitals": vitals,
                "physical_exam": {
                    "consciousness": consciousness,
                    "breathing_status": breathing,
                    "skin_condition": random.choice(["normal", "pale", "sweaty", "rash", "warm"]),
                    "hydration_status": random.choice(["normal", "dry_mouth", "sunken_eyes"])
                },
                "medical_history": {
                    "chronic_diseases": random.sample(["hypertension", "diabetes", "asthma", "heart_disease", "epilepsy", "depression"], random.randint(0, 2)),
                    "current_medications": ["medication_a", "medication_b"] if random.choice([True, False]) else [],
                    "allergies": ["penicillin"] if random.choice([True, False]) else [],
                    "previous_surgeries": ["appendectomy"] if random.choice([True, False]) else [],
                    "family_history": random.sample(["heart_disease", "diabetes", "hypertension", "stroke", "cancer"], random.randint(0, 2))
                },
                "outcome": {
                    "urgency": pattern["urgency"],
                    "specialist": pattern["specialist"],
                    "final_diagnosis": f"{primary_symptom.replace(' ', '_')}_{pattern['specialist']}",
                    "treatment": "standard_treatment",
                    "hospital_stay_days": random.randint(0, 7) if pattern["urgency"] != "non_urgent" else 0,
                    "recovered": random.choice([True, False]),
                    "follow_up_required": pattern["urgency"] != "non_urgent",
                    "recommended_action": "ambulance_immediate" if pattern["urgency"] == "emergency" else ("24_hours" if pattern["urgency"] == "urgent" else "1_week"),
                    "confidence": confidence
                }
            }
            
            samples.append(sample)
            sample_id += 1
            
            if sample_id > total_samples:
                break
        
        if sample_id > total_samples:
            break
    
    # Create final dataset
    dataset = {
        "dataset_info": {
            "name": "J.J. Dossen Hospital - Realistic Patient Assessment Dataset",
            "version": "3.0",
            "total_samples": len(samples),
            "created_date": datetime.now().strftime("%Y-%m-%d"),
            "description": "Comprehensive dataset for training urgency prediction and specialist recommendation models"
        },
        "samples": samples[:total_samples]
    }
    
    # Save to file
    with open('ai_assessment/training/realistic_dataset.json', 'w') as f:
        json.dump(dataset, f, indent=2)
    
    print(f"✅ Generated {len(samples[:total_samples])} samples")
    print(f"📊 Dataset saved to ai_assessment/training/realistic_dataset.json")
    
    # Print statistics
    urgency_counts = {}
    specialist_counts = {}
    for sample in samples[:total_samples]:
        urgency = sample["outcome"]["urgency"]
        specialist = sample["outcome"]["specialist"]
        urgency_counts[urgency] = urgency_counts.get(urgency, 0) + 1
        specialist_counts[specialist] = specialist_counts.get(specialist, 0) + 1
    
    print("\n📈 Dataset Statistics:")
    print("-" * 40)
    print("Urgency Distribution:")
    for urgency, count in urgency_counts.items():
        print(f"  {urgency}: {count} ({count/len(samples[:total_samples])*100:.1f}%)")
    
    print("\nSpecialist Distribution:")
    for specialist, count in specialist_counts.items():
        print(f"  {specialist}: {count} ({count/len(samples[:total_samples])*100:.1f}%)")
    
    return dataset

if __name__ == "__main__":
    generate_complete_dataset(15000)