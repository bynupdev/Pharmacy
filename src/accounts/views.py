from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import timedelta
from prescriptions.models import Prescription
from inventory.models import Batch, StockAlert
from sales.models import Sale
from .models import UserProfile
from .forms import UserForm, UserProfileForm

@login_required
def dashboard(request):
    """Main dashboard with key metrics and alerts"""
    context = {}
    
    # Get counts
    context['total_patients'] = User.objects.filter(is_staff=False).count()
    context['total_prescriptions'] = Prescription.objects.count()
    context['pending_prescriptions'] = Prescription.objects.filter(status='pending').count()
    context['low_stock_alerts'] = StockAlert.objects.filter(alert_type='low_stock', is_resolved=False).count()
    
    # Recent prescriptions
    context['recent_prescriptions'] = Prescription.objects.select_related('patient').order_by('-created_at')[:5]
    
    # Today's sales
    today = timezone.now().date()
    today_sales = Sale.objects.filter(created_at__date=today)
    context['today_sales_count'] = today_sales.count()
    context['today_revenue'] = today_sales.aggregate(Sum('total'))['total__sum'] or 0
    
    # Stock alerts
    context['expiring_soon'] = Batch.objects.filter(
        expiry_date__lte=timezone.now().date() + timedelta(days=30),
        quantity__gt=0
    ).select_related('drug')[:5]
    
    return render(request, 'dashboard.html', context)

@login_required
def profile(request):
    """User profile view"""
    user = request.user
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'Profile updated successfully.')
            return redirect('profile')
    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=user.profile)
    
    return render(request, 'accounts/profile.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
@user_passes_test(lambda u: u.profile.role == 'admin')
def user_list(request):
    """List all users (admin only)"""
    users = User.objects.select_related('profile').all()
    return render(request, 'accounts/user_list.html', {'users': users})

@login_required
@user_passes_test(lambda u: u.profile.role == 'admin')
def user_create(request):
    """Create new user (admin only)"""
    if request.method == 'POST':
        user_form = UserForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()
            profile = profile_form.save(commit=False)
            profile.user = user
            profile.save()
            messages.success(request, 'User created successfully.')
            return redirect('user_list')
    else:
        user_form = UserForm()
        profile_form = UserProfileForm()
    
    return render(request, 'accounts/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form
    })

@login_required
@user_passes_test(lambda u: u.profile.role == 'admin')
def user_edit(request, pk):
    """Edit user (admin only)"""
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=user.profile)
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, 'User updated successfully.')
            return redirect('user_list')
    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=user.profile)
    
    return render(request, 'accounts/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'edit_mode': True
    })

@login_required
@user_passes_test(lambda u: u.profile.role == 'admin')
def user_delete(request, pk):
    """Delete user (admin only)"""
    user = get_object_or_404(User, pk=pk)
    if request.method == 'POST':
        user.delete()
        messages.success(request, 'User deleted successfully.')
        return redirect('user_list')
    return render(request, 'accounts/user_confirm_delete.html', {'user': user})