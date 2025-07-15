"""
Role-based access control decorators
"""

from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps

User = get_user_model()

def admin_required(function=None, redirect_url='/dashboard/'):
    """
    Decorator for views that checks that the user is an admin (staff member).
    """
    def check_admin(user):
        return user.is_authenticated and user.is_staff
    
    actual_decorator = user_passes_test(
        check_admin,
        login_url='/admin/login/',
        redirect_field_name='next'
    )
    
    if function:
        return actual_decorator(function)
    return actual_decorator

def farmer_required(function=None, redirect_url='/dashboard/'):
    """
    Decorator for views that checks that the user is a farmer (regular user).
    """
    def check_farmer(user):
        return user.is_authenticated and not user.is_staff
    
    actual_decorator = user_passes_test(
        check_farmer,
        login_url='/accounts/login/',
        redirect_field_name='next'
    )
    
    if function:
        return actual_decorator(function)
    return actual_decorator

def role_required(allowed_roles):
    """
    Decorator that checks if user has one of the allowed roles.
    allowed_roles: list of roles ('admin', 'farmer')
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect('/accounts/login/')
            
            user_role = get_user_role(request.user)
            
            if user_role not in allowed_roles:
                messages.error(request, 'You do not have permission to access this page.')
                if user_role == 'admin':
                    return redirect('/dashboard/admin/')
                else:
                    return redirect('/dashboard/')
            
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator

def get_user_role(user):
    """
    Get the role of a user.
    Returns 'admin' for staff users, 'farmer' for regular users.
    """
    if not user.is_authenticated:
        return None
    
    if user.is_staff or user.is_superuser:
        return 'admin'
    else:
        return 'farmer'

def check_admin_access(user):
    """
    Check if user has admin access.
    """
    return user.is_authenticated and (user.is_staff or user.is_superuser)

def check_farmer_access(user):
    """
    Check if user has farmer access.
    """
    return user.is_authenticated and not user.is_staff

# Context processor for role-based templates
def user_role_context(request):
    """
    Context processor to add user role to template context.
    """
    if request.user.is_authenticated:
        return {
            'user_role': get_user_role(request.user),
            'is_admin': check_admin_access(request.user),
            'is_farmer': check_farmer_access(request.user)
        }
    return {
        'user_role': None,
        'is_admin': False,
        'is_farmer': False
    }
