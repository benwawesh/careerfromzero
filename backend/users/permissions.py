"""
Custom permissions for admin panel
"""
from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):
    """
    Permission to check if user is admin (is_staff)
    Admin uses same authentication as regular users (JWT)
    """
    
    def has_permission(self, request, view):
        # User must be authenticated
        if not request.user or not request.user.is_authenticated:
            return False
        
        # User must be staff
        return request.user.is_staff
    
    def has_object_permission(self, request, view, obj):
        # Admin can manage any object
        return self.has_permission(request, view)