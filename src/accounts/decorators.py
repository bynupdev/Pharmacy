from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

def admin_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='login'):
    """Decorator for views that checks that the user is an admin"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'profile') and u.profile.role == 'admin',
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def pharmacist_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='login'):
    """Decorator for views that checks that the user is a pharmacist"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'profile') and u.profile.role in ['admin', 'pharmacist'],
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def technician_required(function=None, redirect_field_name=REDIRECT_FIELD_NAME, login_url='login'):
    """Decorator for views that checks that the user is a technician"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and hasattr(u, 'profile') and u.profile.role in ['admin', 'pharmacist', 'technician'],
        login_url=login_url,
        redirect_field_name=redirect_field_name
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def role_required(allowed_roles=[]):
    """Decorator for views that checks if user has any of the allowed roles"""
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('login')
            
            if not hasattr(request.user, 'profile'):
                messages.error(request, 'User profile not found.')
                return redirect('login')
            
            if request.user.profile.role in allowed_roles:
                return view_func(request, *args, **kwargs)
            
            messages.error(request, 'You do not have permission to access this page.')
            return redirect('dashboard')
        return _wrapped_view
    return decorator