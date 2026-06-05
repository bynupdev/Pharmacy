from datetime import timezone

from django.db import models
from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

class Pharmacy(models.Model):
    """Simple pharmacy/organization"""
    name = models.CharField(max_length=200, unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural = "Pharmacies"
    

class UserProfile(models.Model):
    USER_ROLES = (
        ('admin', 'Administrator'),
        ('pharmacist', 'Pharmacist'),
        ('technician', 'Pharmacy Technician'),
    )
    
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=20, choices=USER_ROLES, default='pharmacist')
    license_number = models.CharField(max_length=50, blank=True)
    phone_number = models.CharField(max_length=15)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, null=True, blank=True)
    is_approved = models.BooleanField(default=False)  # Admin must approve
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.get_full_name()} - {self.get_role_display() if self.role else 'Pending'}"

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create UserProfile automatically when a new User is created"""
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    """Save UserProfile when User is saved"""
    # Use try/except to handle cases where profile might not exist yet
    try:
        instance.profile.save()
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist (for existing users)
        UserProfile.objects.create(user=instance)


class PendingUserRequest(models.Model):
    """Stores user registration requests for existing pharmacies"""
    STATUS_CHOICES = (
        ('pending', 'Pending Approval'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    )
    
    email = models.EmailField()
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    requested_pharmacy_name = models.CharField(max_length=200)
    pharmacy = models.ForeignKey(Pharmacy, on_delete=models.CASCADE, related_name='pending_requests')
    requested_role = models.CharField(max_length=20, choices=UserProfile.USER_ROLES, default='technician')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    rejection_reason = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Link to the created user once approved
    created_user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='pending_request')
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} -> {self.pharmacy.name} ({self.status})"
    
    class Meta:
        ordering = ['-created_at']

class PasswordResetToken(models.Model):
    """Simple model for password reset tokens"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='reset_tokens')
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    
    def is_valid(self):
        return not self.used and self.expires_at > timezone.now()
    
    def __str__(self):
        return f"Reset token for {self.user.username}"