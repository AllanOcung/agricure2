"""
Role-based access control decorators for dashboard views
"""

from functools import wraps
from django.contrib.auth.decorators import login_required
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.contrib import messages
from django.http import HttpResponseForbidden
from django.urls import reverse

User = get_user_model()

def get_user_role(user):
    """Get user role based on user attributes"""
    if not user.is_authenticated:
        return None
    
    # Check if user is superuser (always admin)
    if user.is_superuser:
        return 'admin'
    
    # Check if user has a UserProfile with role field
    try:
        from accounts.models import UserProfile
        profile = UserProfile.objects.get(user=user)
        return profile.role
    except UserProfile.DoesNotExist:
        # Create profile if it doesn't exist
        from accounts.models import UserProfile
        profile = UserProfile.objects.create(user=user, role='farmer')
        return profile.role
    except Exception:
        # Fallback: check if user is staff
        if user.is_staff:
            return 'admin'
        # Default to farmer
        return 'farmer'

def role_required(allowed_roles):
    """
    Decorator to restrict access to views based on user role
    
    Args:
        allowed_roles: List of roles that can access the view
    """
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def _wrapped_view(request, *args, **kwargs):
            user_role = get_user_role(request.user)
            
            if user_role not in allowed_roles:
                messages.error(request, f'Access denied. This page is restricted to {", ".join(allowed_roles)} users.')
                return HttpResponseForbidden("Access denied. You don't have permission to access this page.")
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

def admin_required(view_func):
    """
    Decorator to restrict access to admin users only
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user_role = get_user_role(request.user)
        
        if user_role != 'admin':
            messages.error(request, 'Access denied. This page is restricted to admin users only.')
            return HttpResponseForbidden("Access denied. You need admin privileges to access this page.")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def farmer_required(view_func):
    """
    Decorator to restrict access to farmer users only
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user_role = get_user_role(request.user)
        
        if user_role != 'farmer':
            messages.error(request, 'Access denied. This page is restricted to farmer users only.')
            return HttpResponseForbidden("Access denied. You need farmer privileges to access this page.")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def admin_or_farmer_required(view_func):
    """
    Decorator to allow access to both admin and farmer users
    """
    @wraps(view_func)
    @login_required
    def _wrapped_view(request, *args, **kwargs):
        user_role = get_user_role(request.user)
        
        if user_role not in ['admin', 'farmer']:
            messages.error(request, 'Access denied. You need to be logged in as an admin or farmer.')
            return HttpResponseForbidden("Access denied. You need admin or farmer privileges to access this page.")
        
        return view_func(request, *args, **kwargs)
    return _wrapped_view

def user_role_context(request):
    """
    Context processor to make user role available in templates
    
    Add this to your TEMPLATES['OPTIONS']['context_processors'] in settings.py:
    'dashboard.decorators.user_role_context'
    """
    if request.user.is_authenticated:
        return {
            'user_role': get_user_role(request.user),
            'is_admin': get_user_role(request.user) == 'admin',
            'is_farmer': get_user_role(request.user) == 'farmer',
        }
    return {
        'user_role': None,
        'is_admin': False,
        'is_farmer': False,
    }

def check_user_role(user, required_role):
    """
    Helper function to check if user has required role
    
    Args:
        user: User instance
        required_role: Required role string ('admin', 'farmer', etc.)
    
    Returns:
        bool: True if user has required role, False otherwise
    """
    if not user.is_authenticated:
        return False
    
    user_role = get_user_role(user)
    return user_role == required_role

def has_admin_permission(user):
    """
    Check if user has admin permissions
    
    Args:
        user: User instance
    
    Returns:
        bool: True if user has admin permissions, False otherwise
    """
    return check_user_role(user, 'admin')

def has_farmer_permission(user):
    """
    Check if user has farmer permissions
    
    Args:
        user: User instance
    
    Returns:
        bool: True if user has farmer permissions, False otherwise
    """
    return check_user_role(user, 'farmer')

# Middleware for role-based access control
class RoleBasedAccessMiddleware:
    """
    Middleware to handle role-based access control
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Add user role to request object
        if request.user.is_authenticated:
            request.user_role = get_user_role(request.user)
        else:
            request.user_role = None
        
        response = self.get_response(request)
        return response

# Permission classes for API views (if using DRF)
class IsAdminUser:
    """
    Custom permission class for Django REST Framework
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and has_admin_permission(request.user)

class IsFarmerUser:
    """
    Custom permission class for Django REST Framework
    """
    def has_permission(self, request, view):
        return request.user.is_authenticated and has_farmer_permission(request.user)

class IsAdminOrFarmerUser:
    """
    Custom permission class for Django REST Framework
    """
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        
        user_role = get_user_role(request.user)
        return user_role in ['admin', 'farmer']
