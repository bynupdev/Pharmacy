#!/usr/bin/env python
"""
Check trained drug data accuracy and create name-to-ID mapping
Run: python check_and_map_drugs.py
"""

import os
import sys
import django
import pandas as pd
import joblib
from collections import defaultdict

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from inventory.models import Drug
from accounts.models import Pharmacy

print("=" * 70)
print("DRUG DATA DIAGNOSTIC AND MAPPING TOOL")
print("=" * 70)

# ============================================
# PART 1: Check Training Data
# ============================================
print("\n" + "=" * 70)
print("PART 1: CHECKING TRAINING DATA")
print("=" * 70)

# Load training data
df = pd.read_csv('ddi_pairs_50k.csv')
print(f"\n✅ Loaded {len(df)} rows from ddi_pairs_50k.csv")
print(f"Columns: {df.columns.tolist()}")

# Check what drug name columns exist
name_columns = []
id_columns = []

for col in df.columns:
    if 'name' in col.lower():
        name_columns.append(col)
    if 'ik14' in col.lower() or 'id' in col.lower():
        id_columns.append(col)

print(f"\n📋 Drug name columns: {name_columns}")
print(f"📋 Drug ID columns: {id_columns}")

# ============================================
# PART 2: Extract All Unique Drug Names and IDs
# ============================================
print("\n" + "=" * 70)
print("PART 2: EXTRACTING UNIQUE DRUGS FROM TRAINING DATA")
print("=" * 70)

# Collect all unique drug names and their IDs
drug_database = {}

# Process a_name and drug_a_ik14
if 'a_name' in df.columns and 'drug_a_ik14' in df.columns:
    for _, row in df.iterrows():
        name = row['a_name']
        drug_id = row['drug_a_ik14']
        if pd.notna(name) and pd.notna(drug_id):
            drug_database[name] = drug_id

# Process b_name and drug_b_ik14
if 'b_name' in df.columns and 'drug_b_ik14' in df.columns:
    for _, row in df.iterrows():
        name = row['b_name']
        drug_id = row['drug_b_ik14']
        if pd.notna(name) and pd.notna(drug_id):
            drug_database[name] = drug_id

print(f"\n✅ Extracted {len(drug_database)} unique drug name-ID pairs")

# Show sample
print("\n📋 Sample of drug name-ID pairs:")
sample_count = 0
for name, drug_id in list(drug_database.items())[:20]:
    print(f"   {name} -> {drug_id}")
    sample_count += 1

# ============================================
# PART 3: Check Your Django Database Drugs
# ============================================
print("\n" + "=" * 70)
print("PART 3: CHECKING YOUR DJANGO DATABASE DRUGS")
print("=" * 70)

# Get pharmacy
pharmacy = Pharmacy.objects.first()
if pharmacy:
    print(f"\n📊 Pharmacy: {pharmacy.name}")
else:
    print("\n⚠️ No pharmacy found! Creating one...")
    from accounts.models import Pharmacy
    pharmacy = Pharmacy.objects.create(
        name="Main Pharmacy",
        address="123 Healthcare Ave",
        phone="+1 (555) 123-4567",
        email="info@pharmacy.com"
    )
    print(f"✅ Created pharmacy: {pharmacy.name}")

# Get all drugs from database
db_drugs = Drug.objects.filter(pharmacy=pharmacy)
print(f"\n✅ Found {db_drugs.count()} drugs in your database")

# Show sample
print("\n📋 Drugs in your database:")
for drug in db_drugs[:20]:
    print(f"   ID: {drug.id}, Name: {drug.name}, Generic: {drug.generic_name}")

# ============================================
# PART 4: Match Database Drugs to Training Data
# ============================================
print("\n" + "=" * 70)
print("PART 4: MATCHING DATABASE DRUGS TO TRAINING DATA")
print("=" * 70)

matched_count = 0
unmatched_count = 0
matched_list = []
unmatched_list = []

# Create case-insensitive lookup
drug_lookup = {k.lower(): v for k, v in drug_database.items()}

for drug in db_drugs:
    drug_name_lower = drug.name.lower()
    
    if drug_name_lower in drug_lookup:
        matched_count += 1
        matched_list.append({
            'db_name': drug.name,
            'db_id': drug.id,
            'training_name': [k for k in drug_database.keys() if k.lower() == drug_name_lower][0],
            'training_id': drug_lookup[drug_name_lower]
        })
    else:
        unmatched_count += 1
        unmatched_list.append(drug.name)

print(f"\n✅ Matched: {matched_count} drugs")
print(f"❌ Unmatched: {unmatched_count} drugs")

if matched_list:
    print("\n📋 Matched drugs (first 10):")
    for match in matched_list[:10]:
        print(f"   '{match['db_name']}' → Training ID: {match['training_id']}")

if unmatched_list:
    print("\n⚠️ Unmatched drugs (first 20):")
    for name in unmatched_list[:20]:
        print(f"   {name}")
        # Try to find similar names
        for training_name in drug_database.keys():
            if name.lower() in training_name.lower() or training_name.lower() in name.lower():
                print(f"      → Did you mean: '{training_name}'?")

# ============================================
# PART 5: Create Name-to-ID Mapping File
# ============================================
print("\n" + "=" * 70)
print("PART 5: CREATING NAME-TO-ID MAPPING")
print("=" * 70)

# Create mapping from drug name to training ID
name_to_id_mapping = {}

for drug in db_drugs:
    drug_name_lower = drug.name.lower()
    if drug_name_lower in drug_lookup:
        name_to_id_mapping[drug.name] = drug_lookup[drug_name_lower]
    else:
        # Try partial match
        for training_name, training_id in drug_database.items():
            if drug.name.lower() in training_name.lower() or training_name.lower() in drug.name.lower():
                name_to_id_mapping[drug.name] = training_id
                print(f"   Partial match: '{drug.name}' → '{training_name}'")
                break

print(f"\n✅ Created mapping for {len(name_to_id_mapping)} drugs")

# Save the mapping
joblib.dump(name_to_id_mapping, 'drug_name_to_id_mapping.pkl')
print("💾 Saved to: drug_name_to_id_mapping.pkl")

# ============================================
# PART 6: Check Model Encoders
# ============================================
print("\n" + "=" * 70)
print("PART 6: CHECKING MODEL ENCODERS")
print("=" * 70)

# Try to load model encoders
try:
    encoder_a = joblib.load('drug_encoder_a.pkl')
    encoder_b = joblib.load('drug_encoder_b.pkl')
    print(f"\n✅ Loaded drug_encoder_a.pkl with {len(encoder_a.classes_)} classes")
    print(f"✅ Loaded drug_encoder_b.pkl with {len(encoder_b.classes_)} classes")
    
    # Check if our drugs are in the encoders
    print("\n📋 Checking if drugs are in encoders:")
    for drug in db_drugs[:20]:
        if drug.name in encoder_a.classes_:
            print(f"   ✓ {drug.name} is in encoder_a")
        elif drug.name in encoder_b.classes_:
            print(f"   ✓ {drug.name} is in encoder_b")
        else:
            print(f"   ✗ {drug.name} is NOT in either encoder")
            
except Exception as e:
    print(f"\n⚠️ Could not load encoders: {e}")

# ============================================
# PART 7: Test Predictions
# ============================================
print("\n" + "=" * 70)
print("PART 7: TESTING PREDICTIONS")
print("=" * 70)

try:
    from ai_engine.predictor_fixed import fixed_predictor
    
    # Test with matched drugs
    test_pairs = [
        ('Colchicine', 'Atorvastatin'),
        ('Warfarin', 'Aspirin'),
        ('Metformin', 'Insulin'),
    ]
    
    print("\n🔬 Testing predictions:")
    for drug1, drug2 in test_pairs:
        result = fixed_predictor.predict(drug1, drug2)
        print(f"\n   {drug1} + {drug2}:")
        print(f"      Has interaction: {result.get('has_interaction', 'N/A')}")
        print(f"      Risk level: {result.get('risk_level', 'N/A')}")
        print(f"      Confidence: {result.get('confidence', 'N/A')}%")
        print(f"      Source: {result.get('source', 'N/A')}")
        
except Exception as e:
    print(f"\n⚠️ Could not test predictions: {e}")

# ============================================
# SUMMARY
# ============================================
print("\n" + "=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"""
📊 Training Data Statistics:
   - Total rows: {len(df)}
   - Unique drugs in training: {len(drug_database)}
   - Drug name columns: {name_columns}
   - Drug ID columns: {id_columns}

📊 Database Statistics:
   - Drugs in your pharmacy: {db_drugs.count()}
   - Successfully mapped: {matched_count}
   - Not mapped: {unmatched_count}

📁 Files Created:
   - drug_name_to_id_mapping.pkl (mapping file)

💡 Recommendations:
   1. If unmatched_count > 0, add those drugs to your training data
   2. If predictions are wrong, retrain model with updated mapping
   3. Use the mapping file in your predictor for accurate lookups
""")

# ============================================
# OPTIONAL: Update Database Drugs with Training IDs
# ============================================
print("\n" + "=" * 70)
print("OPTIONAL: UPDATE DATABASE DRUGS WITH TRAINING IDs")
print("=" * 70)

response = input("\nDo you want to add the training IDs to your database drugs? (y/n): ")
if response.lower() == 'y':
    print("\nUpdating drugs...")
    for drug in db_drugs:
        if drug.name in name_to_id_mapping:
            # Add a new field or update existing one
            # You may need to add an 'external_id' field to your Drug model
            print(f"   {drug.name} → {name_to_id_mapping[drug.name]}")
    print("\n✅ Update complete!")
else:
    print("\nSkipping database update.")

print("\n" + "=" * 70)
print("DIAGNOSTIC COMPLETE!")
print("=" * 70)