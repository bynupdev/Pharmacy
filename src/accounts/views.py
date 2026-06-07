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
from .models import UserProfile, PasswordResetToken, Pharmacy, PendingUserRequest
from .forms import (
    LoginForm, PharmacyRegistrationForm, AdminApprovalForm,
    UserRoleUpdateForm, UserEditForm
)
from .utils import send_password_reset_email, generate_reset_token

from django.contrib.auth import authenticate, login
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.hashers import check_password


# def login_view(request):
#     if request.user.is_authenticated:
#         return redirect('dashboard')
    
#     if request.method == 'POST':
#         form = LoginForm(request, data=request.POST)
#         if form.is_valid():
#             username = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
#             user = authenticate(username=username, password=password)
            
#             if user is not None:
#                 if user.is_active:
#                     login(request, user)
                    
#                     # Store pharmacy ID in session
#                     if hasattr(user, 'profile') and user.profile.pharmacy:
#                         request.session['pharmacy_id'] = user.profile.pharmacy.id
                    
#                     messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
#                     return redirect('dashboard')
#                 else:
#                     messages.error(request, 'This account is disabled.')
#             else:
#                 messages.error(request, 'Invalid username or password.')
    
#     form = LoginForm()
#     return render(request, 'accounts/login.html', {'form': form})


# def login_view(request):
#     """Enhanced login with account state checks"""
#     if request.user.is_authenticated:
#         return redirect('dashboard')
    
#     if request.method == 'POST':
#         form = LoginForm(request, data=request.POST)
#         if form.is_valid():
#             username = form.cleaned_data.get('username')
#             password = form.cleaned_data.get('password')
            
#             user = authenticate(username=username, password=password)
            
#             if user is not None:
#                 # Check if user has a profile
#                 if not hasattr(user, 'profile'):
#                     messages.error(request, 'Account setup incomplete. Please contact support.')
#                     return redirect('accounts:accounts:login')
                
#                 profile = user.profile
                
#                 # Check account status
#                 if not user.is_active:
#                     # Check if there's a pending request
#                     pending = PendingUserRequest.objects.filter(created_user=user, status='pending').first()
#                     if pending:
#                         messages.warning(request, f'Your account is pending approval from {pending.pharmacy.name} admin. Please wait for approval.')
#                     else:
#                         messages.error(request, 'Your account has been deactivated. Contact your pharmacy admin.')
#                     return redirect('accounts:login')
                
#                 if not profile.is_approved:
#                     messages.warning(request, 'Your account is waiting for admin approval. You will be notified once approved.')
#                     return redirect('accounts:login')
                
#                 if not profile.pharmacy or not profile.pharmacy.is_active:
#                     messages.error(request, 'Your pharmacy is inactive. Contact support.')
#                     return redirect('accounts:login')
                
#                 # Login successful
#                 login(request, user)
#                 messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
#                 # Redirect based on role
#                 if profile.role == 'admin':
#                     return redirect('accounts:admin_dashboard')
#                 elif profile.role == 'pharmacist':
#                     return redirect('accounts:pharmacist_dashboard')
#                 else:
#                     return redirect('accounts:technician_dashboard')
#             else:
#                 messages.error(request, 'Invalid username or password.')
#         else:
#             messages.error(request, 'Please correct the errors below.')
#     else:
#         form = LoginForm()
    
#     return render(request, 'accounts/login.html', {'form': form})



from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth import login, authenticate
from django.contrib.auth.models import User
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import PendingUserRequest

def login_view(request):
    """Enhanced login with account state checks"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        # Get credentials directly from POST, not through form validation
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        print(f"Username: {username}")
        print(f"Password provided: {'Yes' if password else 'No'}")
        
        # FIRST: Check if user exists
        try:
            existing_user = User.objects.get(username=username)
            print(f"User found: {existing_user.username}")
            print(f"is_active: {existing_user.is_active}")
            
            if hasattr(existing_user, 'profile'):
                print(f"Profile exists, is_approved: {existing_user.profile.is_approved}")
                print(f"Profile role: {existing_user.profile.role}")
            
            # Case 1: Account pending admin approval (inactive)
            if not existing_user.is_active:
                pending = PendingUserRequest.objects.filter(
                    created_user=existing_user, 
                    status='pending'
                ).first()
                if pending:
                    messages.warning(request, f'Your account is pending approval from {pending.pharmacy.name} admin. Please wait.')
                else:
                    messages.warning(request, 'Your account is waiting for admin approval.')
                return redirect('accounts:login')
            
            # Case 2: Profile exists but not approved
            if hasattr(existing_user, 'profile') and not existing_user.profile.is_approved:
                messages.warning(request, 'Your account is waiting for admin approval. You will be notified once approved.')
                return redirect('accounts:login')
            
            # Case 3: Account is active and approved - now try to authenticate
            user = authenticate(request, username=username, password=password)
            
            if user is not None:
                # Login successful
                login(request, user)
                messages.success(request, f'Welcome back, {user.get_full_name() or user.username}!')
                
                # Redirect based on role
                if user.profile.role == 'admin':
                    return redirect('accounts:admin_dashboard')
                elif user.profile.role == 'pharmacist':
                    return redirect('accounts:pharmacist_dashboard')
                else:
                    return redirect('accounts:technician_dashboard')
            else:
                # Password is incorrect
                messages.error(request, 'Invalid password. Please try again.')
                return redirect('accounts:login')
                
        except User.DoesNotExist:
            print(f"User '{username}' does not exist")
            messages.error(request, 'Username does not exist. Please register first.')
            return redirect('accounts:login')
            
    # GET request - show empty form
    form = AuthenticationForm()
    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Logout view"""
    logout(request)
    messages.success(request, 'You have been successfully logged out.')
    return redirect('accounts:login')

# def register(request):
#     """Simple registration without email verification"""
#     if request.user.is_authenticated:
#         return redirect('dashboard')
    
#     if request.method == 'POST':
#         form = UserRegistrationForm(request.POST)
#         if form.is_valid():
#             user = form.save()  # This triggers the signal to create UserProfile
            
#             profile = user.profile  # Get the profile created by signal
#             profile.role = form.cleaned_data.get('role', 'technician')
#             profile.phone_number = form.cleaned_data.get('phone_number', '')
#             profile.license_number = form.cleaned_data.get('license_number', '')
#             profile.save()
            
#             messages.success(request, 'Account created successfully! You can now log in.')
#             return redirect('accounts:login')
#         else:
#             messages.error(request, 'Please correct the errors below.')
#     else:
#         form = UserRegistrationForm()
    
#     return render(request, 'accounts/register.html', {'form': form})



def register_view(request):
    """Handle registration with pharmacy detection"""
    if request.user.is_authenticated:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PharmacyRegistrationForm(request.POST)
        
        if form.is_valid():
            pharmacy_name = form.cleaned_data['pharmacy_name']
            email = form.cleaned_data['email']
            username = form.cleaned_data['username']
            password = form.cleaned_data['password1']
            first_name = form.cleaned_data['first_name']
            last_name = form.cleaned_data['last_name']
            phone_number = form.cleaned_data.get('phone_number', '')
            
            # Check if pharmacy already exists
            existing_pharmacy = Pharmacy.objects.filter(name__iexact=pharmacy_name).first()
            
            if existing_pharmacy:
                # Existing pharmacy - create pending request
                
                # Check if user already has a pending request
                existing_pending = PendingUserRequest.objects.filter(
                    email__iexact=email,
                    pharmacy=existing_pharmacy,
                    status='pending'
                ).exists()
                
                if existing_pending:
                    messages.warning(request, 'You already have a pending request for this pharmacy. Please wait for admin approval.')
                    return redirect('accounts:login')
                
                # Check if user is already a member of this pharmacy
                existing_user = User.objects.filter(email__iexact=email).first()
                if existing_user and hasattr(existing_user, 'profile') and existing_user.profile.pharmacy == existing_pharmacy:
                    messages.warning(request, 'You are already a member of this pharmacy. Please login.')
                    return redirect('accounts:login')
                
                # Create user account (inactive)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=False
                )
                
                # Update the profile that the signal created
                profile = user.profile
                role='technician'  # ← DEFAULT ROLE FOR PENDING EMPLOYEES
                profile.phone_number = phone_number
                profile.pharmacy = existing_pharmacy
                profile.is_approved = False
                profile.save()
                
                # Create pending request
                pending_request = PendingUserRequest.objects.create(
                    email=email,
                    first_name=first_name,
                    last_name=last_name,
                    requested_pharmacy_name=pharmacy_name,
                    pharmacy=existing_pharmacy,
                    requested_role='technician',
                    status='pending',
                    created_user=user
                )
                
                messages.info(request, f'Your request to join {existing_pharmacy.name} has been sent to the admin for approval.')
                return redirect('accounts:login')
                
            else:
                # New pharmacy - create everything
                pharmacy = Pharmacy.objects.create(
                    name=pharmacy_name,
                    phone=phone_number,
                    email=email
                )
                
                # Create user (active)
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=first_name,
                    last_name=last_name,
                    is_active=True
                )
                
                # Update the profile that the signal created
                profile = user.profile
                profile.role = 'admin'
                profile.phone_number = phone_number
                profile.pharmacy = pharmacy
                profile.is_approved = True
                profile.save()
                
                messages.success(request, f'Welcome! Your pharmacy "{pharmacy_name}" has been created. You are the administrator.')
                return redirect('accounts:login')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = PharmacyRegistrationForm()
    
    return render(request, 'accounts/register.html', {'form': form})


def check_pharmacy_exists(request):
    """AJAX endpoint to check if pharmacy exists"""
    pharmacy_name = request.GET.get('pharmacy_name', '')
    if pharmacy_name:
        exists = Pharmacy.objects.filter(name__iexact=pharmacy_name).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'exists': False})


def check_email_exists(request):
    """AJAX endpoint to check if email exists"""
    email = request.GET.get('email', '')
    if email:
        exists = User.objects.filter(email__iexact=email).exists()
        return JsonResponse({'exists': exists})
    return JsonResponse({'exists': False})


@login_required
def admin_dashboard(request):
    """Admin dashboard with approval queue and user management"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    pharmacy = request.user.profile.pharmacy
    if not pharmacy:
        messages.error(request, 'No pharmacy associated with your account.')
        return redirect('dashboard')
    
    # Get pending requests for this pharmacy
    pending_requests = PendingUserRequest.objects.filter(
        pharmacy=pharmacy,
        status='pending'
    ).order_by('-created_at')
    
    # Get approved users
    users = User.objects.filter(
        profile__pharmacy=pharmacy,
        profile__is_approved=True
    ).select_related('profile')
    
    # Statistics
    stats = {
        'total_users': users.count(),
        'admins': users.filter(profile__role='admin').count(),
        'pharmacists': users.filter(profile__role='pharmacist').count(),
        'technicians': users.filter(profile__role='technician').count(),
        'pending_count': pending_requests.count(),
    }
    
    context = {
        'pending_requests': pending_requests,
        'users': users,
        'stats': stats,
        'pharmacy': pharmacy,
    }
    return render(request, 'accounts/admin_dashboard.html', context)

from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import PendingUserRequest

@login_required
def approve_user(request, request_id):
    """Approve a pending user request"""
    # Get the pending request
    pending = get_object_or_404(PendingUserRequest, id=request_id)
    
    # Check if the current user is admin of the same pharmacy
    if request.user.profile.role != 'admin' or request.user.profile.pharmacy != pending.pharmacy:
        messages.error(request, 'You do not have permission to approve this user.')
        return redirect('admin_dashboard')
    
    if request.method == 'POST':
        role = request.POST.get('role', 'technician')
        
        if role not in ['pharmacist', 'technician']:
            messages.error(request, 'Invalid role selected.')
            return redirect('admin_dashboard')
        
        # Get the user associated with this pending request
        user = pending.created_user
        
        if user:
            # Activate the user
            user.is_active = True
            user.save()
            
            # Update profile
            profile = user.profile
            profile.role = role
            profile.is_approved = True
            profile.save()
            
            # Update pending request status
            pending.status = 'approved'
            pending.save()
            
            messages.success(request, f'{user.get_full_name()} has been approved as {role}.')
        else:
            messages.error(request, 'User not found.')
        
        return redirect('accounts:admin_dashboard')
    
    # GET request - show confirmation page
    return render(request, 'accounts/approve_user.html', {'pending': pending})

@login_required
def reject_user(request, request_id):
    """Reject a pending user request"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        return JsonResponse({'error': 'Permission denied'}, status=403)
    
    pending = get_object_or_404(PendingUserRequest, id=request_id, pharmacy=request.user.profile.pharmacy)
    
    if request.method == 'POST':
        reason = request.POST.get('reason', '')
        
        # Update pending request
        pending.status = 'rejected'
        pending.rejection_reason = reason
        pending.save()
        
        # Delete the user account
        if pending.created_user:
            pending.created_user.delete()
        
        messages.warning(request, f'{pending.first_name} {pending.last_name} has been rejected.')
        return redirect('admin_dashboard')
    
    return JsonResponse({'error': 'Invalid method'}, status=405)

@login_required
def manage_users(request):
    """Admin user management - change roles, deactivate users"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    
    pharmacy = request.user.profile.pharmacy
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        target_user = get_object_or_404(User, id=user_id, profile__pharmacy=pharmacy)
        
        # Prevent admin from deactivating themselves
        if target_user == request.user:
            messages.error(request, 'You cannot modify your own account here.')
            return redirect('accounts:manage_users')
        
        if action == 'change_role':
            new_role = request.POST.get('role')
            if new_role in ['admin', 'pharmacist', 'technician']:
                target_user.profile.role = new_role
                target_user.profile.save()
                messages.success(request, f'Role updated to {new_role}.')
        
        elif action == 'deactivate':
            target_user.is_active = False
            target_user.save()
            messages.warning(request, f'{target_user.get_full_name()} has been deactivated.')
        
        elif action == 'activate':
            target_user.is_active = True
            target_user.save()
            messages.success(request, f'{target_user.get_full_name()} has been activated.')
        
        return redirect('accounts:manage_users')
    
    users = User.objects.filter(
        profile__pharmacy=pharmacy,
        profile__is_approved=True
    ).select_related('profile').exclude(id=request.user.id)
    
    return render(request, 'accounts/manage_users.html', {'users': users})


@login_required
def pharmacist_dashboard(request):
    """Pharmacist dashboard"""
    if not hasattr(request.user, 'profile') or request.user.profile.role not in ['admin', 'pharmacist']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get pharmacy data
    pharmacy = request.user.profile.pharmacy
    
    # Get statistics for pharmacist
    from prescriptions.models import Prescription
    from inventory.models import Batch, StockAlert
    from sales.models import Sale
    from django.utils import timezone
    from datetime import timedelta
    
    context = {
        'pending_prescriptions': Prescription.objects.filter(
            pharmacy=pharmacy, 
            status='pending'
        ).count(),
        'verified_prescriptions': Prescription.objects.filter(
            pharmacy=pharmacy, 
            status='verified'
        ).count(),
        'low_stock_alerts': StockAlert.objects.filter(
            batch__pharmacy=pharmacy,
            alert_type='low_stock', 
            is_resolved=False
        ).count(),
        'today_sales': Sale.objects.filter(
            pharmacy=pharmacy,
            created_at__date=timezone.now().date()
        ).count(),
    }
    return render(request, 'accounts/pharmacist_dashboard.html', context)


@login_required
def technician_dashboard(request):
    """Technician dashboard"""
    if not hasattr(request.user, 'profile') or request.user.profile.role not in ['admin', 'pharmacist', 'technician']:
        messages.error(request, 'You do not have permission to access this page.')
        return redirect('dashboard')
    
    # Get pharmacy data
    pharmacy = request.user.profile.pharmacy
    
    # Get statistics for technician
    from inventory.models import Drug, Batch
    from patients.models import Patient
    
    context = {
        'total_drugs': Drug.objects.filter(pharmacy=pharmacy).count(),
        'total_batches': Batch.objects.filter(pharmacy=pharmacy).count(),
        'total_patients': Patient.objects.filter(pharmacy=pharmacy).count(),
        'expiring_batches': Batch.objects.filter(
            pharmacy=pharmacy,
            expiry_date__lte=timezone.now().date() + timedelta(days=30),
            quantity__gt=0
        ).count(),
    }
    return render(request, 'accounts/technician_dashboard.html', context)




def dashboard_router(request):
    """Route users to their appropriate dashboard based on role"""
    if not request.user.is_authenticated:
        return redirect('accounts:login')
    
    if not hasattr(request.user, 'profile'):
        return redirect('accounts:login')
    
    role = request.user.profile.role
    
    if role == 'admin':
        return redirect('accounts:admin_dashboard')
    elif role == 'pharmacist':
        return redirect('accounts:pharmacist_dashboard')
    elif role == 'technician':
        return redirect('accounts:technician_dashboard')
    else:
        # Fallback for users without role (pending approval)
        return redirect('accounts:login')


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
            return redirect('accounts:login')
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
            return redirect('accounts:login')
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


@login_required
def manage_users(request):
    """Admin user management - change roles, deactivate users"""
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
        messages.error(request, 'Permission denied.')
        return redirect('dashboard')
    
    pharmacy = request.user.profile.pharmacy
    
    if request.method == 'POST':
        user_id = request.POST.get('user_id')
        action = request.POST.get('action')
        
        # IMPORTANT: Only allow managing users from the SAME pharmacy
        try:
            target_user = User.objects.get(
                id=user_id, 
                profile__pharmacy=pharmacy
            )
        except User.DoesNotExist:
            messages.error(request, 'User not found in your pharmacy.')
            return redirect('accounts:manage_users')
        
        # Prevent admin from modifying themselves
        if target_user == request.user:
            messages.error(request, 'You cannot modify your own account here.')
            return redirect('accounts:manage_users')
        
        if action == 'change_role':
            new_role = request.POST.get('role')
            if new_role in ['admin', 'pharmacist', 'technician']:
                target_user.profile.role = new_role
                target_user.profile.save()
                messages.success(request, f'{target_user.get_full_name()} role updated to {new_role}.')
            else:
                messages.error(request, 'Invalid role selected.')
        
        elif action == 'deactivate':
            target_user.is_active = False
            target_user.save()
            messages.warning(request, f'{target_user.get_full_name()} has been deactivated.')
        
        elif action == 'activate':
            target_user.is_active = True
            target_user.save()
            messages.success(request, f'{target_user.get_full_name()} has been activated.')
        
        else:
            messages.error(request, 'Invalid action.')
        
        return redirect('accounts:manage_users')
    
    # GET request - show all users in this pharmacy (excluding the current admin)
    users = User.objects.filter(
        profile__pharmacy=pharmacy,
        profile__is_approved=True
    ).select_related('profile').exclude(id=request.user.id)
    
    return render(request, 'accounts/manage_users.html', {'users': users})



from django.shortcuts import render
from django.contrib.auth.models import User
from django.db.models import Count
from accounts.models import Pharmacy

def landing_page(request):
    """Beautiful landing page for the pharmacy management system"""
    
    # Get statistics
    total_pharmacies = Pharmacy.objects.count()
    total_users = User.objects.filter(is_active=True).count()
    
    # You can add more dynamic stats if needed
    from inventory.models import Drug
    total_drugs = Drug.objects.count()
    
    # Features data
    features = [
        {
            'icon': 'fas fa-chart-line',
            'title': 'Real-time Analytics',
            'description': 'Track sales, inventory, and prescriptions with powerful dashboards and instant insights.',
            'color': '#667eea'
        },
        {
            'icon': 'fas fa-shield-alt',
            'title': 'Secure & Compliant',
            'description': 'HIPAA compliant, end-to-end encryption, and secure role-based access control.',
            'color': '#f59e0b'
        },
        {
            'icon': 'fas fa-prescription-bottle',
            'title': 'Smart Prescriptions',
            'description': 'AI-powered drug interaction checking and digital prescription management.',
            'color': '#10b981'
        },
        {
            'icon': 'fas fa-boxes',
            'title': 'Inventory Control',
            'description': 'Real-time stock tracking, expiry alerts, and automated reordering system.',
            'color': '#ef4444'
        },
        {
            'icon': 'fas fa-mobile-alt',
            'title': 'Mobile Ready',
            'description': 'Fully responsive design - manage your pharmacy from anywhere, any device.',
            'color': '#8b5cf6'
        },
        {
            'icon': 'fas fa-headset',
            'title': '24/7 Support',
            'description': 'Dedicated support team available round the clock to help you.',
            'color': '#06b6d4'
        },
        {
            'icon': 'fas fa-chart-bar',
            'title': 'Advanced Reporting',
            'description': 'Generate detailed reports for sales, inventory, and business performance.',
            'color': '#ec4899'
        },
        {
            'icon': 'fas fa-users',
            'title': 'Multi-User System',
            'description': 'Role-based access for pharmacists, technicians, and cashiers.',
            'color': '#14b8a6'
        },
        {
            'icon': 'fas fa-cloud-upload-alt',
            'title': 'Cloud Backup',
            'description': 'Automatic backups and 99.9% uptime guarantee for your data.',
            'color': '#6366f1'
        },
    ]
    
    # Pricing plans
    pricing_plans = [
        {
            'name': 'Basic',
            'price': '$49',
            'period': 'month',
            'description': 'Perfect for small pharmacies just starting out',
            'features': [
                'Up to 5 users',
                '1,000 prescriptions/month',
                'Basic inventory management',
                'Email support',
                '1GB storage',
                'Standard reports'
            ],
            'button_text': 'Start Free Trial',
            'popular': False,
            'color': '#6b7280'
        },
        {
            'name': 'Professional',
            'price': '$99',
            'period': 'month',
            'description': 'Best for growing pharmacies with higher volume',
            'features': [
                'Up to 20 users',
                '10,000 prescriptions/month',
                'Advanced inventory management',
                'Priority support',
                '10GB storage',
                'AI drug interaction checker',
                'Custom reports',
                'API access'
            ],
            'button_text': 'Start Free Trial',
            'popular': True,
            'color': '#667eea'
        },
        {
            'name': 'Enterprise',
            'price': '$199',
            'period': 'month',
            'description': 'For large pharmacy chains and high-volume operations',
            'features': [
                'Unlimited users',
                'Unlimited prescriptions',
                'Multi-location support',
                '24/7 phone support',
                '100GB storage',
                'Custom integrations',
                'Dedicated account manager',
                'SLA guarantee'
            ],
            'button_text': 'Contact Sales',
            'popular': False,
            'color': '#8b5cf6'
        },
    ]
    
    # Testimonials
    testimonials = [
        {
            'name': 'Dr. Sarah Johnson',
            'role': 'Owner, City Pharmacy',
            'text': 'This system transformed our pharmacy operations. The AI drug interaction checker alone has prevented countless potential issues. Our efficiency has increased by 40%!',
            'rating': 5,
            'image': 'https://ui-avatars.com/api/?background=667eea&color=fff&name=Sarah+Johnson'
        },
        {
            'name': 'Michael Chen',
            'role': 'Pharmacist, Wellness Plus',
            'text': 'Incredible value for money. The inventory management and reporting features are exactly what we needed. Customer support is outstanding!',
            'rating': 5,
            'image': 'https://ui-avatars.com/api/?background=667eea&color=fff&name=Michael+Chen'
        },
        {
            'name': 'Dr. Emily Rodriguez',
            'role': 'Director, Family Health',
            'text': 'The multi-user support and role-based access make it easy to manage my entire team. Weve reduced prescription errors by 60% since switching.',
            'rating': 5,
            'image': 'https://ui-avatars.com/api/?background=667eea&color=fff&name=Emily+Rodriguez'
        },
    ]
    
    # FAQs
    faqs = [
        {
            'question': 'Is there a free trial?',
            'answer': 'Yes! We offer a 14-day free trial on all plans. No credit card required.'
        },
        {
            'question': 'Can I cancel anytime?',
            'answer': 'Absolutely. You can cancel your subscription at any time with no hidden fees.'
        },
        {
            'question': 'Is my data secure?',
            'answer': 'Yes, we use bank-level encryption and follow HIPAA compliance standards.'
        },
        {
            'question': 'Do you offer training?',
            'answer': 'Yes, we provide free onboarding training and 24/7 support for all customers.'
        },
    ]
    
    context = {
        'features': features,
        'pricing_plans': pricing_plans,
        'testimonials': testimonials,
        'faqs': faqs,
        'total_pharmacies': total_pharmacies,
        'total_users': total_users,
        'total_drugs': total_drugs,
        'year': 2024,
    }
    
    return render(request, 'landing/landing_page.html', context)



from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages

def admin_required(view_func):
    """Allow access only to admins"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not hasattr(request.user, 'profile'):
            messages.error(request, 'Account profile not found.')
            return redirect('dashboard')
        
        if request.user.profile.role != 'admin':
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def pharmacist_required(view_func):
    """Allow access to pharmacists and admins"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not hasattr(request.user, 'profile'):
            messages.error(request, 'Account profile not found.')
            return redirect('dashboard')
        
        if request.user.profile.role not in ['admin', 'pharmacist']:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def technician_required(view_func):
    """Allow access to technicians, pharmacists, and admins"""
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('accounts:login')
        
        if not hasattr(request.user, 'profile'):
            messages.error(request, 'Account profile not found.')
            return redirect('dashboard')
        
        if request.user.profile.role not in ['admin', 'pharmacist', 'technician']:
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        
        return view_func(request, *args, **kwargs)
    return wrapper

def role_required(allowed_roles):
    """Generic decorator for multiple allowed roles"""
    def decorator(view_func):
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('accounts:login')
            
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'Account profile not found.')
                return redirect('dashboard')
            
            if request.user.profile.role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                return redirect('dashboard')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator