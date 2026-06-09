from decimal import Decimal

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Drug, Batch, Supplier, StockAlert
from .forms import DrugForm, BatchForm, SupplierForm
from accounts.decorators import admin_required, pharmacist_required, technician_required

@login_required
def inventory_list(request):
    """List all drugs with current stock levels"""
    # Add this check
    if not request.pharmacy:
        messages.error(request, 'Pharmacy not found.')
        return redirect('dashboard')
    # drugs = Drug.objects.all().prefetch_related('batches')
    drugs = Drug.objects.filter(pharmacy=request.pharmacy)
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        drugs = drugs.filter(
            Q(name__icontains=search_query) |
            Q(generic_name__icontains=search_query) |
            Q(manufacturer__icontains=search_query)
        )
    
    # Filter by form
    form_filter = request.GET.get('form', '')
    if form_filter:
        drugs = drugs.filter(form=form_filter)
    
    # Get stock levels for each drug
    for drug in drugs:
        batches = drug.batches.all()
        drug.total_stock = sum(batch.quantity for batch in batches)
        drug.nearest_expiry = min([b.expiry_date for b in batches], default=None)
    
    context = {
        'drugs': drugs,
        'search_query': search_query,
        'form_filter': form_filter,
        'drug_forms': Drug.DRUG_FORMS,
    }
    return render(request, 'inventory/list.html', context)

@login_required
def inventory_detail(request, pk):
    """View drug details and all batches"""
    drug = get_object_or_404(Drug, pk=pk)
    batches = drug.batches.all().order_by('expiry_date')
    
    # Calculate statistics
    total_stock = batches.aggregate(Sum('quantity'))['quantity__sum'] or 0
    expiring_soon = batches.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=30),
        quantity__gt=0
    ).count()
    expired = batches.filter(expiry_date__lt=timezone.now().date()).count()
    
    context = {
        'drug': drug,
        'batches': batches,
        'total_stock': total_stock,
        'expiring_soon': expiring_soon,
        'expired': expired,
    }
    return render(request, 'inventory/detail.html', context)


from .drug_mapper import drug_mapper

@login_required
@technician_required
def inventory_add(request):
    """Add new drug - automatically maps to training ID"""
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            drug = form.save(commit=False)
            drug.pharmacy = request.pharmacy
            
            # AUTO-MAP to training ID
            training_id = drug_mapper.get_training_id(drug.name)
            if training_id:
                drug.training_id = training_id
                messages.info(request, f"Drug mapped to training data (ID: {training_id[:8]}...)")
            else:
                # Try fuzzy matching
                closest = drug_mapper.find_closest_match(drug.name)
                if closest:
                    training_id = drug_mapper.get_training_id(closest)
                    drug.training_id = training_id
                    messages.warning(request, f"Drug mapped to similar drug '{closest}' in training data")
                else:
                    messages.warning(request, "Drug not found in training data. Interaction predictions may be limited.")
            
            drug.save()
            messages.success(request, f'{drug.name} added successfully.')
            return redirect('inventory:list')
    else:
        form = DrugForm()
    
    return render(request, 'inventory/add_edit.html', {
        'form': form,
        'title': 'Add New Drug',
        'edit_mode': False
    })


@login_required
@technician_required
def inventory_edit(request, pk):
    """Edit drug details"""
    drug = get_object_or_404(Drug, pk=pk)
    if request.method == 'POST':
        form = DrugForm(request.POST, instance=drug)
        if form.is_valid():
            form.save()
            messages.success(request, 'Drug updated successfully.')
            return redirect('inventory:detail', pk=drug.pk)
    else:
        form = DrugForm(instance=drug)
    
    return render(request, 'inventory/add_edit.html', {
        'form': form,
        'drug': drug,
        'edit_mode': True
    })

@login_required
@admin_required
def inventory_delete(request, pk):
    """Delete drug"""
    drug = get_object_or_404(Drug, pk=pk)
    if request.method == 'POST':
        drug.delete()
        messages.success(request, 'Drug deleted successfully.')
        return redirect('inventory:list')
    return render(request, 'inventory/confirm_delete.html', {'drug': drug})



@login_required
@technician_required
def add_batch(request, pk):
    """Add stock to existing drug"""
    drug = get_object_or_404(Drug, pk=pk, pharmacy=request.pharmacy)
    suppliers = Supplier.objects.filter(pharmacy=request.pharmacy)
    
    if request.method == 'POST':
        quantity = request.POST.get('quantity')
        purchase_price = request.POST.get('purchase_price')
        selling_price = request.POST.get('selling_price')
        expiry_date = request.POST.get('expiry_date')
        manufacture_date = request.POST.get('manufacture_date')
        batch_number = request.POST.get('batch_number')
        supplier_id = request.POST.get('supplier_id')
        
        # Validation
        if not quantity or not purchase_price or not selling_price or not expiry_date:
            messages.error(request, 'Quantity, purchase price, selling price, and expiry date are required.')
            return redirect('inventory:add_batch', pk=pk)
        
        # Generate batch number if not provided
        if not batch_number:
            from datetime import datetime
            batch_number = f"BATCH-{drug.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get supplier if selected
        supplier = None
        if supplier_id:
            supplier = get_object_or_404(Supplier, id=supplier_id, pharmacy=request.pharmacy)
        
        # Set manufacture date to today if not provided
        if not manufacture_date:
            manufacture_date = timezone.now().date()
        
        # Check if batch number already exists
        if Batch.objects.filter(batch_number=batch_number).exists():
            messages.error(request, f'Batch number {batch_number} already exists.')
            return redirect('inventory:add_batch', pk=pk)
        
        Batch.objects.create(
            drug=drug,
            batch_number=batch_number,
            quantity=int(quantity),
            purchase_price=Decimal(str(purchase_price)),
            selling_price=Decimal(str(selling_price)),
            manufacture_date=manufacture_date,
            expiry_date=expiry_date,
            supplier=supplier,
            pharmacy=request.pharmacy
        )
        
        messages.success(request, f'Added {quantity} units of {drug.name} to stock.')
        return redirect('inventory:list')
    
    return render(request, 'inventory/add_batch.html', {
        'drug': drug,
        'suppliers': suppliers,
        'today': timezone.now().date()
    })


@login_required
def batch_list(request):
    """List all batches"""
    batches = Batch.objects.select_related('drug', 'supplier').all().order_by('expiry_date')
    
    # Filter by status
    status = request.GET.get('status', '')
    if status == 'expiring':
        batches = batches.filter(
            expiry_date__lte=timezone.now().date() + timedelta(days=30),
            expiry_date__gt=timezone.now().date()
        )
    elif status == 'expired':
        batches = batches.filter(expiry_date__lt=timezone.now().date())
    elif status == 'low_stock':
        batches = batches.filter(quantity__lte=50)
    
    context = {
        'batches': batches,
        'status': status
    }
    return render(request, 'inventory/batch_list.html', context)

@login_required
def batch_detail(request, pk):
    """View batch details"""
    batch = get_object_or_404(Batch.objects.select_related('drug', 'supplier'), pk=pk)
    return render(request, 'inventory/batch_detail.html', {'batch': batch})

@login_required
def supplier_list(request):
    """List all suppliers"""
    suppliers = Supplier.objects.annotate(
        drug_count=Count('batch')
    ).all()
    return render(request, 'inventory/supplier_list.html', {'suppliers': suppliers})

@login_required
def supplier_add(request):
    """Add new supplier"""
    if request.method == 'POST':
        form = SupplierForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Supplier added successfully.')
            return redirect('inventory:supplier_list')
    else:
        form = SupplierForm()
    
    return render(request, 'inventory/supplier_form.html', {'form': form})

@login_required
def stock_alerts(request):
    """View all stock alerts"""
    alerts = StockAlert.objects.select_related('batch__drug').all().order_by('-created_at')
    
    # Filter by type
    alert_type = request.GET.get('type', '')
    if alert_type:
        alerts = alerts.filter(alert_type=alert_type)
    
    # Filter by status
    status = request.GET.get('status', '')
    if status == 'resolved':
        alerts = alerts.filter(is_resolved=True)
    elif status == 'unresolved':
        alerts = alerts.filter(is_resolved=False)
    
    context = {
        'alerts': alerts,
        'alert_type': alert_type,
        'status': status,
        'alert_types': StockAlert.ALERT_TYPES
    }
    return render(request, 'inventory/stock_alerts.html', context)

@login_required
def resolve_alert(request, pk):
    """Mark alert as resolved"""
    alert = get_object_or_404(StockAlert, pk=pk)
    if request.method == 'POST':
        alert.is_resolved = True
        alert.resolved_at = timezone.now()
        alert.save()
        messages.success(request, 'Alert resolved successfully.')
        return redirect('inventory:stock_alerts')
    return render(request, 'inventory/resolve_alert.html', {'alert': alert})



def api_search_drugs(request):
    """API endpoint for drug search - formatted for Select2"""
    query = request.GET.get('q', '')
    
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    # Search for drugs in the current pharmacy
    drugs = Drug.objects.filter(
        Q(name__icontains=query) | Q(generic_name__icontains=query),
        pharmacy=request.pharmacy
    )[:10]
    
    # Format for Select2 - needs 'id' and 'text' fields
    results = []
    for drug in drugs:
        # Check if drug has stock
        has_stock = drug.batches.filter(
            quantity__gt=0, 
            expiry_date__gt=timezone.now().date()
        ).exists()
        
        results.append({
            'id': drug.id,
            'text': f"{drug.name} {drug.strength or ''} - {drug.generic_name or ''}",
            'name': drug.name,
            'generic_name': drug.generic_name,
            'strength': drug.strength,
            'has_stock': has_stock
        })
    
    return JsonResponse({'results': results})


from django.http import JsonResponse

def api_supplier_products(request, supplier_id):
    """API endpoint to get products from a supplier"""
    from .models import Batch
    
    batches = Batch.objects.filter(
        supplier_id=supplier_id
    ).select_related('drug').order_by('-created_at')[:50]
    
    products = []
    for batch in batches:
        products.append({
            'drug_name': batch.drug.name,
            'strength': batch.drug.strength,
            'batch_number': batch.batch_number,
            'quantity': batch.quantity,
            'expiry_date': batch.expiry_date.strftime('%Y-%m-%d')
        })
    
    return JsonResponse({'products': products})