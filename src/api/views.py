from rest_framework import viewsets, status
from rest_framework.decorators import api_view, action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.db.models import Q, Sum, Count
from django.utils import timezone
from datetime import timedelta
from inventory.models import Drug, Batch
from patients.models import Patient
from prescriptions.models import Prescription
from sales.models import Sale
from .serializers import (
    DrugSerializer, PatientSerializer, 
    PrescriptionSerializer, SaleSerializer
)

class DrugViewSet(viewsets.ModelViewSet):
    """API endpoint for drugs"""
    queryset = Drug.objects.all()
    serializer_class = DrugSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Drug.objects.all()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(name__icontains=search) |
                Q(generic_name__icontains=search)
            )
        return queryset
    
    @action(detail=True, methods=['get'])
    def batches(self, request, pk=None):
        """Get all batches for a drug"""
        drug = self.get_object()
        batches = drug.batches.filter(quantity__gt=0)
        data = [{
            'id': b.id,
            'batch_number': b.batch_number,
            'quantity': b.quantity,
            'expiry_date': b.expiry_date,
            'selling_price': float(b.selling_price)
        } for b in batches]
        return Response(data)
    
    @action(detail=False, methods=['get'])
    def low_stock(self, request):
        """Get low stock drugs"""
        threshold = int(request.query_params.get('threshold', 50))
        drugs = Drug.objects.annotate(
            total_stock=Sum('batches__quantity')
        ).filter(total_stock__lte=threshold)
        serializer = self.get_serializer(drugs, many=True)
        return Response(serializer.data)

class PatientViewSet(viewsets.ModelViewSet):
    """API endpoint for patients"""
    queryset = Patient.objects.all()
    serializer_class = PatientSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Patient.objects.all()
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(phone__icontains=search)
            )
        return queryset
    
    @action(detail=True, methods=['get'])
    def prescriptions(self, request, pk=None):
        """Get all prescriptions for a patient"""
        patient = self.get_object()
        prescriptions = patient.prescriptions.all().order_by('-created_at')
        serializer = PrescriptionSerializer(prescriptions, many=True)
        return Response(serializer.data)

class PrescriptionViewSet(viewsets.ModelViewSet):
    """API endpoint for prescriptions"""
    queryset = Prescription.objects.all()
    serializer_class = PrescriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Prescription.objects.all()
        status = self.request.query_params.get('status', None)
        if status:
            queryset = queryset.filter(status=status)
        return queryset
    
    @action(detail=True, methods=['post'])
    def verify(self, request, pk=None):
        """Verify a prescription"""
        prescription = self.get_object()
        prescription.status = 'verified'
        prescription.verified_by = request.user
        prescription.verified_at = timezone.now()
        prescription.save()
        return Response({'status': 'verified'})
    
    @action(detail=True, methods=['post'])
    def dispense(self, request, pk=None):
        """Dispense a prescription"""
        prescription = self.get_object()
        if prescription.status != 'verified':
            return Response(
                {'error': 'Prescription must be verified first'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check stock
        for item in prescription.items.all():
            if not item.batch or item.batch.quantity < item.quantity:
                return Response(
                    {'error': f'Insufficient stock for {item.drug.name}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Update stock
        for item in prescription.items.all():
            if item.batch:
                item.batch.quantity -= item.quantity
                item.batch.save()
        
        prescription.status = 'dispensed'
        prescription.dispensed_at = timezone.now()
        prescription.save()
        
        return Response({'status': 'dispensed'})

class SaleViewSet(viewsets.ModelViewSet):
    """API endpoint for sales"""
    queryset = Sale.objects.all()
    serializer_class = SaleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        queryset = Sale.objects.all()
        date_from = self.request.query_params.get('date_from', None)
        date_to = self.request.query_params.get('date_to', None)
        
        if date_from:
            queryset = queryset.filter(created_at__date__gte=date_from)
        if date_to:
            queryset = queryset.filter(created_at__date__lte=date_to)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def today(self, request):
        """Get today's sales"""
        today = timezone.now().date()
        sales = self.queryset.filter(created_at__date=today)
        serializer = self.get_serializer(sales, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get sales summary"""
        days = int(request.query_params.get('days', 30))
        since = timezone.now() - timedelta(days=days)
        
        sales = self.queryset.filter(created_at__gte=since)
        total = sales.aggregate(Sum('total'))['total__sum'] or 0
        count = sales.count()
        
        return Response({
            'period': f'last_{days}_days',
            'total_sales': float(total),
            'transaction_count': count,
            'average_transaction': float(total / count) if count > 0 else 0
        })

@api_view(['POST'])
def check_interactions(request):
    """Check drug interactions"""
    from prescriptions.interaction_engine import DrugInteractionEngine
    
    drug_ids = request.data.get('drug_ids', [])
    patient_id = request.data.get('patient_id')
    
    if not drug_ids or not patient_id:
        return Response(
            {'error': 'drug_ids and patient_id are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        patient = Patient.objects.get(id=patient_id)
        drugs = Drug.objects.filter(id__in=drug_ids)
        
        # Create temporary prescription for checking
        from collections import namedtuple
        TempItem = namedtuple('TempItem', ['drug'])
        temp_items = [TempItem(drug=d) for d in drugs]
        
        temp_prescription = type('TempPrescription', (), {
            'patient': patient,
            'items': temp_items
        })
        
        engine = DrugInteractionEngine()
        alerts = engine.check_prescription(temp_prescription)
        
        return Response({
            'alerts': alerts,
            'has_interactions': len(alerts) > 0,
            'high_risk_count': sum(1 for a in alerts if a['severity'] == 'high')
        })
        
    except Patient.DoesNotExist:
        return Response(
            {'error': 'Patient not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(['GET'])
def dashboard_stats(request):
    """Get dashboard statistics"""
    today = timezone.now().date()
    week_ago = today - timedelta(days=7)
    
    stats = {
        'total_patients': Patient.objects.count(),
        'total_prescriptions': Prescription.objects.count(),
        'pending_prescriptions': Prescription.objects.filter(status='pending').count(),
        'today_sales': Sale.objects.filter(created_at__date=today).aggregate(
            total=Sum('total'),
            count=Count('id')
        ),
        'week_sales': Sale.objects.filter(created_at__date__gte=week_ago).aggregate(
            total=Sum('total'),
            count=Count('id')
        ),
        'low_stock_count': Batch.objects.filter(quantity__lte=50, quantity__gt=0).count(),
        'expiring_count': Batch.objects.filter(
            expiry_date__lte=today + timedelta(days=30),
            expiry_date__gt=today,
            quantity__gt=0
        ).count()
    }
    
    return Response(stats)

@api_view(['GET'])
def search_drugs(request):
    """Search drugs"""
    query = request.query_params.get('q', '')
    if len(query) < 2:
        return Response({'results': []})
    
    drugs = Drug.objects.filter(
        Q(name__icontains=query) |
        Q(generic_name__icontains=query)
    )[:10]
    
    results = [{
        'id': d.id,
        'name': d.name,
        'generic_name': d.generic_name,
        'strength': d.strength,
        'form': d.form
    } for d in drugs]
    
    return Response({'results': results})

@api_view(['GET'])
def search_patients(request):
    """Search patients"""
    query = request.query_params.get('q', '')
    if len(query) < 2:
        return Response({'patients': []})
    
    patients = Patient.objects.filter(
        Q(first_name__icontains=query) |
        Q(last_name__icontains=query) |
        Q(phone__icontains=query)
    )[:10]
    
    results = [{
        'id': p.id,
        'name': p.full_name,
        'age': p.age,
        'phone': p.phone,
        'allergies': p.allergies
    } for p in patients]
    
    return Response({'patients': results})