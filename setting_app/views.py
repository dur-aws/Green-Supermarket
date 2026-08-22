# Create your views here.
from django.contrib.auth.views import LoginView
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib.auth import login

from .models import ActivityLog
from django.views.generic import ListView
from django.db.models import Q
from accounts.mixins import RBACPermissionMixin


class UserLoginView(LoginView):
    template_name = 'accounts/login.html'

    def form_valid(self, form):
        user = form.get_user()

        # Block inactive accounts
        if user.status != 1 or not user.is_active:
            messages.error(self.request, "Your account is currently inactive. Contact system administrator.")
            
            # Record failed login attempt to Activity Log
            ActivityLog.objects.create(
                user=user,
                action_type='ACCESS_DENIED',
                path=self.request.path,
                method='POST',
                status_code=403,
                description=f"Inactive account login attempt by username: {user.username}"
            )
            return self.form_invalid(form)

        login(self.request, user)
        
        # Record successful login attempt
        ActivityLog.objects.create(
            user=user,
            action_type='LOGIN',
            path=self.request.path,
            method='POST',
            status_code=200,
            description=f"User {user.username} logged in successfully."
        )

        messages.success(self.request, f"Welcome back, {user.first_name or user.username}!")
        return redirect(self.get_success_url())


class LogActivityListView(RBACPermissionMixin, ListView):
    model = ActivityLog
    template_name = 'activityLog.html'
    context_object_name = 'activity_logs'
    paginate_by = 15

    def get_queryset(self):
        queryset = ActivityLog.objects.select_related('user', 'user__role').all()
        
        # Search filter (username, path, description, IP)
        q = self.request.GET.get('q')
        if q:
            queryset = queryset.filter(
                Q(user__username__icontains=q) |
                Q(path__icontains=q) |
                Q(description__icontains=q) |
                Q(ip_address__icontains=q)
            )

        # Action Type filter (LOGIN, CREATE, DELETE, ACCESS_DENIED, etc.)
        action = self.request.GET.get('action')
        if action:
            queryset = queryset.filter(action_type=action)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Stats summary counters for the stat strip
        all_logs = ActivityLog.objects.all()
        context['total_logs'] = all_logs.count()
        context['login_count'] = all_logs.filter(action_type='LOGIN').count()
        context['denied_count'] = all_logs.filter(action_type='ACCESS_DENIED').count()
        context['action_choices'] = ActivityLog.ACTION_TYPES
        return context