import pandas as pd
import numpy as np
import os
import joblib
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix, roc_auc_score
import warnings
warnings.filterwarnings('ignore')

print("=" * 60)
print("DRUG INTERACTION MODEL - WITH DRUG NAME MAPPING")
print("=" * 60)

# Load the dataset
print("\n📊 Loading drug interaction data...")
df = pd.read_csv('ddi_pairs_50k.csv')
print(f"✅ Loaded {len(df)} drug pairs")

# Create binary labels (0 = Low risk, 1 = High risk)
print("\n🔍 Creating binary interaction labels...")

signal_col = 'faers_prr_max_strict'
df[signal_col] = df[signal_col].fillna(0)

# Create binary label: High risk if PRR > 2
df['is_high_risk'] = (df[signal_col] > 2).astype(int)

print(f"\n📊 Label Distribution:")
risk_counts = df['is_high_risk'].value_counts()
print(f"   Low Risk (0): {risk_counts.get(0, 0)} pairs ({risk_counts.get(0, 0)/len(df)*100:.1f}%)")
print(f"   High Risk (1): {risk_counts.get(1, 0)} pairs ({risk_counts.get(1, 0)/len(df)*100:.1f}%)")

# Create drug name to ID mapping
print("\n🔢 Creating drug name to ID mapping...")

# Use the coded IDs (these are what the model actually learned)
df['drug_a_id'] = df['drug_a_ik14'].fillna('unknown').astype(str)
df['drug_b_id'] = df['drug_b_ik14'].fillna('unknown').astype(str)

# Also store the readable names for reference
df['drug_a_name'] = df['a_name'].fillna('unknown').astype(str)
df['drug_b_name'] = df['b_name'].fillna('unknown').astype(str)

# Create mapping from drug name to ID
drug_name_to_id = {}
for idx, row in df.iterrows():
    if row['drug_a_name'] != 'unknown':
        drug_name_to_id[row['drug_a_name'].upper()] = row['drug_a_id']
    if row['drug_b_name'] != 'unknown':
        drug_name_to_id[row['drug_b_name'].upper()] = row['drug_b_id']

print(f"📊 Created mapping for {len(drug_name_to_id)} unique drug names")

# Encode drug IDs
le_drug1 = LabelEncoder()
le_drug2 = LabelEncoder()

df['drug1_encoded'] = le_drug1.fit_transform(df['drug_a_id'])
df['drug2_encoded'] = le_drug2.fit_transform(df['drug_b_id'])

# Create features
feature_columns = ['drug1_encoded', 'drug2_encoded']

# Drug ID lengths (as proxy for drug complexity)
df['drug1_len'] = df['drug_a_id'].str.len()
df['drug2_len'] = df['drug_b_id'].str.len()
feature_columns.extend(['drug1_len', 'drug2_len'])

# First character of ID
df['drug1_first'] = df['drug_a_id'].str[0].apply(lambda x: ord(x) % 32 if x else 0)
df['drug2_first'] = df['drug_b_id'].str[0].apply(lambda x: ord(x) % 32 if x else 0)
feature_columns.extend(['drug1_first', 'drug2_first'])

# Whether same drug
df['is_same'] = (df['drug_a_id'] == df['drug_b_id']).astype(int)
feature_columns.append('is_same')

# Interaction features
df['drug_sum'] = df['drug1_encoded'] + df['drug2_encoded']
df['drug_product'] = df['drug1_encoded'] * df['drug2_encoded']
df['drug_diff'] = abs(df['drug1_encoded'] - df['drug2_encoded'])
feature_columns.extend(['drug_sum', 'drug_product', 'drug_diff'])

# Add PRR as a feature (but be careful with leakage)
# We'll use log-transformed PRR to reduce influence
df['log_prr'] = np.log1p(df[signal_col].fillna(0))
feature_columns.append('log_prr')

X = df[feature_columns].values
y = df['is_high_risk'].values

print(f"📊 Feature matrix shape: {X.shape}")

# Scale features
scaler = StandardScaler()
X = scaler.fit_transform(X)

# Split data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

print(f"\n📊 Training set: {len(X_train)} samples")

# Train with balanced class weights
from sklearn.utils.class_weight import compute_class_weight
class_weights = compute_class_weight('balanced', classes=np.unique(y_train), y=y_train)
weight_dict = {0: class_weights[0], 1: class_weights[1]}

print(f"⚖️ Class weights: Low Risk: {weight_dict[0]:.2f}, High Risk: {weight_dict[1]:.2f}")

# Train model with optimized parameters
model = RandomForestClassifier(
    n_estimators=150,
    max_depth=12,
    min_samples_split=8,
    min_samples_leaf=3,
    class_weight=weight_dict,
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

# Save all model files
print("\n💾 Saving model files...")
joblib.dump(model, 'drug_interaction_model.pkl')
joblib.dump(le_drug1, 'drug_encoder_1.pkl')
joblib.dump(le_drug2, 'drug_encoder_2.pkl')
joblib.dump(scaler, 'feature_scaler.pkl')
joblib.dump(feature_columns, 'feature_columns.pkl')
joblib.dump(drug_name_to_id, 'drug_name_to_id_mapping.pkl')

# Save label info
label_info = {
    '0': 'low_risk',
    '1': 'high_risk',
    'threshold': 0.4  # Lower threshold to catch more high-risk cases
}
joblib.dump(label_info, 'label_info.pkl')

model_size = os.path.getsize('drug_interaction_model.pkl') / (1024 * 1024)
print(f"\n📦 Model file size: {model_size:.2f} MB")
print(f"📁 Files saved in: {os.getcwd()}")

print("\n" + "=" * 60)
print("🎉 TRAINING COMPLETE!")
print("=" * 60)

# Test with actual IDs from the dataset
print("\n🔬 Testing with known drug pairs from dataset:")

# Get some actual high-risk examples from the data
high_risk_samples = df[df['is_high_risk'] == 1].head(5)
low_risk_samples = df[df['is_high_risk'] == 0].head(5)

print("\nHigh Risk Predictions:")
for idx, row in high_risk_samples.iterrows():
    drug1 = row['drug_a_name']
    drug2 = row['drug_b_name']
    features = X_test[np.where((X_test == row['drug1_encoded']).all(axis=1))[0]] if len(np.where((X_test == row['drug1_encoded']).all(axis=1))[0]) > 0 else None
    
    if features is not None and len(features) > 0:
        prob = model.predict_proba(features[0:1])[0][1]
        print(f"   {drug1} + {drug2}: High Risk Confidence: {prob*100:.1f}%")

print("\n" + "=" * 60)
print("DJANGO INTEGRATION CODE")
print("=" * 60)