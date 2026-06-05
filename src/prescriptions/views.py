from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count
from django.http import JsonResponse, HttpResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.core.paginator import Paginator
import json
from datetime import datetime
from .models import Prescription, PrescriptionItem, InteractionLog
# from .ai_interaction_engine import AIDrugInteractionEngine
from patients.models import Patient
from inventory.models import Drug, Batch
from .forms import PrescriptionForm, PrescriptionItemForm, PrescriptionVerifyForm
from accounts.decorators import admin_required, pharmacist_required, technician_required
import re

@login_required
def prescription_list(request):
    """List all prescriptions"""
    prescriptions = Prescription.objects.select_related('patient', 'pharmacist').all().order_by('-created_at')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status:
        prescriptions = prescriptions.filter(status=status)
    
    # Filter by date
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        prescriptions = prescriptions.filter(created_at__date__gte=date_from)
    if date_to:
        prescriptions = prescriptions.filter(created_at__date__lte=date_to)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        prescriptions = prescriptions.filter(
            Q(prescription_number__icontains=search) |
            Q(patient__first_name__icontains=search) |
            Q(patient__last_name__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(prescriptions, 20)
    page = request.GET.get('page')
    prescriptions_page = paginator.get_page(page)
    
    context = {
        'prescriptions': prescriptions_page,
        'status_choices': Prescription.STATUS_CHOICES,
        'current_status': status,
        'date_from': date_from,
        'date_to': date_to,
        'search': search
    }
    return render(request, 'prescriptions/list.html', context)


from .fda_dosage_api import FDADosageAPI

fda_client = FDADosageAPI()

@login_required
@require_http_methods(["POST"])
def check_fda_dosage_api(request):
    """Real-time FDA dosage check API"""
    try:
        data = json.loads(request.body)
        drug_name = data.get('drug_name')
        dose_mg = float(data.get('dose_mg', 0))
        frequency = int(data.get('frequency', 1))
        
        if not drug_name or dose_mg <= 0:
            return JsonResponse({'error': 'Invalid input'}, status=400)
        
        # Check FDA database
        safety = fda_client.check_dosage_safety(drug_name, dose_mg, frequency)
        
        return JsonResponse({
            'success': True,
            'is_safe': safety['is_safe'],
            'severity': safety['severity'],
            'warnings': safety['warnings'],
            'fda_max_daily': safety.get('fda_max_daily'),
            'fda_recommended': safety.get('fda_recommended')
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required
@technician_required
def prescription_create(request):
    """Create new prescription with FDA dosage checking and AI interaction detection"""
    if request.method == 'POST':
        form = PrescriptionForm(request.POST)
        items_data = request.POST.get('items', '[]')
        
        try:
            items = json.loads(items_data)
        except:
            items = []
        
        if form.is_valid() and items:
            prescription = form.save(commit=False)
            prescription.pharmacist = request.user
            prescription.prescription_number = generate_prescription_number()
            prescription.pharmacy = request.pharmacy
            prescription.save()
            
            # Create prescription items
            for item_data in items:
                drug = Drug.objects.get(id=item_data['drug_id'])
                
                # Find available batch
                batch = Batch.objects.filter(
                    drug=drug,
                    quantity__gte=item_data['quantity'],
                    expiry_date__gt=timezone.now().date(),
                    pharmacy=request.pharmacy
                ).first()
                
                PrescriptionItem.objects.create(
                    prescription=prescription,
                    drug=drug,
                    batch=batch,
                    dosage=item_data['dosage'],
                    frequency=item_data['frequency'],
                    duration=item_data['duration'],
                    quantity=item_data['quantity'],
                    instructions=item_data.get('instructions', '')
                )
            
            # ============================================================
            # STEP 1: CRITICAL DOSAGE SAFETY CHECK (MUST PASS FIRST)
            # ============================================================
            dosage_alerts = []
            try:
                from .dosage_checker import dosage_checker
                dosage_alerts = dosage_checker.check_prescription(prescription)
            except Exception as e:
                print(f"Dosage checker error: {e}")
            
            # Check for critical/severe dosage issues
            critical_alerts = [a for a in dosage_alerts if a.get('severity') in ['critical', 'high']]
            moderate_alerts = [a for a in dosage_alerts if a.get('severity') == 'moderate']
            
            # Store alerts in session
            request.session['prescription_alerts'] = dosage_alerts
            
            # If critical overdose detected - BLOCK prescription immediately
            if critical_alerts:
                prescription.status = 'on_hold'
                prescription.save()
                
                # Show critical errors
                for alert in critical_alerts:
                    messages.error(request, f"🚨 {alert.get('description', 'Critical safety issue detected')}")
                    messages.error(request, f"   → {alert.get('recommendation', 'Do not dispense')}")
                
                messages.error(request, "⚠️ Prescription has been placed ON HOLD due to safety concerns.")
                return redirect('prescriptions:detail', pk=prescription.pk)
            
            # Show warnings for moderate issues
            for alert in moderate_alerts:
                messages.warning(request, f"⚠️ {alert.get('description', 'Potential issue detected')}")
            
            # ============================================================
            # STEP 2: DRUG INTERACTION CHECK (AI ENGINE)
            # ============================================================
            interaction_alerts = []
            try:
                from .interaction_engine import DrugInteractionEngine
                engine = DrugInteractionEngine()
                interaction_alerts = engine.check_prescription(prescription, request.user)
            except Exception as e:
                print(f"Interaction engine error: {e}")
            
            # Check for high-risk interactions
            high_risk_interactions = [a for a in interaction_alerts if a.get('severity') == 'high']
            
            # Store interaction alerts
            request.session['prescription_interactions'] = interaction_alerts
            
            # If high-risk interactions found - place on hold
            if high_risk_interactions:
                prescription.status = 'on_hold'
                prescription.save()
                
                for alert in high_risk_interactions:
                    messages.error(request, f"🔴 HIGH RISK INTERACTION: {alert.get('description', 'Unknown interaction')}")
                    messages.error(request, f"   → {alert.get('recommendation', 'Review before dispensing')}")
                
                messages.error(request, "⚠️ Prescription placed ON HOLD due to high-risk drug interactions.")
                return redirect('prescriptions:detail', pk=prescription.pk)
            
            # ============================================================
            # STEP 3: Show warnings for moderate interactions
            # ============================================================
            moderate_interactions = [a for a in interaction_alerts if a.get('severity') == 'moderate']
            for alert in moderate_interactions:
                messages.warning(request, f"⚠️ {alert.get('description', 'Potential interaction detected')}")
            
            # ============================================================
            # STEP 4: Final approval - Prescription is safe
            # ============================================================
            if critical_alerts or high_risk_interactions:
                # This should not happen due to returns above, but just in case
                prescription.status = 'on_hold'
                prescription.save()
                messages.warning(request, "Prescription requires pharmacist review before dispensing.")
            else:
                # Prescription is safe - proceed
                messages.success(request, "✅ Prescription created successfully. No safety issues detected.")
            
            return redirect('prescriptions:detail', pk=prescription.pk)
        else:
            if not form.is_valid():
                for field, errors in form.errors.items():
                    for error in errors:
                        messages.error(request, f"{field}: {error}")
            if not items:
                messages.error(request, 'Please add at least one medication to the prescription.')
            
            return redirect('prescriptions:create')
    else:
        form = PrescriptionForm()
    
    # Get patients and drugs for the dropdowns
    patients = Patient.objects.filter(pharmacy=request.pharmacy).order_by('last_name', 'first_name')
    drugs = Drug.objects.filter(pharmacy=request.pharmacy).order_by('name')
    
    context = {
        'form': form,
        'patients': patients,
        'drugs': drugs,
        'is_edit': False,
        'today': timezone.now().date()
    }
    return render(request, 'prescriptions/create.html', context)


@login_required
def prescription_detail(request, pk):
    """View prescription details"""
    prescription = get_object_or_404(
        Prescription.objects.select_related('patient', 'pharmacist'),
        pk=pk
    )
    items = prescription.items.select_related('drug', 'batch').all()
    interactions = prescription.interaction_logs.all()
    
    # Check stock availability for each item
    stock_available = True
    stock_details = []
    
    for item in items:
        if not item.batch:
            # Try to find an available batch
            available_batch = Batch.objects.filter(
                drug=item.drug,
                quantity__gte=item.quantity,
                expiry_date__gt=timezone.now().date()
            ).first()
            
            if available_batch:
                stock_details.append({
                    'drug': item.drug.name,
                    'status': 'available',
                    'batch': available_batch.batch_number,
                    'available': available_batch.quantity
                })
            else:
                stock_available = False
                stock_details.append({
                    'drug': item.drug.name,
                    'status': 'out_of_stock',
                    'message': 'No batch available'
                })
        elif item.batch.quantity < item.quantity:
            stock_available = False
            stock_details.append({
                'drug': item.drug.name,
                'status': 'insufficient',
                'batch': item.batch.batch_number,
                'available': item.batch.quantity,
                'needed': item.quantity
            })
        else:
            stock_details.append({
                'drug': item.drug.name,
                'status': 'ok',
                'batch': item.batch.batch_number,
                'available': item.batch.quantity
            })
    
    context = {
        'prescription': prescription,
        'items': items,
        'interactions': interactions,
        'stock_available': stock_available,
        'stock_details': stock_details,
        'can_dispense': prescription.status == 'verified' and stock_available,
        'can_verify': prescription.status == 'pending' and not interactions.filter(severity='high', overridden_by__isnull=True).exists()
    }
    return render(request, 'prescriptions/detail.html', context)



@login_required
@technician_required
def prescription_edit(request, pk):
    """Edit prescription"""
    prescription = get_object_or_404(Prescription, pk=pk)
    
    if prescription.status not in ['pending', 'on_hold']:
        messages.error(request, 'Cannot edit prescription in current status.')
        return redirect('prescriptions:detail', pk=pk)
    
    if request.method == 'POST':
        form = PrescriptionForm(request.POST, instance=prescription)
        if form.is_valid():
            form.save()
            messages.success(request, 'Prescription updated successfully.')
            return redirect('prescriptions:detail', pk=pk)
    else:
        form = PrescriptionForm(instance=prescription)
    
    items = prescription.items.select_related('drug').all()
    
    context = {
        'form': form,
        'prescription': prescription,
        'items': items,
        'drugs': Drug.objects.all()
    }
    return render(request, 'prescriptions/edit.html', context)

@login_required
@pharmacist_required
def prescription_verify(request, pk):
    """Verify prescription (pharmacist)"""
    prescription = get_object_or_404(Prescription, pk=pk)
    
    if prescription.status != 'pending':
        messages.error(request, 'Prescription cannot be verified.')
        return redirect('prescriptions:detail', pk=pk)
    
    if request.method == 'POST':
        form = PrescriptionVerifyForm(request.POST)
        if form.is_valid():
            prescription.status = 'verified'
            prescription.verified_by = request.user
            prescription.verified_at = timezone.now()
            prescription.notes = form.cleaned_data.get('notes', '')
            prescription.save()
            
            messages.success(request, 'Prescription verified successfully.')
            return redirect('prescriptions:detail', pk=pk)
    else:
        form = PrescriptionVerifyForm()
    
    context = {
        'prescription': prescription,
        'form': form
    }
    return render(request, 'prescriptions/verify.html', context)


@login_required
@pharmacist_required
def prescription_dispense(request, pk):
    """Dispense prescription"""
    prescription = get_object_or_404(Prescription, pk=pk)
    
    # Check if prescription is verified (by status, not by verified_by field)
    if prescription.status != 'verified':
        messages.error(request, 'Prescription must be verified before dispensing.')
        return redirect('prescriptions:detail', pk=pk)
    
    # Check stock and assign batches if needed
    items = prescription.items.select_related('drug', 'batch').all()
    stock_issues = []
    
    for item in items:
        # Check if batch exists and has enough quantity
        if not item.batch:
            # Try to find an available batch
            available_batch = Batch.objects.filter(
                drug=item.drug,
                quantity__gte=item.quantity,
                expiry_date__gt=timezone.now().date(),
                pharmacy=request.pharmacy
            ).first()
            
            if available_batch:
                item.batch = available_batch
                item.save()
                print(f"Assigned batch {available_batch.batch_number} to {item.drug.name}")
            else:
                stock_issues.append(f"{item.drug.name} - No batch available")
        elif item.batch.quantity < item.quantity:
            stock_issues.append(f"{item.drug.name} - Only {item.batch.quantity} units available, need {item.quantity}")
    
    if stock_issues:
        messages.error(request, f'Cannot dispense: {" | ".join(stock_issues)}')
        return redirect('prescriptions:detail', pk=pk)
    
    if request.method == 'POST':
        # Process the dispensing
        try:
            for item in items:
                if item.batch:
                    # Update stock
                    item.batch.quantity -= item.quantity
                    item.batch.save()
                    
                    # Check if low stock alert needed
                    if item.batch.quantity <= 10:
                        from inventory.models import StockAlert
                        StockAlert.objects.create(
                            batch=item.batch,
                            alert_type='low_stock',
                            message=f'Low stock alert: {item.batch.drug.name} - Only {item.batch.quantity} remaining'
                        )
            
            prescription.status = 'dispensed'
            prescription.dispensed_at = timezone.now()
            prescription.save()
            
            messages.success(request, 'Prescription dispensed successfully.')
            return redirect('sales:create_from_rx', prescription_id=pk)
            
        except Exception as e:
            messages.error(request, f'Error dispensing: {str(e)}')
            return redirect('prescriptions:detail', pk=pk)
    
    # GET request - show dispense confirmation page
    context = {
        'prescription': prescription,
        'items': items,
        'stock_available': len(stock_issues) == 0
    }
    return render(request, 'prescriptions/dispense.html', context)

    

@login_required
def prescription_cancel(request, pk):
    """Cancel prescription"""
    prescription = get_object_or_404(Prescription, pk=pk)
    
    if prescription.status in ['dispensed', 'cancelled']:
        messages.error(request, 'Cannot cancel prescription in current status.')
        return redirect('prescriptions:detail', pk=pk)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        prescription.status = 'cancelled'
        prescription.cancellation_reason = reason
        prescription.cancelled_by = request.user
        prescription.cancelled_at = timezone.now()
        prescription.save()
        
        messages.success(request, 'Prescription cancelled successfully.')
        return redirect('prescriptions:detail', pk=pk)
    
    return render(request, 'prescriptions/cancel.html', {'prescription': prescription})

@login_required
def prescription_print(request, pk):
    """Generate printable prescription"""
    prescription = get_object_or_404(
        Prescription.objects.select_related('patient', 'pharmacist'),
        pk=pk
    )
    items = prescription.items.select_related('drug').all()
    
    return render(request, 'prescriptions/print.html', {
        'prescription': prescription,
        'items': items
    })



# Initialize AI engine (singleton)
# ai_engine = AIDrugInteractionEngine()
ai_engine = None  # Temporarily disabled for database setup

# Replace the old import
# from ai_engine.predictor import predictor

# With this:
from ai_engine.predictor_fixed import fixed_predictor as predictor

@login_required
@require_http_methods(["POST"])
def check_interactions_api(request):
    """AI-powered drug interaction checking WITH dosage safety checks"""
    try:
        data = json.loads(request.body)
        patient_id = data.get('patient_id')
        items_data = data.get('items', [])
        
        print(f"🔍 Checking prescription for patient {patient_id}")
        print(f"📊 Items to check: {items_data}")
        
        if not patient_id or not items_data:
            return JsonResponse({'error': 'Patient and medications required'}, status=400)
        
        # Get patient for age-based checks
        patient = Patient.objects.get(id=patient_id)
        
        # ============================================================
        # STEP 1: DOSAGE SAFETY CHECKS (CRITICAL)
        # ============================================================
        dosage_alerts = []
        
        for item in items_data:
            drug_id = item.get('drug_id')
            drug_name = item.get('drug_name', '')
            dosage = item.get('dosage', '')
            frequency = item.get('frequency', '')
            duration = item.get('duration', '7 days')
            quantity = item.get('quantity', 0)
            
            # Get drug details if we have ID
            if drug_id:
                try:
                    drug = Drug.objects.get(id=drug_id)
                    drug_name = drug.name
                except:
                    pass
            
            print(f"💊 Checking: {drug_name} - {dosage} {frequency}")
            
            # Parse dosage
            dose_mg = parse_dosage_to_mg(dosage)
            times_per_day = parse_frequency_to_times(frequency)
            
            print(f"   Dose: {dose_mg}mg, Times per day: {times_per_day}")
            
            if dose_mg is None:
                dosage_alerts.append({
                    'type': 'dosage_parsing_error',
                    'severity': 'warning',
                    'drug': drug_name,
                    'description': f"Could not parse dosage: '{dosage}'. Please verify manually.",
                    'recommendation': "Check that dosage is entered correctly (e.g., '500mg')"
                })
                continue
            
            daily_dose = dose_mg * times_per_day
            
            # CRITICAL SAFETY LIMITS DATABASE
            SAFETY_LIMITS = {
                'ATENOLOL': {'max_daily': 100, 'max_single': 100, 'warning': 'beta-blocker overdose risk'},
                'ALLOPURINOL': {'max_daily': 800, 'max_single': 300, 'warning': 'severe skin reactions, liver failure'},
                'AMANTADINE': {'max_daily': 400, 'max_single': 200, 'warning': 'neurotoxicity, hallucinations'},
                'PARACETAMOL': {'max_daily': 4000, 'max_single': 1000, 'warning': 'liver failure'},
                'IBUPROFEN': {'max_daily': 3200, 'max_single': 800, 'warning': 'kidney damage, stomach bleeding'},
                'ASPIRIN': {'max_daily': 4000, 'max_single': 1000, 'warning': 'bleeding risk'},
                'METFORMIN': {'max_daily': 2550, 'max_single': 1000, 'warning': 'lactic acidosis'},
                'ATORVASTATIN': {'max_daily': 80, 'max_single': 80, 'warning': 'liver damage, muscle breakdown'},
                'SIMVASTATIN': {'max_daily': 40, 'max_single': 40, 'warning': 'muscle damage'},
                'LISINOPRIL': {'max_daily': 40, 'max_single': 40, 'warning': 'hypotension, kidney failure'},
                'WARFARIN': {'max_daily': 10, 'max_single': 10, 'warning': 'severe bleeding'},
                'DIGOXIN': {'max_daily': 0.5, 'max_single': 0.5, 'warning': 'cardiac toxicity'},
                'COLCHICINE': {'max_daily': 2, 'max_single': 1.8, 'warning': 'severe toxicity, death'},
                'THEOPHYLLINE': {'max_daily': 600, 'max_single': 300, 'warning': 'seizures, cardiac arrhythmia'},
                'PHENYTOIN': {'max_daily': 400, 'max_single': 300, 'warning': 'toxicity, nystagmus'},
                'CARBAMAZEPINE': {'max_daily': 1200, 'max_single': 400, 'warning': 'blood disorders'},
                'VALPROATE': {'max_daily': 3000, 'max_single': 1000, 'warning': 'liver failure'},
                'LITHIUM': {'max_daily': 1800, 'max_single': 600, 'warning': 'toxicity, kidney damage'},
                'QUETIAPINE': {'max_daily': 800, 'max_single': 400, 'warning': 'sedation, metabolic issues'},
                'CLOZAPINE': {'max_daily': 900, 'max_single': 450, 'warning': 'seizures, agranulocytosis'},
                'TRAMADOL': {'max_daily': 400, 'max_single': 100, 'warning': 'seizures, serotonin syndrome'},
                'CODEINE': {'max_daily': 360, 'max_single': 60, 'warning': 'respiratory depression'},
                'MORPHINE': {'max_daily': 200, 'max_single': 30, 'warning': 'respiratory depression, addiction'},
                'OXYCODONE': {'max_daily': 80, 'max_single': 20, 'warning': 'respiratory depression, death'},
                'HYDROCODONE': {'max_daily': 60, 'max_single': 10, 'warning': 'respiratory depression'},
                'PROPRANOLOL': {'max_daily': 320, 'max_single': 160, 'warning': 'bradycardia, heart block'},
                'METOPROLOL': {'max_daily': 400, 'max_single': 200, 'warning': 'bradycardia, hypotension'},
                'CARVEDILOL': {'max_daily': 100, 'max_single': 50, 'warning': 'heart failure exacerbation'},
            }
            
            # Find matching drug
            matched_drug = None
            drug_upper = drug_name.upper()
            
            for limit_drug in SAFETY_LIMITS.keys():
                if limit_drug in drug_upper or drug_upper in limit_drug:
                    matched_drug = limit_drug
                    break
            
            if matched_drug:
                limits = SAFETY_LIMITS[matched_drug]
                max_daily = limits['max_daily']
                max_single = limits['max_single']
                
                print(f"   Matched drug: {matched_drug}, Max daily: {max_daily}mg, Max single: {max_single}mg")
                
                # Check single dose
                if dose_mg > max_single:
                    ratio = dose_mg / max_single
                    dosage_alerts.append({
                        'type': 'single_dose_overdose',
                        'severity': 'high',
                        'drug': drug_name,
                        'description': f"💀 CRITICAL: Single dose of {dose_mg}mg is {ratio:.0f}X higher than maximum safe single dose of {max_single}mg for {matched_drug}!",
                        'recommendation': f"DO NOT DISPENSE. Maximum single dose is {max_single}mg. Contact prescriber immediately."
                    })
                
                # Check daily dose
                if daily_dose > max_daily:
                    ratio = daily_dose / max_daily
                    if ratio >= 10:
                        severity = 'critical'
                        description = f"💀💀💀 EXTREME LETHAL OVERDOSE: {daily_dose}mg/day is {ratio:.0f}X the maximum safe dose of {max_daily}mg/day! THIS COULD BE FATAL!"
                    elif ratio >= 5:
                        severity = 'critical'
                        description = f"💀💀 CRITICAL OVERDOSE: {daily_dose}mg/day is {ratio:.1f}X the maximum safe dose of {max_daily}mg/day!"
                    elif ratio >= 2:
                        severity = 'high'
                        description = f"⚠️ SEVERE OVERDOSE: {daily_dose}mg/day exceeds maximum of {max_daily}mg/day by {int((ratio-1)*100)}%"
                    else:
                        severity = 'high'
                        description = f"⚠️ OVERDOSE: Daily dose of {daily_dose}mg exceeds maximum of {max_daily}mg/day"
                    
                    dosage_alerts.append({
                        'type': 'daily_dose_overdose',
                        'severity': severity,
                        'drug': drug_name,
                        'daily_dose': daily_dose,
                        'max_daily': max_daily,
                        'description': description,
                        'recommendation': f"DO NOT DISPENSE. Maximum daily dose is {max_daily}mg. {limits['warning']}"
                    })
                elif daily_dose > max_daily * 0.8:
                    dosage_alerts.append({
                        'type': 'high_dose_warning',
                        'severity': 'moderate',
                        'drug': drug_name,
                        'description': f"Daily dose of {daily_dose}mg is approaching the maximum of {max_daily}mg ({int((daily_dose/max_daily)*100)}% of limit)",
                        'recommendation': f"Consider if dose is appropriate. {limits['warning']}"
                    })
            else:
                # Unknown drug - flag for review if dose is high
                if daily_dose > 2000:
                    dosage_alerts.append({
                        'type': 'unverified_drug',
                        'severity': 'moderate',
                        'drug': drug_name,
                        'description': f"⚠️ UNVERIFIED DRUG: '{drug_name}' at {daily_dose}mg/day. Safety limits not in database.",
                        'recommendation': "Manual verification required. Please check dosing guidelines."
                    })
            
            # Check quantity vs expected
            if quantity > 0:
                duration_match = re.search(r'(\d+)', duration)
                duration_days = int(duration_match.group(1)) if duration_match else 7
                expected_quantity = times_per_day * duration_days
                
                if abs(quantity - expected_quantity) > expected_quantity * 0.2:
                    dosage_alerts.append({
                        'type': 'quantity_mismatch',
                        'severity': 'moderate',
                        'drug': drug_name,
                        'description': f"Quantity ({quantity}) does not match expected quantity ({expected_quantity}) for {duration_days} days of treatment",
                        'recommendation': "Verify quantity with prescriber."
                    })
        
        # ============================================================
        # STEP 2: DRUG-DRUG INTERACTION CHECKS (Existing AI)
        # ============================================================
        interaction_alerts = []
        
        # Create temp prescription for interaction checking
        class TempItem:
            def __init__(self, drug_id, drug_name, dosage, frequency, duration, quantity):
                self.drug = type('Drug', (), {'id': drug_id, 'name': drug_name})()
                self.dosage = dosage
                self.frequency = frequency
                self.duration = duration
                self.quantity = quantity
        
        temp_items = []
        for item in items_data:
            temp_items.append(TempItem(
                item.get('drug_id'),
                item.get('drug_name', ''),
                item.get('dosage', ''),
                item.get('frequency', ''),
                item.get('duration', '7 days'),
                item.get('quantity', 0)
            ))
        
        class TempPrescription:
            def __init__(self, patient, items):
                self.patient = patient
                self.items = items
        
        temp_prescription = TempPrescription(patient, temp_items)
        
        # Run interaction checks
        try:
            from .interaction_engine import DrugInteractionEngine
            engine = DrugInteractionEngine()
            interaction_alerts = engine.check_prescription(temp_prescription, request.user)
        except Exception as e:
            print(f"Interaction engine error: {e}")
        
        # ============================================================
        # STEP 3: COMBINE ALERTS
        # ============================================================
        all_alerts = dosage_alerts + interaction_alerts
        
        # Count high risk alerts
        high_risk_count = sum(1 for a in all_alerts if a.get('severity') in ['high', 'critical'])
        
        print(f"📊 Total alerts: {len(all_alerts)}, High risk: {high_risk_count}")
        print(f"   Dosage alerts: {len(dosage_alerts)}")
        print(f"   Interaction alerts: {len(interaction_alerts)}")
        
        return JsonResponse({
            'success': True,
            'alerts': all_alerts,
            'dosage_alerts': dosage_alerts,
            'interaction_alerts': interaction_alerts,
            'has_interactions': len(all_alerts) > 0,
            'high_risk_count': high_risk_count,
            'message': f"Found {len(all_alerts)} issue(s) including {high_risk_count} high-risk issue(s)"
        })
        
    except Patient.DoesNotExist:
        return JsonResponse({'error': 'Patient not found'}, status=404)
    except Exception as e:
        print(f"Error in check_interactions_api: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)


# Helper functions for dosage parsing
def parse_dosage_to_mg(dosage_text: str) -> float:
    """Parse dosage text to mg value"""
    if not dosage_text:
        return None
    
    dosage_lower = dosage_text.lower()
    
    # Extract number
    num_match = re.search(r'(\d+(?:\.\d+)?)', dosage_lower)
    if not num_match:
        return None
    
    dose_value = float(num_match.group(1))
    
    if 'mg' in dosage_lower:
        return dose_value
    elif 'mcg' in dosage_lower or 'microgram' in dosage_lower:
        return dose_value / 1000
    elif 'g' in dosage_lower or 'gram' in dosage_lower:
        return dose_value * 1000
    
    # Assume mg if no unit
    return dose_value


def parse_frequency_to_times(frequency_text: str) -> int:
    """Convert frequency text to times per day"""
    if not frequency_text:
        return 1
    
    freq_lower = frequency_text.lower()
    
    if 'once' in freq_lower or 'daily' in freq_lower:
        return 1
    elif 'twice' in freq_lower or 'bid' in freq_lower:
        return 2
    elif 'three' in freq_lower or 'thrice' in freq_lower or 'tid' in freq_lower:
        return 3
    elif 'four' in freq_lower or 'qid' in freq_lower:
        return 4
    elif 'every 4 hours' in freq_lower:
        return 6
    elif 'every 6 hours' in freq_lower:
        return 4
    elif 'every 8 hours' in freq_lower:
        return 3
    elif 'every 12 hours' in freq_lower:
        return 2
    
    # Try to extract pattern "every X hours"
    hour_match = re.search(r'every\s+(\d+)\s+hour', freq_lower)
    if hour_match:
        hours = int(hour_match.group(1))
        if hours > 0:
            return 24 // hours
    
    return 1


def simple_interaction_check(patient, items):
    """Simple fallback interaction checker"""
    alerts = []
    
    # Check allergies
    if patient and hasattr(patient, 'allergies') and patient.allergies:
        allergies = [a.strip().lower() for a in patient.allergies.split(',')]
        
        for item in items:
            drug_name = item.drug.name.lower()
            for allergy in allergies:
                if allergy and allergy in drug_name:
                    alerts.append({
                        'type': 'drug-allergy',
                        'severity': 'high',
                        'drug': item.drug.name,
                        'allergen': allergy,
                        'description': f'Patient is allergic to {allergy}',
                        'recommendation': 'DO NOT DISPENSE. Choose alternative.'
                    })
    
    # Check quantities
    for item in items:
        if item.quantity > 100:
            alerts.append({
                'type': 'dosage-warning',
                'severity': 'moderate',
                'drug': item.drug.name,
                'description': f'High quantity: {item.quantity} units',
                'recommendation': 'Verify with prescriber'
            })
    
    return alerts

@login_required
@require_http_methods(["POST"])
def override_interaction(request, interaction_id):
    """Override an interaction alert"""
    try:
        data = json.loads(request.body)
        reason = data.get('reason', '')
        
        if not reason:
            return JsonResponse({'error': 'Override reason required'}, status=400)
        
        interaction = get_object_or_404(InteractionLog, pk=interaction_id)
        
        interaction.overridden_by = request.user
        interaction.overridden_at = timezone.now()
        interaction.override_reason = reason
        interaction.save()
        
        # Log the override
        messages.success(request, 'Interaction overridden successfully.')
        
        return JsonResponse({
            'success': True,
            'message': 'Interaction overridden successfully'
        })
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def interaction_logs(request):
    """View interaction logs"""
    logs = InteractionLog.objects.select_related(
        'prescription__patient', 'drug_1', 'drug_2', 'overridden_by'
    ).all().order_by('-created_at')
    
    # Filter by severity
    severity = request.GET.get('severity', '')
    if severity:
        logs = logs.filter(severity=severity)
    
    # Filter by overridden status
    overridden = request.GET.get('overridden', '')
    if overridden == 'yes':
        logs = logs.filter(overridden_by__isnull=False)
    elif overridden == 'no':
        logs = logs.filter(overridden_by__isnull=True)
    
    # Pagination
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs_page = paginator.get_page(page)
    
    context = {
        'logs': logs_page,
        'severity': severity,
        'overridden': overridden,
        'severity_choices': InteractionLog.SEVERITY_CHOICES
    }
    return render(request, 'prescriptions/interaction_logs.html', context)

def generate_prescription_number():
    """Generate unique prescription number"""
    from datetime import datetime
    import random
    import string
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_chars = ''.join(random.choices(string.ascii_uppercase, k=3))
    return f"RX{timestamp}{random_chars}"

def debug_api(request):
    return render(request, 'debug_api.html')