from django.db import models
from django.contrib.auth.models import User
from patients.models import Patient
from inventory.models import Drug, Batch

class Prescription(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('dispensed', 'Dispensed'),
        ('cancelled', 'Cancelled'),
        ('on_hold', 'On Hold'),
    )
    
    prescription_number = models.CharField(max_length=50, unique=True)
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='prescriptions')
    prescribed_by = models.CharField(max_length=200)  # Doctor's name
    prescribed_date = models.DateField()
    pharmacist = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='processed_prescriptions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"RX-{self.prescription_number} - {self.patient.full_name}"

class PrescriptionItem(models.Model):
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='items')
    drug = models.ForeignKey(Drug, on_delete=models.CASCADE)
    batch = models.ForeignKey(Batch, on_delete=models.SET_NULL, null=True)
    dosage = models.CharField(max_length=100)  # e.g., "1 tablet"
    frequency = models.CharField(max_length=100)  # e.g., "twice daily"
    duration = models.CharField(max_length=50)  # e.g., "7 days"
    quantity = models.PositiveIntegerField()
    instructions = models.TextField(blank=True)
    substituted = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.drug.name} - {self.dosage}"

class InteractionLog(models.Model):
    SEVERITY_CHOICES = (
        ('low', 'Low Risk'),
        ('moderate', 'Moderate Risk'),
        ('high', 'High Risk'),
    )
    
    prescription = models.ForeignKey(Prescription, on_delete=models.CASCADE, related_name='interaction_logs')
    drug_1 = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='interactions_as_drug1')
    drug_2 = models.ForeignKey(Drug, on_delete=models.CASCADE, related_name='interactions_as_drug2', null=True, blank=True)
    interaction_type = models.CharField(max_length=50)  # drug-drug, drug-allergy, drug-food, etc.
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES)
    description = models.TextField()
    recommendation = models.TextField()
    overridden_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='overridden_interactions')
    overridden_at = models.DateTimeField(null=True, blank=True)
    override_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']