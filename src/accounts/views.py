from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.forms import PasswordChangeForm
from django.db.models import Q, Count, Sum
from django.utils import timezone
from django.core.paginator import Paginator
from django.urls import reverse
from django.http import JsonResponse
from datetime import timedelta

from prescriptions.models import Prescription
from inventory.models import Batch, StockAlert
from sales.models import Sale
from .models import UserProfile, PasswordResetToken
from .forms import (
    UserForm, UserProfileForm, LoginForm, 
    UserRegistrationForm, PasswordResetRequestForm,
    SetPasswordForm
)
from .utils import send_password_reset_email, generate_reset_token

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import check_password

def login_view(request):
    """Fixed login view"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            
            # Method 1: Use Django's authenticate
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                if user.is_active:
                    login(request, user)
                    messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                    
                    next_url = request.GET.get('next')
                    if next_url:
                        return redirect(next_url)
                    return redirect('dashboard')
                else:
                    messages.error(request, 'This account is disabled. Contact administrator.')
            else:
                # Method 2: Manual check for debugging
                try:
                    user_obj = User.objects.get(username=username)
                    password_check = check_password(password, user_obj.password)
                    if password_check:
                        messages.error(request, f"Password is correct but authenticate failed. Is user active? {user_obj.is_active}")
                    else:
                        messages.error(request, "Password is incorrect")
                except User.DoesNotExist:
                    messages.error(request, f"User '{username}' does not exist")
        else:
            messages.error(request, 'Invalid form data. Please check your input.')
    
    form = LoginForm()
    return render(request, 'accounts/login.html', {'form': form})

def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('login')

def register(request):
    """Simple registration without email verification"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()  # This triggers the signal to create UserProfile
            
            # Don't create UserProfile here - the signal already did!
            # Just update the profile with additional data
            profile = user.profile  # Get the profile created by signal
            profile.role = form.cleaned_data.get('role', 'technician')
            profile.phone_number = form.cleaned_data.get('phone_number', '')
            profile.license_number = form.cleaned_data.get('license_number', '')
            profile.save()
            
            messages.success(request, 'Account created successfully! You can now log in.')
            return redirect('login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})

def password_reset_request(request):
    """Request password reset"""
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            try:
                user = User.objects.get(email=email)
                
                # Create reset token
                token = generate_reset_token()
                expires_at = timezone.now() + timedelta(hours=24)
                
                reset_token = PasswordResetToken.objects.create(
                    user=user,
                    token=token,
                    expires_at=expires_at
                )
                
                # Build reset URL
                reset_url = request.build_absolute_uri(
                    reverse('password_reset_confirm', kwargs={'token': token})
                )
                
                # Send email
                send_password_reset_email(email, reset_url, user.username)
                
                messages.success(request, 'Password reset link has been sent to your email.')
            except User.DoesNotExist:
                # Don't reveal that user doesn't exist
                messages.success(request, 'If an account exists with this email, you will receive a password reset link.')
            return redirect('login')
    else:
        form = PasswordResetRequestForm()
    
    return render(request, 'accounts/password_reset_request.html', {'form': form})

def password_reset_confirm(request, token):
    """Confirm password reset and set new password"""
    try:
        reset_token = PasswordResetToken.objects.get(token=token, used=False)
        if not reset_token.is_valid():
            messages.error(request, 'This password reset link has expired.')
            return redirect('password_reset')
    except PasswordResetToken.DoesNotExist:
        messages.error(request, 'Invalid password reset link.')
        return redirect('password_reset')
    
    if request.method == 'POST':
        form = SetPasswordForm(request.POST)
        if form.is_valid():
            user = reset_token.user
            user.set_password(form.cleaned_data['new_password1'])
            user.save()
            
            # Mark token as used
            reset_token.used = True
            reset_token.save()
            
            messages.success(request, 'Password reset successful! You can now log in.')
            return redirect('login')
    else:
        form = SetPasswordForm()
    
    return render(request, 'accounts/password_reset_confirm.html', {'form': form, 'token': token})

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
    
    # Get user activity
    recent_activity = []
    
    prescriptions = Prescription.objects.filter(pharmacist=user)[:5]
    for rx in prescriptions:
        recent_activity.append({
            'action': f'Processed prescription #{rx.prescription_number}',
            'time': rx.created_at,
        })
    
    sales = Sale.objects.filter(pharmacist=user)[:5]
    for sale in sales:
        recent_activity.append({
            'action': f'Completed sale #{sale.invoice_number} - ${sale.total}',
            'time': sale.created_at,
        })
    
    recent_activity.sort(key=lambda x: x['time'], reverse=True)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form,
        'recent_activity': recent_activity[:10],
    }
    return render(request, 'accounts/profile.html', context)

@login_required
def change_password(request):
    """Change user password"""
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Your password was successfully updated!')
            return redirect('profile')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PasswordChangeForm(request.user)
    
    return render(request, 'accounts/change_password.html', {'form': form})

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

# Admin Views
@login_required
def user_list(request):
    """List all users (admin only)"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    users = User.objects.select_related('profile').all().order_by('-date_joined')
    
    # Filters
    role = request.GET.get('role', '')
    if role:
        users = users.filter(profile__role=role)
    
    status = request.GET.get('status', '')
    if status == 'active':
        users = users.filter(is_active=True)
    elif status == 'inactive':
        users = users.filter(is_active=False)
    
    # Search
    search = request.GET.get('search', '')
    if search:
        users = users.filter(
            Q(username__icontains=search) |
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(email__icontains=search)
        )
    
    # Pagination
    paginator = Paginator(users, 20)
    page = request.GET.get('page')
    users_page = paginator.get_page(page)
    
    context = {
        'users': users_page,
        'role_filter': role,
        'status_filter': status,
        'search': search,
        'role_choices': UserProfile.USER_ROLES,
    }
    return render(request, 'accounts/user_list.html', context)

@login_required
def user_create(request):
    """Create new user (admin only)"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    if request.method == 'POST':
        user_form = UserRegistrationForm(request.POST)
        profile_form = UserProfileForm(request.POST)
        
        if user_form.is_valid() and profile_form.is_valid():
            user = user_form.save()  # Signal creates UserProfile
            
            # Update the profile with form data
            profile = user.profile
            profile.role = profile_form.cleaned_data['role']
            profile.phone_number = profile_form.cleaned_data['phone_number']
            profile.license_number = profile_form.cleaned_data['license_number']
            profile.save()
            
            messages.success(request, f'User {user.username} created successfully.')
            return redirect('user_list')
    else:
        user_form = UserRegistrationForm()
        profile_form = UserProfileForm()
    
    return render(request, 'accounts/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'edit_mode': False
    })


@login_required
def user_edit(request, pk):
    """Edit user (admin only)"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=user)
        profile_form = UserProfileForm(request.POST, instance=user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            messages.success(request, f'User {user.username} updated successfully.')
            return redirect('user_list')
    else:
        user_form = UserForm(instance=user)
        profile_form = UserProfileForm(instance=user.profile)
    
    return render(request, 'accounts/user_form.html', {
        'user_form': user_form,
        'profile_form': profile_form,
        'edit_mode': True,
        'edit_user': user
    })

@login_required
def user_toggle_active(request, pk):
    """Toggle user active status"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    if user == request.user:
        messages.error(request, 'You cannot deactivate your own account.')
        return redirect('user_list')
    
    user.is_active = not user.is_active
    user.save()
    
    status = 'activated' if user.is_active else 'deactivated'
    messages.success(request, f'User {user.username} {status} successfully.')
    return redirect('user_list')

@login_required
def user_delete(request, pk):
    """Delete user (admin only)"""
    if request.user.profile.role != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    user = get_object_or_404(User, pk=pk)
    
    if user == request.user:
        messages.error(request, 'You cannot delete your own account.')
        return redirect('user_list')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'User {username} deleted successfully.')
        return redirect('user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {'user': user})

# API endpoints
@login_required
def api_check_username(request):
    """Check if username is available"""
    username = request.GET.get('username', '')
    if len(username) < 3:
        return JsonResponse({'available': False, 'error': 'Username too short'})
    
    exists = User.objects.filter(username__iexact=username).exists()
    return JsonResponse({'available': not exists})

@login_required
def api_check_email(request):
    """Check if email is available"""
    email = request.GET.get('email', '')
    exists = User.objects.filter(email__iexact=email).exists()
    return JsonResponse({'available': not exists})