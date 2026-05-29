#!/usr/bin/env python
"""
Complete Database Setup Script - Clean Version (No Emojis)
Creates admin account, drugs, batches, suppliers, and stock data
Run: python setup_database_clean.py
"""

import os
import sys
import django
import pandas as pd
from datetime import datetime, timedelta
import random
import logging

# Suppress warnings
logging.disable(logging.CRITICAL)

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'src.settings')
django.setup()

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from accounts.models import UserProfile, Pharmacy
from inventory.models import Drug, Batch, Supplier
from patients.models import Patient
from prescriptions.models import Prescription, PrescriptionItem
from sales.models import Sale, SaleItem

print("=" * 70)
print("PHARMACY DATABASE SETUP")
print("=" * 70)

# ============================================
# STEP 1: Create Pharmacy
# ============================================
print("\n[1/8] Creating Pharmacy...")

pharmacy, created = Pharmacy.objects.get_or_create(
    name="Demo Pharmacy",
    defaults={
        'address': "123 Healthcare Ave, Medical District",
        'phone': "+1 (555) 123-4567",
        'email': "info@demopharmacy.com"
    }
)
print(f"   OK: Pharmacy: {pharmacy.name}")

# ============================================
# STEP 2: Create Admin User
# ============================================
print("\n[2/8] Creating Admin User...")

admin_user, created = User.objects.get_or_create(
    username='admin',
    defaults={
        'first_name': 'System',
        'last_name': 'Administrator',
        'email': 'admin@pharmacy.com',
        'password': make_password('admin123'),
        'is_staff': True,
        'is_superuser': True,
        'is_active': True
    }
)

if created:
    print(f"   OK: Admin user created: username='admin', password='admin123'")
else:
    print(f"   OK: Admin user already exists")

# Create/update user profile
profile, profile_created = UserProfile.objects.get_or_create(
    user=admin_user,
    defaults={
        'role': 'admin',
        'phone_number': '+1 (555) 000-0001',
        'license_number': 'PHARM-ADMIN-001',
        'pharmacy': pharmacy
    }
)
if not profile.pharmacy:
    profile.pharmacy = pharmacy
    profile.save()
print(f"   OK: Admin profile linked to {pharmacy.name}")

# ============================================
# STEP 3: Create Suppliers
# ============================================
print("\n[3/8] Creating Suppliers...")

suppliers_data = [
    {'name': 'MedSource International', 'contact': 'John Smith', 'email': 'orders@medsource.com', 'phone': '+1 (800) 111-2222'},
    {'name': 'PharmaDirect', 'contact': 'Sarah Johnson', 'email': 'sales@pharmadirect.com', 'phone': '+1 (800) 333-4444'},
    {'name': 'HealthSupply Co.', 'contact': 'Mike Brown', 'email': 'info@healthsupply.com', 'phone': '+1 (800) 555-6666'},
    {'name': 'Global Meds', 'contact': 'Lisa Wong', 'email': 'orders@globalmeds.com', 'phone': '+1 (800) 777-8888'},
]

suppliers = []
for sup_data in suppliers_data:
    supplier, created = Supplier.objects.get_or_create(
        name=sup_data['name'],
        defaults={
            'contact_person': sup_data['contact'],
            'email': sup_data['email'],
            'phone': sup_data['phone'],
            'address': '123 Supply Chain Blvd',
            'pharmacy': pharmacy
        }
    )
    suppliers.append(supplier)
    print(f"   OK: {supplier.name}")

# ============================================
# STEP 4: Create Drugs from CSV Data
# ============================================
print("\n[4/8] Creating Drugs from data...")

# Drug data: Name, Generic Name, Form, Strength, Manufacturer, Requires Prescription
drugs_data = [
    ("Colchicine", "Colchicine", "tablet", "0.6mg", "Various", True),
    ("Atorvastatin", "Atorvastatin Calcium", "tablet", "20mg", "Pfizer", True),
    ("Methimazole", "Methimazole", "tablet", "5mg", "Various", True),
    ("Fluconazole", "Fluconazole", "capsule", "150mg", "Pfizer", True),
    ("Allopurinol", "Allopurinol", "tablet", "100mg", "Various", True),
    ("Folic acid", "Folic Acid", "tablet", "1mg", "Various", False),
    ("Desloratadine", "Desloratadine", "tablet", "5mg", "Schering-Plough", True),
    ("Magnesium cation", "Magnesium", "capsule", "250mg", "Various", False),
    ("Spironolactone", "Spironolactone", "tablet", "25mg", "Various", True),
    ("Atenolol", "Atenolol", "tablet", "50mg", "AstraZeneca", True),
    ("Lorazepam", "Lorazepam", "tablet", "1mg", "Various", True),
    ("Amikacin", "Amikacin", "injection", "500mg", "Various", True),
    ("Pentamidine", "Pentamidine", "injection", "300mg", "Various", True),
    ("Azathioprine", "Azathioprine", "tablet", "50mg", "Various", True),
    ("Codeine", "Codeine", "tablet", "30mg", "Various", True),
    ("Prednisolone", "Prednisolone", "tablet", "5mg", "Various", True),
    ("Aripiprazole", "Aripiprazole", "tablet", "10mg", "Otsuka", True),
    ("Cyclobenzaprine", "Cyclobenzaprine", "tablet", "10mg", "Various", True),
    ("Dofetilide", "Dofetilide", "capsule", "250mcg", "Pfizer", True),
    ("Tamsulosin", "Tamsulosin", "capsule", "0.4mg", "Various", True),
    ("Pregabalin", "Pregabalin", "capsule", "75mg", "Pfizer", True),
    ("Loxoprofen", "Loxoprofen", "tablet", "60mg", "Various", True),
    ("Amantadine", "Amantadine", "capsule", "100mg", "Various", True),
    ("Fluvoxamine", "Fluvoxamine", "tablet", "50mg", "Various", True),
    ("Clozapine", "Clozapine", "tablet", "25mg", "Various", True),
    ("Albuterol", "Albuterol", "inhaler", "90mcg", "GSK", True),
    ("Diclofenac", "Diclofenac", "tablet", "50mg", "Various", True),
    ("Aspirin", "Acetylsalicylic Acid", "tablet", "81mg", "Bayer", False),
    ("Warfarin", "Warfarin Sodium", "tablet", "5mg", "Various", True),
    ("Ibuprofen", "Ibuprofen", "tablet", "200mg", "Various", False),
    ("Metformin", "Metformin HCl", "tablet", "500mg", "Various", True),
    ("Lisinopril", "Lisinopril", "tablet", "10mg", "Various", True),
    ("Omeprazole", "Omeprazole", "capsule", "20mg", "Various", False),
]

drug_objects = []
for drug_data in drugs_data:
    name, generic, form, strength, manufacturer, rx_required = drug_data
    
    drug, created = Drug.objects.get_or_create(
        name=name,
        generic_name=generic,
        defaults={
            'form': form,
            'strength': strength,
            'manufacturer': manufacturer,
            'requires_prescription': rx_required,
            'description': f"{name} {strength} - Used for various conditions",
            'pharmacy': pharmacy
        }
    )
    drug_objects.append(drug)

print(f"   OK: Created {len(drug_objects)} drugs")

# ============================================
# STEP 5: Create Batches (Stock)
# ============================================
print("\n[5/8] Creating Stock Batches...")

batch_count = 0
for drug in drug_objects[:20]:  # Create batches for first 20 drugs to save time
    # Create 1-2 batches per drug
    num_batches = random.randint(1, 2)
    
    for i in range(num_batches):
        batch_number = f"BATCH-{drug.id}-{datetime.now().strftime('%Y%m')}-{i+1:03d}"
        
        # Random purchase and selling prices
        purchase_price = round(random.uniform(5, 100), 2)
        selling_price = round(purchase_price * 1.3, 2)
        
        # Random expiry date (30-365 days from now)
        expiry_days = random.randint(30, 365)
        expiry_date = datetime.now().date() + timedelta(days=expiry_days)
        
        # Random manufacture date (1-2 years ago)
        manufacture_date = datetime.now().date() - timedelta(days=random.randint(365, 730))
        
        # Random quantity (50-500 units)
        quantity = random.randint(50, 500)
        
        # Random supplier
        supplier = random.choice(suppliers)
        
        batch, created = Batch.objects.get_or_create(
            batch_number=batch_number,
            defaults={
                'drug': drug,
                'supplier': supplier,
                'quantity': quantity,
                'purchase_price': purchase_price,
                'selling_price': selling_price,
                'manufacture_date': manufacture_date,
                'expiry_date': expiry_date,
                'pharmacy': pharmacy
            }
        )
        batch_count += 1

print(f"   OK: Created {batch_count} stock batches")

# ============================================
# STEP 6: Create Sample Patients
# ============================================
print("\n[6/8] Creating Sample Patients...")

patients_data = [
    {'first': 'John', 'last': 'Doe', 'dob': '1960-05-15', 'gender': 'M', 'phone': '+1 (555) 111-2222', 'allergies': 'Penicillin'},
    {'first': 'Jane', 'last': 'Smith', 'dob': '1975-08-20', 'gender': 'F', 'phone': '+1 (555) 333-4444', 'allergies': 'Sulfa'},
    {'first': 'Robert', 'last': 'Johnson', 'dob': '1982-11-30', 'gender': 'M', 'phone': '+1 (555) 555-6666', 'allergies': 'None'},
    {'first': 'Maria', 'last': 'Garcia', 'dob': '1990-03-25', 'gender': 'F', 'phone': '+1 (555) 777-8888', 'allergies': 'Aspirin'},
    {'first': 'David', 'last': 'Wilson', 'dob': '1968-12-10', 'gender': 'M', 'phone': '+1 (555) 999-0000', 'allergies': 'Codeine'},
]

patients = []
for p_data in patients_data:
    patient, created = Patient.objects.get_or_create(
        first_name=p_data['first'],
        last_name=p_data['last'],
        defaults={
            'date_of_birth': p_data['dob'],
            'gender': p_data['gender'],
            'phone': p_data['phone'],
            'email': f"{p_data['first'].lower()}.{p_data['last'].lower()}@example.com",
            'address': "123 Patient St, Medical City",
            'allergies': p_data['allergies'],
            'emergency_contact_name': "Emergency Contact",
            'emergency_contact_phone': "+1 (555) 000-9999",
            'pharmacy': pharmacy
        }
    )
    patients.append(patient)
    print(f"   OK: {patient.first_name} {patient.last_name}")

# ============================================
# STEP 7: Create Sample Prescriptions
# ============================================
print("\n[7/8] Creating Sample Prescriptions...")

prescription_statuses = ['pending', 'verified', 'dispensed', 'completed']
prescription_count = 0

for patient in patients[:3]:
    num_rx = random.randint(1, 2)
    
    for i in range(num_rx):
        # Select random drugs
        selected_drugs = random.sample(drug_objects, min(2, len(drug_objects)))
        
        rx_number = f"RX-{datetime.now().strftime('%Y%m%d')}-{patient.id:03d}-{i+1:03d}"
        
        prescription = Prescription.objects.create(
            prescription_number=rx_number,
            patient=patient,
            prescribed_by=f"Dr. {random.choice(['Smith', 'Johnson', 'Williams', 'Brown'])}",
            prescribed_date=datetime.now().date(),
            pharmacist=admin_user,
            status=random.choice(prescription_statuses),
            notes="Take as prescribed",
            pharmacy=pharmacy
        )
        
        for drug in selected_drugs:
            # Find a batch for this drug
            batch = Batch.objects.filter(drug=drug, quantity__gt=0, pharmacy=pharmacy).first()
            
            PrescriptionItem.objects.create(
                prescription=prescription,
                drug=drug,
                batch=batch,
                dosage=f"{drug.strength}",
                frequency=random.choice(['once daily', 'twice daily', 'three times daily']),
                duration=f"{random.randint(5, 30)} days",
                quantity=random.randint(10, 90),
                instructions="Take with food"
            )
        
        prescription_count += 1

print(f"   OK: Created {prescription_count} prescriptions")

# ============================================
# STEP 8: Create Sample Sales
# ============================================
print("\n[8/8] Creating Sample Sales...")

sales_count = 0
for i in range(10):
    # Select random items
    num_items = random.randint(1, 2)
    available_batches = list(Batch.objects.filter(pharmacy=pharmacy))
    if len(available_batches) < num_items:
        continue
    
    selected_batches = random.sample(available_batches, num_items)
    
    subtotal = 0
    sale_items = []
    
    for batch in selected_batches:
        quantity = random.randint(1, 2)
        item_total = quantity * float(batch.selling_price)
        subtotal += item_total
        sale_items.append({
            'batch': batch,
            'quantity': quantity,
            'unit_price': batch.selling_price,
            'total_price': item_total
        })
    
    tax = subtotal * 0.1
    total = subtotal + tax
    
    invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{i+1:04d}"
    
    sale = Sale.objects.create(
        invoice_number=invoice_number,
        pharmacist=admin_user,
        subtotal=subtotal,
        tax=tax,
        total=total,
        payment_method=random.choice(['cash', 'card', 'mobile']),
        pharmacy=pharmacy
    )
    
    for item in sale_items:
        SaleItem.objects.create(
            sale=sale,
            batch=item['batch'],
            quantity=item['quantity'],
            unit_price=item['unit_price'],
            total_price=item['total_price']
        )
        
        # Update batch quantity
        item['batch'].quantity -= item['quantity']
        item['batch'].save()
    
    sales_count += 1

print(f"   OK: Created {sales_count} sales transactions")

# ============================================
# SUMMARY
# ============================================
print("\n" + "=" * 70)
print("DATABASE SETUP COMPLETE!")
print("=" * 70)
print("\nSUMMARY:")
print(f"   Pharmacy: {pharmacy.name}")
print(f"   Admin User: admin / admin123")
print(f"   Drugs: {Drug.objects.filter(pharmacy=pharmacy).count()}")
print(f"   Batches: {Batch.objects.filter(pharmacy=pharmacy).count()}")
print(f"   Patients: {Patient.objects.filter(pharmacy=pharmacy).count()}")
print(f"   Prescriptions: {Prescription.objects.filter(pharmacy=pharmacy).count()}")
print(f"   Sales: {Sale.objects.filter(pharmacy=pharmacy).count()}")

print("\nLOGIN CREDENTIALS:")
print("   Username: admin")
print("   Password: admin123")

print("\nYou can now:")
print("   1. Login with admin/admin123")
print("   2. Test the drug interaction system")
print("   3. Create prescriptions and sales")

print("\n" + "=" * 70)