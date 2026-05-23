import json
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import joblib
import os

print("📂 Loading realistic dataset...")
with open('ai_assessment/training/realistic_dataset.json', 'r') as f:
    data = json.load(f)

print(f"✅ Loaded {len(data['samples'])} samples")

# Convert to DataFrame
records = []
for sample in data['samples']:
    record = {
        'age': sample['patient_demographics']['age'],
        'gender': sample['patient_demographics']['gender'],
        'known_conditions_count': len(sample['patient_demographics']['known_conditions']),
        'has_hypertension': 1 if 'hypertension' in sample['patient_demographics']['known_conditions'] else 0,
        'has_diabetes': 1 if 'diabetes' in sample['patient_demographics']['known_conditions'] else 0,
        'has_asthma': 1 if 'asthma' in sample['patient_demographics']['known_conditions'] else 0,
        'is_pregnant': 1 if sample['patient_demographics']['pregnancy_status'] == 'pregnant' else 0,
        'severity_score': sample['symptoms']['severity'],
        'symptom_duration_hours': sample['symptoms']['duration_hours'],
        'temperature': sample['vitals']['temperature_c'],
        'bp_systolic': sample['vitals']['bp_systolic'],
        'pulse_rate': sample['vitals']['pulse_rate'],
        'respiratory_rate': sample['vitals']['respiratory_rate'],
        'oxygen_saturation': sample['vitals']['oxygen_saturation'],
        'consciousness': sample['physical_exam']['consciousness'],
        'breathing_status': sample['physical_exam']['breathing_status'],
        'urgency': sample['outcome']['urgency'],
        'specialist': sample['outcome']['specialist']
    }
    records.append(record)

df = pd.DataFrame(records)
print(f"📊 DataFrame shape: {df.shape}")

# Encode categorical variables
label_encoders = {}
categorical_cols = ['gender', 'consciousness', 'breathing_status']

for col in categorical_cols:
    le = LabelEncoder()
    df[col + '_encoded'] = le.fit_transform(df[col])
    label_encoders[col] = le

# Prepare features
feature_cols = ['age', 'gender_encoded', 'known_conditions_count', 'has_hypertension', 
                'has_diabetes', 'has_asthma', 'is_pregnant', 'severity_score', 
                'symptom_duration_hours', 'temperature', 'bp_systolic', 'pulse_rate',
                'respiratory_rate', 'oxygen_saturation', 'consciousness_encoded', 
                'breathing_status_encoded']

X = df[feature_cols]
y_urgency = df['urgency']
y_specialist = df['specialist']

print(f"\n📈 Dataset Statistics:")
print(f"  Total samples: {len(df)}")
print(f"  Urgency distribution:")
print(df['urgency'].value_counts())
print(f"\n  Specialist distribution:")
print(df['specialist'].value_counts())

# Train-test split
X_train, X_test, y_train, y_test = train_test_split(X, y_urgency, test_size=0.2, random_state=42, stratify=y_urgency)
X_train_s, X_test_s, y_train_s, y_test_s = train_test_split(X, y_specialist, test_size=0.2, random_state=42, stratify=y_specialist)

print(f"\n🔧 Training on {len(X_train)} samples, testing on {len(X_test)} samples")

# Train urgency model
print("\n🚀 Training Urgency Model...")
urgency_model = RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42)
urgency_model.fit(X_train, y_train)

# Evaluate urgency model
y_pred = urgency_model.predict(X_test)
accuracy = accuracy_score(y_test, y_pred)
print(f"\n✅ Urgency Model Accuracy: {accuracy:.2%}")
print(classification_report(y_test, y_pred))

# Train specialist model
print("\n🚀 Training Specialist Model...")
specialist_model = RandomForestClassifier(n_estimators=200, max_depth=15, random_state=42)
specialist_model.fit(X_train_s, y_train_s)

# Evaluate specialist model
y_pred_s = specialist_model.predict(X_test_s)
accuracy_s = accuracy_score(y_test_s, y_pred_s)
print(f"\n✅ Specialist Model Accuracy: {accuracy_s:.2%}")
print(classification_report(y_test_s, y_pred_s))

# Save models
os.makedirs('ai_assessment/ml_models', exist_ok=True)
joblib.dump(urgency_model, 'ai_assessment/ml_models/urgency_model.pkl')
joblib.dump(specialist_model, 'ai_assessment/ml_models/specialist_model.pkl')
joblib.dump(label_encoders, 'ai_assessment/ml_models/label_encoders.pkl')

print("\n✅ Models saved successfully to ai_assessment/ml_models/")