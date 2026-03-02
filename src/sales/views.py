from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Sum, Count
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.core.paginator import Paginator
from django.template.loader import render_to_string
from django.views.decorators.http import require_http_methods
import json
from datetime import datetime, timedelta
from .models import Sale, SaleItem, Receipt
from inventory.models import Drug, Batch
from prescriptions.models import Prescription
from .forms import SaleForm, SaleItemForm

@login_required
def pos(request):
    """Point of Sale interface"""
    context = {
        'drugs': Drug.objects.all().order_by('name'),
        'recent_sales': Sale.objects.select_related('pharmacist').all().order_by('-created_at')[:10]
    }
    return render(request, 'sales/pos.html', context)

@login_required
def sale_create(request):
    """Create new sale"""
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # Create sale
        sale = Sale.objects.create(
            invoice_number=generate_invoice_number(),
            pharmacist=request.user,
            subtotal=data['subtotal'],
            discount=data['discount'],
            tax=data['tax'],
            total=data['total'],
            payment_method=data['payment_method'],
            payment_reference=data.get('payment_reference', '')
        )
        
        # Create sale items and update stock
        for item_data in data['items']:
            batch = Batch.objects.get(id=item_data['batch_id'])
            
            SaleItem.objects.create(
                sale=sale,
                batch=batch,
                quantity=item_data['quantity'],
                unit_price=item_data['price'],
                total_price=item_data['total']
            )
            
            # Update stock
            batch.quantity -= item_data['quantity']
            batch.save()
        
        # Create receipt
        receipt = Receipt.objects.create(
            sale=sale,
            receipt_number=f"RCP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        return JsonResponse({
            'success': True,
            'sale_id': sale.id,
            'receipt_id': receipt.id
        })
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def create_from_prescription(request, prescription_id):
    """Create sale from prescription"""
    prescription = get_object_or_404(Prescription, pk=prescription_id)
    
    if prescription.status != 'dispensed':
        messages.error(request, 'Prescription must be dispensed first.')
        return redirect('prescriptions:detail', pk=prescription_id)
    
    if request.method == 'POST':
        data = json.loads(request.body)
        
        # Create sale
        sale = Sale.objects.create(
            invoice_number=generate_invoice_number(),
            prescription=prescription,
            pharmacist=request.user,
            subtotal=data['subtotal'],
            discount=data['discount'],
            tax=data['tax'],
            total=data['total'],
            payment_method=data['payment_method'],
            payment_reference=data.get('payment_reference', '')
        )
        
        # Create sale items from prescription items
        for item in prescription.items.all():
            SaleItem.objects.create(
                sale=sale,
                batch=item.batch,
                quantity=item.quantity,
                unit_price=item.batch.selling_price,
                total_price=item.quantity * item.batch.selling_price
            )
        
        # Create receipt
        receipt = Receipt.objects.create(
            sale=sale,
            receipt_number=f"RCP{datetime.now().strftime('%Y%m%d%H%M%S')}"
        )
        
        messages.success(request, 'Sale completed successfully.')
        return JsonResponse({
            'success': True,
            'sale_id': sale.id,
            'receipt_id': receipt.id
        })
    
    # Calculate totals
    items = []
    subtotal = 0
    for item in prescription.items.all():
        item_total = item.quantity * item.batch.selling_price
        subtotal += item_total
        items.append({
            'drug': item.drug.name,
            'batch': item.batch.batch_number,
            'quantity': item.quantity,
            'price': float(item.batch.selling_price),
            'total': float(item_total)
        })
    
    tax = subtotal * 0.1  # 10% tax
    total = subtotal + tax
    
    context = {
        'prescription': prescription,
        'items': items,
        'subtotal': subtotal,
        'tax': tax,
        'total': total,
        'payment_methods': Sale.PAYMENT_METHODS
    }
    return render(request, 'sales/create_from_rx.html', context)

@login_required
def sale_history(request):
    """View sales history"""
    sales = Sale.objects.select_related('pharmacist', 'prescription').all().order_by('-created_at')
    
    # Filter by date
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')
    if date_from:
        sales = sales.filter(created_at__date__gte=date_from)
    if date_to:
        sales = sales.filter(created_at__date__lte=date_to)
    
    # Filter by payment method
    payment_method = request.GET.get('payment_method', '')
    if payment_method:
        sales = sales.filter(payment_method=payment_method)
    
    # Search by invoice number
    search = request.GET.get('search', '')
    if search:
        sales = sales.filter(invoice_number__icontains=search)
    
    # Pagination
    paginator = Paginator(sales, 20)
    page = request.GET.get('page')
    sales_page = paginator.get_page(page)
    
    # Calculate totals
    total_revenue = sales.aggregate(Sum('total'))['total__sum'] or 0
    total_transactions = sales.count()
    avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
    
    context = {
        'sales': sales_page,
        'date_from': date_from,
        'date_to': date_to,
        'payment_method': payment_method,
        'search': search,
        'payment_methods': Sale.PAYMENT_METHODS,
        'total_revenue': total_revenue,
        'total_transactions': total_transactions,
        'avg_transaction': avg_transaction
    }
    return render(request, 'sales/history.html', context)

@login_required
def sale_detail(request, pk):
    """View sale details"""
    sale = get_object_or_404(
        Sale.objects.select_related('pharmacist', 'prescription', 'receipt'),
        pk=pk
    )
    items = sale.items.select_related('batch__drug').all()
    
    context = {
        'sale': sale,
        'items': items
    }
    return render(request, 'sales/detail.html', context)

@login_required
def receipt(request, pk):
    """View receipt"""
    receipt = get_object_or_404(Receipt.objects.select_related('sale'), pk=pk)
    items = receipt.sale.items.select_related('batch__drug').all()
    
    context = {
        'receipt': receipt,
        'sale': receipt.sale,
        'items': items,
        'pharmacy_name': 'City Pharmacy',
        'pharmacy_address': '123 Main Street, City, State 12345',
        'pharmacy_phone': '(555) 123-4567',
        'pharmacy_email': 'info@citypharmacy.com'
    }
    return render(request, 'sales/receipt.html', context)

@login_required
def print_receipt(request, pk):
    """Print receipt"""
    receipt = get_object_or_404(Receipt, pk=pk)
    receipt.printed = True
    receipt.save()
    
    return redirect('sales:receipt', pk=pk)

@login_required
def email_receipt(request, pk):
    """Email receipt to customer"""
    receipt = get_object_or_404(Receipt, pk=pk)
    
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            # In production, actually send email
            receipt.sent_to_email = True
            receipt.save()
            messages.success(request, f'Receipt sent to {email}')
            return redirect('sales:detail', pk=receipt.sale.id)
    
    return render(request, 'sales/email_receipt.html', {'receipt': receipt})

@login_required
def api_search_drugs(request):
    """API endpoint for drug search in POS"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'results': []})
    
    batches = Batch.objects.filter(
        Q(drug__name__icontains=query) |
        Q(drug__generic_name__icontains=query) |
        Q(batch_number__icontains=query),
        quantity__gt=0,
        expiry_date__gt=timezone.now().date()
    ).select_related('drug').distinct()[:10]
    
    results = [{
        'id': batch.id,
        'drug_id': batch.drug.id,
        'name': batch.drug.name,
        'generic_name': batch.drug.generic_name,
        'strength': batch.drug.strength,
        'batch_number': batch.batch_number,
        'price': float(batch.selling_price),
        'quantity_available': batch.quantity,
        'expiry_date': batch.expiry_date.strftime('%Y-%m-%d')
    } for batch in batches]
    
    return JsonResponse({'results': results})

@login_required
@require_http_methods(["POST"])
def api_calculate_total(request):
    """Calculate total with tax and discount"""
    data = json.loads(request.body)
    items = data.get('items', [])
    discount = float(data.get('discount', 0))
    
    subtotal = 0
    for item in items:
        subtotal += item['quantity'] * item['price']
    
    tax = subtotal * 0.1  # 10% tax
    total = subtotal + tax - discount
    
    return JsonResponse({
        'subtotal': subtotal,
        'tax': tax,
        'discount': discount,
        'total': total
    })

def generate_invoice_number():
    """Generate unique invoice number"""
    from datetime import datetime
    import random
    
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    random_num = random.randint(1000, 9999)
    return f"INV{timestamp}{random_num}"