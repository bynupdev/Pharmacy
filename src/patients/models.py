from django.db import models
from django.contrib.auth.models import User
from datetime import date

class Patient(models.Model):
    BLOOD_TYPES = (
        ('A+', 'A+'), ('A-', 'A-'),
        ('B+', 'B+'), ('B-', 'B-'),
        ('AB+', 'AB+'), ('AB-', 'AB-'),
        ('O+', 'O+'), ('O-', 'O-'),
    )
    
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    date_of_birth = models.DateField()
    gender = models.CharField(max_length=10, choices=(('M', 'Male'), ('F', 'Female'), ('O', 'Other')))
    phone = models.CharField(max_length=15)
    email = models.EmailField(blank=True)
    address = models.TextField()
    blood_type = models.CharField(max_length=3, choices=BLOOD_TYPES, blank=True)
    allergies = models.TextField(blank=True, help_text="List all known allergies")
    chronic_conditions = models.TextField(blank=True, help_text="List all chronic conditions")
    current_medications = models.TextField(blank=True, help_text="List current medications")
    emergency_contact_name = models.CharField(max_length=200)
    emergency_contact_phone = models.CharField(max_length=15)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        indexes = [
            models.Index(fields=['last_name', 'first_name']),
            models.Index(fields=['phone']),
        ]
    
    def __str__(self):
        return f"{self.last_name}, {self.first_name}"
    
    @property
    def age(self):
        today = date.today()
        return today.year - self.date_of_birth.year - (
            (today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day)
        )
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

class Allergy(models.Model):
    patient = models.ForeignKey(Patient, on_delete=models.CASCADE, related_name='allergy_list')
    allergen = models.CharField(max_length=200)
    severity = models.CharField(max_length=20, choices=(
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('severe', 'Severe'),
    ))
    reaction = models.TextField()
    diagnosed_date = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.patient.full_name} - {self.allergen}"