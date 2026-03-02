from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from django.http import HttpResponse
from datetime import datetime, timedelta
import csv
import json
from inventory.models import Drug, Batch, StockAlert
from sales.models import Sale, SaleItem
from prescriptions.models import Prescription, InteractionLog

# Try to import pandas, but provide fallback if not available
try:
    import pandas as pd
    import numpy as np
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("Pandas not installed. Using basic reporting.")

# @login_required
def report_dashboard(request):
    """Main reports dashboard"""
    context = {}
    
    # Sales summary
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    
    context['today_sales'] = Sale.objects.filter(created_at__date=today).aggregate(
        total=Sum('total'), count=Count('id')
    )
    context['week_sales'] = Sale.objects.filter(created_at__date__gte=week_ago).aggregate(
        total=Sum('total'), count=Count('id')
    )
    context['month_sales'] = Sale.objects.filter(created_at__date__gte=month_ago).aggregate(
        total=Sum('total'), count=Count('id')
    )
    
    # Inventory alerts
    context['low_stock_count'] = StockAlert.objects.filter(
        alert_type='low_stock', is_resolved=False
    ).count()
    context['expiring_count'] = StockAlert.objects.filter(
        alert_type='expiry', is_resolved=False
    ).count()
    
    # Interaction stats
    context['interaction_count'] = InteractionLog.objects.filter(
        created_at__date__gte=week_ago
    ).count()
    context['high_risk_count'] = InteractionLog.objects.filter(
        severity='high', created_at__date__gte=week_ago
    ).count()
    
    return render(request, 'reports/dashboard.html', context)

@login_required
def inventory_report(request):
    """Inventory valuation and status report"""
    # Get all drugs with their batches
    drugs = Drug.objects.all().prefetch_related('batches')
    
    report_data = []
    total_value = 0
    total_cost = 0
    
    for drug in drugs:
        batches = drug.batches.all()
        total_quantity = sum(b.quantity for b in batches)
        total_value += sum(b.quantity * b.selling_price for b in batches)
        total_cost += sum(b.quantity * b.purchase_price for b in batches)
        
        # Get nearest expiry
        valid_batches = [b for b in batches if b.quantity > 0]
        nearest_expiry = min([b.expiry_date for b in valid_batches], default=None) if valid_batches else None
        
        report_data.append({
            'drug': drug,
            'total_quantity': total_quantity,
            'batches_count': batches.count(),
            'nearest_expiry': nearest_expiry,
            'total_value': sum(b.quantity * b.selling_price for b in batches),
            'total_cost': sum(b.quantity * b.purchase_price for b in batches),
            'potential_profit': sum(b.quantity * (b.selling_price - b.purchase_price) for b in batches)
        })
    
    context = {
        'report_data': report_data,
        'total_value': total_value,
        'total_cost': total_cost,
        'total_profit': total_value - total_cost,
        'drug_count': drugs.count(),
        'report_date': timezone.now()
    }
    return render(request, 'reports/inventory.html', context)

@login_required
def sales_report(request):
    """Sales analysis report"""
    # Get date range
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
    
    sales = Sale.objects.filter(created_at__date__gte=date_from, created_at__date__lte=date_to)
    
    # Daily sales breakdown
    daily_sales = sales.extra({'date': "date(created_at)"}).values('date').annotate(
        total=Sum('total'),
        count=Count('id')
    ).order_by('date')
    
    # Payment method breakdown
    payment_methods = sales.values('payment_method').annotate(
        total=Sum('total'),
        count=Count('id')
    )
    
    # Top selling drugs
    top_drugs = SaleItem.objects.filter(
        sale__created_at__date__gte=date_from,
        sale__created_at__date__lte=date_to
    ).values('batch__drug__name').annotate(
        total_quantity=Sum('quantity'),
        total_revenue=Sum('total_price')
    ).order_by('-total_quantity')[:10]
    
    # Summary stats
    total_revenue = sales.aggregate(Sum('total'))['total__sum'] or 0
    total_transactions = sales.count()
    avg_transaction = total_revenue / total_transactions if total_transactions > 0 else 0
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'daily_sales': daily_sales,
        'payment_methods': payment_methods,
        'top_drugs': top_drugs,
        'total_revenue': total_revenue,
        'total_transactions': total_transactions,
        'avg_transaction': avg_transaction,
        'payment_method_choices': Sale.PAYMENT_METHODS
    }
    
    # If pandas is available, create charts
    if PANDAS_AVAILABLE:
        # Convert to pandas for charting
        df = pd.DataFrame(list(daily_sales))
        if not df.empty:
            context['chart_data'] = df.to_json(orient='records')
    
    return render(request, 'reports/sales.html', context)

@login_required
def expiry_report(request):
    """Drug expiry report"""
    today = timezone.now().date()
    
    # Expiring in next 30 days
    expiring_soon = Batch.objects.filter(
        expiry_date__gt=today,
        expiry_date__lte=today + timedelta(days=30),
        quantity__gt=0
    ).select_related('drug', 'supplier').order_by('expiry_date')
    
    # Already expired
    expired = Batch.objects.filter(
        expiry_date__lt=today,
        quantity__gt=0
    ).select_related('drug', 'supplier').order_by('expiry_date')
    
    # Value at risk
    expiring_value = sum(b.quantity * b.purchase_price for b in expiring_soon)
    expired_value = sum(b.quantity * b.purchase_price for b in expired)
    
    context = {
        'expiring_soon': expiring_soon,
        'expired': expired,
        'expiring_count': expiring_soon.count(),
        'expired_count': expired.count(),
        'expiring_value': expiring_value,
        'expired_value': expired_value,
        'report_date': today
    }
    return render(request, 'reports/expiry.html', context)

@login_required
def low_stock_report(request):
    """Low stock items report"""
    threshold = int(request.GET.get('threshold', 50))
    
    low_stock_batches = Batch.objects.filter(
        quantity__lte=threshold,
        quantity__gt=0
    ).select_related('drug', 'supplier').order_by('quantity')
    
    # Group by drug
    low_stock_drugs = {}
    for batch in low_stock_batches:
        if batch.drug.id not in low_stock_drugs:
            low_stock_drugs[batch.drug.id] = {
                'drug': batch.drug,
                'total_quantity': 0,
                'batches': []
            }
        low_stock_drugs[batch.drug.id]['total_quantity'] += batch.quantity
        low_stock_drugs[batch.drug.id]['batches'].append(batch)
    
    context = {
        'low_stock_drugs': low_stock_drugs.values(),
        'threshold': threshold,
        'total_items': low_stock_batches.count()
    }
    return render(request, 'reports/low_stock.html', context)

@login_required
def interaction_report(request):
    """Drug interaction frequency report"""
    # Get date range
    date_from = request.GET.get('date_from', (timezone.now() - timedelta(days=30)).strftime('%Y-%m-%d'))
    date_to = request.GET.get('date_to', timezone.now().strftime('%Y-%m-%d'))
    
    interactions = InteractionLog.objects.filter(
        created_at__date__gte=date_from,
        created_at__date__lte=date_to
    )
    
    # Severity breakdown
    severity_counts = interactions.values('severity').annotate(count=Count('id'))
    
    # Type breakdown
    type_counts = interactions.values('interaction_type').annotate(count=Count('id'))
    
    # Most common drug pairs
    common_pairs = interactions.exclude(drug_2__isnull=True).values(
        'drug_1__name', 'drug_2__name'
    ).annotate(count=Count('id')).order_by('-count')[:10]
    
    # Override statistics
    overridden_count = interactions.filter(overridden_by__isnull=False).count()
    override_rate = (overridden_count / interactions.count() * 100) if interactions.count() > 0 else 0
    
    context = {
        'date_from': date_from,
        'date_to': date_to,
        'total_interactions': interactions.count(),
        'severity_counts': severity_counts,
        'type_counts': type_counts,
        'common_pairs': common_pairs,
        'overridden_count': overridden_count,
        'override_rate': override_rate,
        'severity_choices': InteractionLog.SEVERITY_CHOICES
    }
    return render(request, 'reports/interactions.html', context)

@login_required
def export_report(request, report_type):
    """Export reports as CSV"""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="{report_type}_report_{datetime.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    if report_type == 'inventory':
        writer.writerow(['Drug Name', 'Generic Name', 'Total Quantity', 'Batches', 'Total Value', 'Nearest Expiry'])
        drugs = Drug.objects.all().prefetch_related('batches')
        for drug in drugs:
            batches = drug.batches.all()
            total_quantity = sum(b.quantity for b in batches)
            total_value = sum(b.quantity * b.selling_price for b in batches)
            valid_batches = [b for b in batches if b.quantity > 0]
            nearest_expiry = min([b.expiry_date for b in valid_batches], default='N/A') if valid_batches else 'N/A'
            writer.writerow([
                drug.name,
                drug.generic_name,
                total_quantity,
                batches.count(),
                f"${total_value:.2f}",
                nearest_expiry
            ])
    
    elif report_type == 'sales':
        writer.writerow(['Date', 'Invoice #', 'Items', 'Subtotal', 'Tax', 'Total', 'Payment Method'])
        sales = Sale.objects.all().order_by('-created_at')
        for sale in sales:
            writer.writerow([
                sale.created_at.strftime('%Y-%m-%d %H:%M'),
                sale.invoice_number,
                sale.items.count(),
                f"${sale.subtotal:.2f}",
                f"${sale.tax:.2f}",
                f"${sale.total:.2f}",
                sale.get_payment_method_display()
            ])
    
    elif report_type == 'expiry':
        writer.writerow(['Drug', 'Batch', 'Quantity', 'Expiry Date', 'Days Until Expiry', 'Supplier'])
        batches = Batch.objects.filter(expiry_date__gt=timezone.now().date()).order_by('expiry_date')
        for batch in batches:
            writer.writerow([
                batch.drug.name,
                batch.batch_number,
                batch.quantity,
                batch.expiry_date.strftime('%Y-%m-%d'),
                batch.days_until_expiry(),
                batch.supplier.name if batch.supplier else 'N/A'
            ])
    
    elif report_type == 'interactions':
        writer.writerow(['Date', 'Prescription #', 'Drug 1', 'Drug 2', 'Type', 'Severity', 'Overridden'])
        interactions = InteractionLog.objects.select_related('prescription', 'drug_1', 'drug_2').all()
        for interaction in interactions:
            writer.writerow([
                interaction.created_at.strftime('%Y-%m-%d %H:%M'),
                interaction.prescription.prescription_number,
                interaction.drug_1.name if interaction.drug_1 else 'N/A',
                interaction.drug_2.name if interaction.drug_2 else 'N/A',
                interaction.interaction_type,
                interaction.severity.upper(),
                'Yes' if interaction.overridden_by else 'No'
            ])
    
    return response