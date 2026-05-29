#!/usr/bin/env python
"""
Import JSON data to Neon database
Run AFTER switching to Neon and running migrations
"""

import os
import sys
import json
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.core import serializers
from django.contrib.auth.models import User
from accounts.models import UserProfile, Pharmacy
from inventory.models import Drug, Batch, Supplier
from patients.models import Patient

print("=" * 70)
print("IMPORTING DATA TO NEON DATABASE")
print("=" * 70)

# Load the exported data
with open('pharmacy_data_export.json', 'r') as f:
    export_data = json.load(f)

# Import in correct order (dependencies first)
print("\n[1/6] Importing Users...")
for obj in export_data['users']:
    user = User(**obj['fields'])
    user.pk = obj['pk']
    user.save()
print(f"   Imported {len(export_data['users'])} users")

print("\n[2/6] Importing Pharmacies...")
for obj in export_data['pharmacies']:
    pharmacy = Pharmacy(**obj['fields'])
    pharmacy.pk = obj['pk']
    pharmacy.save()
print(f"   Imported {len(export_data['pharmacies'])} pharmacies")

print("\n[3/6] Importing User Profiles...")
for obj in export_data['profiles']:
    profile = UserProfile(**obj['fields'])
    profile.pk = obj['pk']
    profile.save()
print(f"   Imported {len(export_data['profiles'])} profiles")

print("\n[4/6] Importing Suppliers...")
for obj in export_data['suppliers']:
    supplier = Supplier(**obj['fields'])
    supplier.pk = obj['pk']
    supplier.save()
print(f"   Imported {len(export_data['suppliers'])} suppliers")

print("\n[5/6] Importing Drugs...")
for obj in export_data['drugs']:
    drug = Drug(**obj['fields'])
    drug.pk = obj['pk']
    drug.save()
print(f"   Imported {len(export_data['drugs'])} drugs")

print("\n[6/6] Importing Batches...")
for obj in export_data['batches']:
    batch = Batch(**obj['fields'])
    batch.pk = obj['pk']
    batch.save()
print(f"   Imported {len(export_data['batches'])} batches")

print("\n[7/7] Importing Patients...")
for obj in export_data['patients']:
    patient = Patient(**obj['fields'])
    patient.pk = obj['pk']
    patient.save()
print(f"   Imported {len(export_data['patients'])} patients")

print("\n" + "=" * 70)
print("IMPORT COMPLETE!")
print("=" * 70)