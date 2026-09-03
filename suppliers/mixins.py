# mixins.py
from django.contrib.auth.mixins import AccessMixin
from django.core.exceptions import PermissionDenied

class SupplierAccessMixin(AccessMixin):
    """Ensures that logged-in suppliers can only view their own records."""

    allow_staff = True
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        
        # Check if user is linked to a Supplier profile or is staff/admin
        if not hasattr(request.user, 'supplier_profile') and not (self.allow_staff and request.user.is_staff):
            raise PermissionDenied("You do not have access to the Supplier Portal.")
            
        return super().dispatch(request, *args, **kwargs)

    def get_supplier(self):
        if self.request.user.is_staff:
            return None  # Admins can filter manually or see all
        return self.request.user.supplier_profile