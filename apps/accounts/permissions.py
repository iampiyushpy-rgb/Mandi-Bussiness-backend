from rest_framework import permissions

class IsSuperAdmin(permissions.BasePermission):
    """Allows access only to Super Admins."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_superuser:
            return True
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.role and profile.role.code == 'SUPER_ADMIN')

class IsAdmin(permissions.BasePermission):
    """Allows access to Super Admins and Admins."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.role and profile.role.code in ['SUPER_ADMIN', 'ADMIN'])

class CanManagePurchases(permissions.BasePermission):
    """Allows access to Admins, Purchase Managers, and read access for authenticated users."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        if request.method in permissions.SAFE_METHODS:
            return True
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.role and profile.role.code in [
            'SUPER_ADMIN', 'ADMIN', 'PURCHASE_MANAGER', 'DATA_OPERATOR'
        ])

class CanManageSales(permissions.BasePermission):
    """Allows access to Admins, Sales Managers, and Sales Persons."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.role and profile.role.code in [
            'SUPER_ADMIN', 'ADMIN', 'SALES_MANAGER', 'DATA_OPERATOR', 'SALES_PERSON'
        ])

class CanManageInventory(permissions.BasePermission):
    """Allows access to Admins, Warehouse Managers, Purchase Managers, and read access for authenticated users."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        if request.method in permissions.SAFE_METHODS:
            return True
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.role and profile.role.code in [
            'SUPER_ADMIN', 'ADMIN', 'WAREHOUSE_MANAGER', 'PURCHASE_MANAGER'
        ])

class CanManagePayments(permissions.BasePermission):
    """Allows access to Admins and Accountants."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.role and profile.role.code in [
            'SUPER_ADMIN', 'ADMIN', 'ACCOUNTANT'
        ])

class CanViewReports(permissions.BasePermission):
    """Allows access to Admins, Accountants, and Managers."""
    def has_permission(self, request, view):
        if not (request.user and request.user.is_authenticated and request.user.is_active):
            return False
        if request.user.is_superuser or request.user.is_staff:
            return True
        profile = getattr(request.user, 'profile', None)
        return bool(profile and profile.role and profile.role.code in [
            'SUPER_ADMIN', 'ADMIN', 'ACCOUNTANT', 'SALES_MANAGER', 'PURCHASE_MANAGER'
        ])
