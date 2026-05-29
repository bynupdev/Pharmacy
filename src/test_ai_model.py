import joblib
import numpy as np

print("=" * 70)
print("TESTING FIXED MODEL")
print("=" * 70)

# Load fixed model
model = joblib.load('drug_interaction_model_fixed.pkl')
le_a = joblib.load('drug_encoder_a.pkl')
le_b = joblib.load('drug_encoder_b.pkl')
scaler = joblib.load('feature_scaler_fixed.pkl')

# Known high-risk pairs from your data
test_pairs = [
    ('Colchicine', 'Atorvastatin'),
    ('Methimazole', 'Fluconazole'),
    ('Allopurinol', 'Folic acid'),
    ('Spironolactone', 'Atenolol'),
    ('Desloratadine', 'Magnesium cation'),
]

print("\n🔬 Testing known high-risk drug pairs:")
print("-" * 50)

for drug1, drug2 in test_pairs:
    try:
        d1_enc = le_a.transform([drug1])[0]
        d2_enc = le_b.transform([drug2])[0]
        
        features = np.array([[
            d1_enc, d2_enc,
            len(drug1), len(drug2),
            ord(drug1[0]) % 32, ord(drug2[0]) % 32,
            len(drug1.split()), len(drug2.split()),
            1 if drug1 == drug2 else 0,
            d1_enc + d2_enc,
            d1_enc * d2_enc,
            abs(d1_enc - d2_enc)
        ]])
        
        features = scaler.transform(features)
        prob = model.predict_proba(features)[0][1]
        
        risk = "🔴 HIGH" if prob > 0.5 else "🟡 MEDIUM" if prob > 0.3 else "🟢 LOW"
        print(f"\n💊 {drug1} + {drug2}")
        print(f"   Risk: {risk} ({prob*100:.1f}%)")
        
    except Exception as e:
        print(f"\n❌ {drug1} + {drug2}: {e}")

print("\n" + "=" * 70)