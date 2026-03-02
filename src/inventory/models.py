from django.db import models
from django.utils import timezone
from datetime import timedelta

class Supplier(models.Model):
    name = models.CharField(max_length=200)
    contact_person = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    address = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return self.name

class Drug(models.Model):
    DRUG_FORMS = (
        ('tablet', 'Tablet'),
        ('capsule', 'Capsule'),
        ('liquid', 'Liquid'),
        ('injection', 'Injection'),
        ('cream', 'Cream'),
        ('ointment', 'Ointment'),
        ('inhaler', 'Inhaler'),
    )
    
    name = models.CharField(max_length=200)
    generic_name = models.CharField(max_length=200)
    rxcui = models.CharField(max_length=20, unique=True, null=True, blank=True)
    form = models.CharField(max_length=20, choices=DRUG_FORMS)
    strength = models.CharField(max_length=50)  # e.g., "500mg"
    manufacturer = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    requires_prescription = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['rxcui']),
        ]
    
    def __str__(self):
        return f"{self.name} {self.strength}"

class Batch(models.Model):
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='batches')
    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True)
    batch_number = models.CharField(max_length=100, unique=True)
    quantity = models.PositiveIntegerField(default=0)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    manufacture_date = models.DateField()
    expiry_date = models.DateField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['expiry_date']),
            models.Index(fields=['batch_number']),
        ]
    
    def __str__(self):
        return f"{self.drug.name} - {self.batch_number}"
    
    def is_expired(self):
        return self.expiry_date < timezone.now().date()
    
    def days_until_expiry(self):
        return (self.expiry_date - timezone.now().date()).days
    
    def is_low_stock(self, threshold=50):
        return self.quantity <= threshold

class StockAlert(models.Model):
    ALERT_TYPES = (
        ('low_stock', 'Low Stock'),
        ('expiry', 'Expiring Soon'),
        ('expired', 'Expired'),
    )
    
    batch = models.ForeignKey(Batch, on_delete=models.CASCADE, related_name='alerts')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES)
    message = models.TextField()
    is_resolved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']