"""
Role-based permission classes for DRF views.

Usage:
    class MyView(APIView):
        permission_classes = [IsAuthenticated, IsAnalystOrAbove]
"""

from rest_framework.permissions import BasePermission
from apps.users.models import User


class IsAdmin(BasePermission):
    """Only ADMIN role."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.ADMIN
        )


class IsAnalystOrAbove(BasePermission):
    """ANALYST or ADMIN — can create/modify rules and view all logs."""
    ALLOWED = {User.Role.ADMIN, User.Role.ANALYST}

    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role in self.ALLOWED
        )


class IsViewerOrAbove(BasePermission):
    """Any authenticated role — read-only access to logs and alerts."""
    def has_permission(self, request, view):
        return request.user.is_authenticated


class IsAPIUser(BasePermission):
    """Service account with API key — can only ship logs (POST /ingest)."""
    def has_permission(self, request, view):
        return (
            request.user.is_authenticated
            and request.user.role == User.Role.API_USER
        )


class ReadOnlyOrAdmin(BasePermission):
    """GET requests allowed for all authenticated users; mutations require ADMIN."""
    def has_permission(self, request, view):
        if not request.user.is_authenticated:
            return False
        if request.method in ("GET", "HEAD", "OPTIONS"):
            return True
        return request.user.role == User.Role.ADMIN