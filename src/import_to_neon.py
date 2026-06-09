#!/usr/bin/env python
"""
Clear all patients from all pharmacies
Run: python clear_all_patients.py
"""

import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from patients.models import Patient
from prescriptions.models import Prescription, PrescriptionItem
from sales.models import Sale, SaleItem

print("=" * 50)
print("CLEARING ALL PATIENTS")
print("=" * 50)

# Count before deletion
total_patients = Patient.objects.count()
print(f"\nPatients before deletion: {total_patients}")

# First delete related records (prescriptions, sales) that reference patients
print("\nDeleting related records...")

# Delete PrescriptionItems linked to prescriptions that have patients
prescription_items_deleted = PrescriptionItem.objects.filter(prescription__patient__isnull=False).count()
PrescriptionItem.objects.filter(prescription__patient__isnull=False).delete()
print(f"  Deleted {prescription_items_deleted} prescription items")

# Delete Prescriptions that have patients
prescriptions_deleted = Prescription.objects.filter(patient__isnull=False).count()
Prescription.objects.filter(patient__isnull=False).delete()
print(f"  Deleted {prescriptions_deleted} prescriptions")

# Delete Sales (no direct patient link, but to be safe)
sales_deleted = Sale.objects.count()
Sale.objects.all().delete()
print(f"  Deleted {sales_deleted} sales")

# Finally delete all patients
patients_deleted = Patient.objects.all().delete()[0]
print(f"\nPatients deleted: {patients_deleted}")

print("\n" + "=" * 50)
print("COMPLETE!")
print("=" * 50)