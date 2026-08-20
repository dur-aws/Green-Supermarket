# accounts/mixins.py
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import PermissionDenied
from .models import ModulePermission

class RBACPermissionMixin(LoginRequiredMixin, UserPassesTestMixin):
    module_name = None  # Define in each view (e.g., 'products')
    required_permission = 'view'  # Options: 'view', 'add', 'edit', 'delete'

    def test_func(self):
        user = self.request.user
        
        # Superuser bypasses all permission checks
        if user.is_superuser:
            return True

        if not hasattr(user, 'role') or not user.role:
            return False

        if not self.module_name:
            raise NotImplementedError("Each view using RBACPermissionMixin must specify a 'module_name'.")

        try:
            perm = ModulePermission.objects.get(role=user.role, module_name=self.module_name)
            
            if self.required_permission == 'view':
                return perm.can_view
            elif self.required_permission == 'add':
                return perm.can_add
            elif self.required_permission == 'edit':
                return perm.can_edit
            elif self.required_permission == 'delete':
                return perm.can_delete
        except ModulePermission.DoesNotExist:
            return False

        return False

    def handle_no_permission(self):
        raise PermissionDenied("Can't Access !.")