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
from .interaction_engine import DrugInteractionEngine
from patients.models import Patient
from inventory.models import Drug, Batch
from .forms import PrescriptionForm, PrescriptionItemForm, PrescriptionVerifyForm

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

@login_required
def prescription_create(request):
    """Create new prescription"""
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
            prescription.save()
            
            # Create prescription items
            for item_data in items:
                drug = Drug.objects.get(id=item_data['drug_id'])
                # Find available batch
                batch = Batch.objects.filter(
                    drug=drug,
                    quantity__gte=item_data['quantity'],
                    expiry_date__gt=timezone.now().date()
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
            
            # Check interactions
            engine = DrugInteractionEngine()
            alerts = engine.check_prescription(prescription, request.user)
            
            if alerts:
                high_risk = any(a['severity'] == 'high' for a in alerts)
                if high_risk:
                    prescription.status = 'on_hold'
                    prescription.save()
                    messages.warning(request, 'High-risk interactions detected. Prescription placed on hold.')
                else:
                    messages.info(request, f'{len(alerts)} interaction(s) detected. Please review.')
            
            messages.success(request, 'Prescription created successfully.')
            return redirect('prescriptions:detail', pk=prescription.pk)
        else:
            messages.error(request, 'Please fill all required fields.')
    else:
        form = PrescriptionForm()
    
    context = {
        'form': form,
        'patients': Patient.objects.all().order_by('last_name'),
        'drugs': Drug.objects.all().order_by('name')
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
    
    # Check stock availability
    stock_available = True
    for item in items:
        if not item.batch or item.batch.quantity < item.quantity:
            stock_available = False
            break
    
    context = {
        'prescription': prescription,
        'items': items,
        'interactions': interactions,
        'stock_available': stock_available,
        'can_dispense': prescription.status == 'verified' and stock_available,
        'can_verify': prescription.status == 'pending' and not interactions.filter(severity='high', overridden_by__isnull=True).exists()
    }
    return render(request, 'prescriptions/detail.html', context)

@login_required
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
def prescription_dispense(request, pk):
    """Dispense prescription"""
    prescription = get_object_or_404(Prescription, pk=pk)
    
    if prescription.status != 'verified':
        messages.error(request, 'Prescription must be verified before dispensing.')
        return redirect('prescriptions:detail', pk=pk)
    
    if request.method == 'POST':
        # Check stock and update quantities
        items = prescription.items.select_related('batch').all()
        stock_sufficient = True
        
        for item in items:
            if not item.batch or item.batch.quantity < item.quantity:
                stock_sufficient = False
                break
        
        if not stock_sufficient:
            messages.error(request, 'Insufficient stock for one or more items.')
            return redirect('prescriptions:detail', pk=pk)
        
        # Update stock
        for item in items:
            if item.batch:
                item.batch.quantity -= item.quantity
                item.batch.save()
                
                # Check if low stock alert needed
                if item.batch.is_low_stock():
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
    
    return render(request, 'prescriptions/dispense.html', {'prescription': prescription})

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

from .ai_interaction_engine import AIDrugInteractionEngine

# Initialize AI engine (singleton)
ai_engine = AIDrugInteractionEngine()

@login_required
@require_http_methods(["POST"])
def check_interactions_api(request):
    """AI-powered drug interaction checking"""
    try:
        data = json.loads(request.body)
        patient_id = data.get('patient_id')
        items = data.get('items', [])
        
        print(f"🤖 AI Engine received request - Patient: {patient_id}, Items: {items}")
        
        if not patient_id or not items:
            return JsonResponse({'error': 'Patient and medications required'}, status=400)
        
        # Get patient
        patient = Patient.objects.get(id=patient_id)
        
        # Create temp prescription
        class TempItem:
            def __init__(self, drug, dosage, frequency, duration, quantity):
                self.drug = drug
                self.dosage = dosage
                self.frequency = frequency
                self.duration = duration
                self.quantity = quantity
        
        temp_items = []
        for item in items:
            drug = Drug.objects.get(id=item['drug_id'])
            temp_items.append(TempItem(
                drug=drug,
                dosage=item.get('dosage', '1 tablet'),
                frequency=item.get('frequency', 'once daily'),
                duration=item.get('duration', '7 days'),
                quantity=item.get('quantity', 1)
            ))
        
        class TempPrescription:
            def __init__(self, patient, items):
                self.patient = patient
                self.items = items
        
        temp_prescription = TempPrescription(patient, temp_items)
        
        # Use AI engine
        alerts = ai_engine.check_prescription(temp_prescription, request.user)
        
        print(f"🤖 AI Engine generated {len(alerts)} alerts")
        
        return JsonResponse({
            'success': True,
            'alerts': alerts,
            'ai_processed': True,
            'has_interactions': len(alerts) > 0,
            'high_risk_count': sum(1 for a in alerts if a.get('severity') == 'high')
        })
        
    except Exception as e:
        print(f"🤖 AI Engine error: {str(e)}")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

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