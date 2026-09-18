from functools import wraps

from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required

from .models import ModulePermission


def rbac_required(module_name, required_permission='view'):
    def decorator(view_func):
        @wraps(view_func)
        @login_required
        def wrapped(request, *args, **kwargs):
            user = request.user
            if not user.is_superuser:
                role = getattr(user, 'role', None)
                permission = ModulePermission.objects.filter(
                    role=role,
                    module_name=module_name,
                ).first()
                if not permission or not getattr(permission, f'can_{required_permission}', False):
                    raise PermissionDenied("Can't Access !.")
            return view_func(request, *args, **kwargs)
        return wrapped
    return decorator
