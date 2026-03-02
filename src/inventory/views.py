from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Sum
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
from .models import Drug, Batch, Supplier, StockAlert
from .forms import DrugForm, BatchForm, SupplierForm

@login_required
def inventory_list(request):
    """List all drugs with current stock levels"""
    drugs = Drug.objects.all().prefetch_related('batches')
    
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

@login_required
def inventory_add(request):
    """Add new drug"""
    if request.method == 'POST':
        form = DrugForm(request.POST)
        if form.is_valid():
            drug = form.save()
            messages.success(request, f'Drug {drug.name} added successfully.')
            return redirect('inventory:detail', pk=drug.pk)
    else:
        form = DrugForm()
    
    return render(request, 'inventory/add_edit.html', {'form': form, 'edit_mode': False})

@login_required
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
def inventory_delete(request, pk):
    """Delete drug"""
    drug = get_object_or_404(Drug, pk=pk)
    if request.method == 'POST':
        drug.delete()
        messages.success(request, 'Drug deleted successfully.')
        return redirect('inventory:list')
    return render(request, 'inventory/confirm_delete.html', {'drug': drug})

@login_required
def add_batch(request, pk):
    """Add new batch for a drug"""
    drug = get_object_or_404(Drug, pk=pk)
    
    if request.method == 'POST':
        form = BatchForm(request.POST)
        if form.is_valid():
            batch = form.save(commit=False)
            batch.drug = drug
            batch.save()
            
            # Check if expiry alert needed
            if batch.days_until_expiry() <= 30 and batch.days_until_expiry() > 0:
                StockAlert.objects.create(
                    batch=batch,
                    alert_type='expiry',
                    message=f'Batch {batch.batch_number} of {drug.name} expires in {batch.days_until_expiry()} days'
                )
            
            messages.success(request, f'Batch {batch.batch_number} added successfully.')
            return redirect('inventory:detail', pk=drug.pk)
    else:
        form = BatchForm(initial={'drug': drug})
    
    return render(request, 'inventory/add_batch.html', {
        'form': form,
        'drug': drug
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

@login_required
def api_search_drugs(request):
    """API endpoint for drug search"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    drugs = Drug.objects.filter(
        Q(name__icontains=query) | Q(generic_name__icontains=query)
    )[:10]
    
    results = [{
        'id': drug.id,
        'name': drug.name,
        'generic_name': drug.generic_name,
        'strength': drug.strength,
        'form': drug.form,
        'rxcui': drug.rxcui
    } for drug in drugs]
    
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