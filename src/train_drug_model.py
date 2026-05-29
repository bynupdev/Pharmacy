"""
Retrain model WITHOUT using PRR as a feature
This prevents data leakage and creates a real predictive model
"""

import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("RETRAINING MODEL - WITHOUT PRR AS FEATURE")
print("=" * 70)

# Load data
print("\n📊 Loading data...")
df = pd.read_csv('ddi_pairs_50k.csv')
print(f"✅ Loaded {len(df)} rows")

# Create labels from PRR (but DON'T use PRR as feature)
signal_col = 'faers_prr_max_strict'
df[signal_col] = df[signal_col].fillna(0)

# Create binary label: 1 = high risk (PRR > 5), 0 = low risk (PRR <= 5)
df['is_high_risk'] = (df[signal_col] > 5).astype(int)

print(f"\n📊 Label distribution:")
print(f"   Low Risk (0): {(df['is_high_risk']==0).sum()} ({(df['is_high_risk']==0).sum()/len(df)*100:.1f}%)")
print(f"   High Risk (1): {(df['is_high_risk']==1).sum()} ({(df['is_high_risk']==1).sum()/len(df)*100:.1f}%)")

# Use drug names as features
df['a_name'] = df['a_name'].fillna('unknown').astype(str)
df['b_name'] = df['b_name'].fillna('unknown').astype(str)

# Combine drug names to create features
print("\n🔢 Creating features from drug names...")

# Encode drug names
le_a = LabelEncoder()
le_b = LabelEncoder()

df['drug_a_encoded'] = le_a.fit_transform(df['a_name'])
df['drug_b_encoded'] = le_b.fit_transform(df['b_name'])

# Create features (NO PRR or other signal columns!)
feature_columns = ['drug_a_encoded', 'drug_b_encoded']

# Add drug name length
df['drug_a_len'] = df['a_name'].str.len()
df['drug_b_len'] = df['b_name'].str.len()
feature_columns.extend(['drug_a_len', 'drug_b_len'])

# Add first letter as number
df['drug_a_first'] = df['a_name'].str[0].apply(lambda x: ord(x) % 32 if x and len(x) > 0 else 0)
df['drug_b_first'] = df['b_name'].str[0].apply(lambda x: ord(x) % 32 if x and len(x) > 0 else 0)
feature_columns.extend(['drug_a_first', 'drug_b_first'])

# Add word count
df['drug_a_words'] = df['a_name'].str.split().str.len()
df['drug_b_words'] = df['b_name'].str.split().str.len()
feature_columns.extend(['drug_a_words', 'drug_b_words'])

# Add whether same drug
df['is_same'] = (df['a_name'] == df['b_name']).astype(int)
feature_columns.append('is_same')

# Add interaction features
df['drug_sum'] = df['drug_a_encoded'] + df['drug_b_encoded']
df['drug_product'] = df['drug_a_encoded'] * df['drug_b_encoded']
df['drug_diff'] = abs(df['drug_a_encoded'] - df['drug_b_encoded'])
feature_columns.extend(['drug_sum', 'drug_product', 'drug_diff'])

X = df[feature_columns].values
y = df['is_high_risk'].values

print(f"📊 Feature matrix: {X.shape}")
print(f"📊 Features: {feature_columns}")

# Scale features
scaler = StandardScaler()
X = scaler.fit_transform(X)

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n📊 Training set: {len(X_train)} samples")

# Train with class weights to handle imbalance
from sklearn.utils.class_weight import compute_class_weight
classes = np.unique(y_train)
weights = compute_class_weight('balanced', classes=classes, y=y_train)
class_weight_dict = {cls: weight for cls, weight in zip(classes, weights)}

print(f"⚖️ Class weights: Low Risk: {class_weight_dict.get(0, 1):.2f}, High Risk: {class_weight_dict.get(1, 1):.2f}")

# Train model
print("\n🚀 Training Random Forest...")
model = RandomForestClassifier(
    n_estimators=200,
    max_depth=15,
    min_samples_split=10,
    min_samples_leaf=5,
    class_weight=class_weight_dict,
    random_state=42,
    n_jobs=-1
)

model.fit(X_train, y_train)

# Evaluate
y_pred = model.predict(X_test)
y_pred_proba = model.predict_proba(X_test)[:, 1]

accuracy = accuracy_score(y_test, y_pred)
auc = roc_auc_score(y_test, y_pred_proba)

print(f"\n✅ Model trained!")
print(f"📈 Test Accuracy: {accuracy:.4f} ({accuracy*100:.1f}%)")
print(f"📈 AUC Score: {auc:.4f}")

print(f"\n📋 Classification Report:")
print(classification_report(y_test, y_pred, target_names=['Low Risk', 'High Risk']))

# Feature importance
print(f"\n🔍 Top 10 Most Important Features:")
feature_importance = pd.DataFrame({
    'feature': feature_columns,
    'importance': model.feature_importances_
}).sort_values('importance', ascending=False)
print(feature_importance.head(10).to_string(index=False))

# Save models
print("\n💾 Saving models...")
joblib.dump(model, 'drug_interaction_model_fixed.pkl')
joblib.dump(le_a, 'drug_encoder_a.pkl')
joblib.dump(le_b, 'drug_encoder_b.pkl')
joblib.dump(scaler, 'feature_scaler_fixed.pkl')
joblib.dump(feature_columns, 'feature_columns_fixed.pkl')
joblib.dump(class_weight_dict, 'class_weights.pkl')

# Save drug name mappings for reference
drug_names = dict(zip(le_a.classes_, range(len(le_a.classes_))))
joblib.dump(drug_names, 'drug_name_mapping.pkl')

print(f"\n📦 Model size: {os.path.getsize('drug_interaction_model_fixed.pkl') / 1024:.1f} KB")
print("\n✅ Retraining complete! Model saved with '_fixed' suffix.")

# Test with known high-risk pairs
print("\n" + "=" * 70)
print("🔬 TESTING WITH KNOWN HIGH-RISK PAIRS")
print("=" * 70)

test_pairs = [
    ('Colchicine', 'Atorvastatin'),
    ('Methimazole', 'Fluconazole'),
    ('Allopurinol', 'Folic acid'),
    ('Spironolactone', 'Atenolol'),
]

for drug1, drug2 in test_pairs:
    try:
        d1_enc = le_a.transform([drug1])[0] if drug1 in le_a.classes_ else -1
        d2_enc = le_b.transform([drug2])[0] if drug2 in le_b.classes_ else -1
        
        features = np.array([[
            d1_enc, d2_enc,
            len(drug1), len(drug2),
            ord(drug1[0]) % 32 if drug1 else 0, ord(drug2[0]) % 32 if drug2 else 0,
            len(drug1.split()), len(drug2.split()),
            1 if drug1 == drug2 else 0,
            d1_enc + d2_enc,
            d1_enc * d2_enc,
            abs(d1_enc - d2_enc)
        ]])
        
        features = scaler.transform(features)
        prob = model.predict_proba(features)[0][1]
        
        print(f"\n💊 {drug1} + {drug2}")
        print(f"   High Risk Probability: {prob*100:.1f}%")
        if prob > 0.5:
            print(f"   🔴 HIGH RISK - Recommend verification")
        else:
            print(f"   🟢 LOW RISK")
            
    except Exception as e:
        print(f"\n⚠️ {drug1} + {drug2}: {str(e)[:50]}")