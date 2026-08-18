# accounts/middleware.py
import re
import logging
from django.contrib import messages
from django.utils import timezone
from .models import ActivityLog

logger = logging.getLogger(__name__)

class AuditLogMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # 1. Ignore static, media, admin assets, and the audit log itself
        ignored_paths = ['/static/', '/media/', '/admin/', '/activity-log']
        if any(request.path.startswith(path) for path in ignored_paths):
            return response

        path_lower = request.path.lower()
        action_type = None

        # 2. Check for Security Exceptions
        if response.status_code == 403:
            action_type = 'ACCESS_DENIED'
        elif response.status_code >= 500:
            action_type = 'SYSTEM_ERROR'

        # 3. Check for Data Modifications (POST, PUT, DELETE)
        elif request.method in ['POST', 'PUT', 'PATCH', 'DELETE']:
            if request.method == 'DELETE' or 'delete' in path_lower:
                action_type = 'DELETE'
            elif 'add' in path_lower or 'create' in path_lower:
                action_type = 'CREATE'
            elif 'login' in path_lower:
                action_type = 'LOGIN'
            elif 'logout' in path_lower:
                action_type = 'LOGOUT'
            else:
                action_type = 'UPDATE'

        # 4. Check for Specific Resource/Data Access on GET requests
        # Logs GET requests ONLY when accessing specific records (e.g., /users/5/, /suppliers/detail/12)
        elif request.method == 'GET' and response.status_code < 400:
            # Matches URIs with trailing integer IDs or specific detail keywords
            is_detail_view = bool(re.search(r'/(detail|view|\d+)(/|$)', path_lower))
            if is_detail_view:
                action_type = 'DATA_ACCESS'

        # If not a mutation, security error, or detail data view, ignore
        if not action_type:
            return response

        # 5. Capture Flash Messages
        alert_text = None
        try:
            storage = messages.get_messages(request)
            if storage.used:
                captured_messages = []
                for msg in storage:
                    prefix = "Error: " if msg.tags in ['error', 'danger'] else ("Warning: " if msg.tags == 'warning' else "")
                    captured_messages.append(f"[{msg.tags.upper()}] {prefix}{msg.message}")
                if captured_messages:
                    alert_text = " | ".join(captured_messages)
        except Exception:
            pass

        # 6. Extract IP & Save Entry
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        ip = x_forwarded_for.split(',')[0] if x_forwarded_for else request.META.get('REMOTE_ADDR')

        try:
            user = request.user if request.user.is_authenticated else None
            
            # Custom readable description based on action
            if action_type == 'DATA_ACCESS':
                desc = f"User '{user.username if user else 'Guest'}' accessed record at {request.path}"
            else:
                desc = f"User '{user.username if user else 'Guest'}' performed {action_type} on {request.path}"

            ActivityLog.objects.create(
                user=user,
                action_type=action_type,
                path=request.path[:255],
                method=request.method,
                status_code=response.status_code,
                ip_address=ip,
                description=desc,
                alert_message=alert_text,
                timestamp=timezone.now()
            )
        except Exception as e:
            logger.error(f"Failed to save activity log: {e}")

        return response