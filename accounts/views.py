# accounts/views.py
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.views import LoginView, LogoutView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404, render
from django.urls import reverse_lazy
from django.views.generic import ListView, View, DetailView, CreateView, UpdateView, DeleteView, FormView
from django.db.models import Count, Q
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.core.exceptions import PermissionDenied
from django.contrib.auth.decorators import login_required
from .forms import CustomLoginForm, AdminUserCreationForm, AdminUserUpdateForm, AdminResetPasswordForm
from .mixins import RBACPermissionMixin
from django.contrib.auth import update_session_auth_hash
from .models import Role, ModulePermission

User = get_user_model()

# --- AUTHENTICATION VIEWS ---

class UserLoginView(LoginView):
    template_name = 'accounts/login.html'
    authentication_form = CustomLoginForm
    redirect_authenticated_user = True


    def form_valid(self, form):
        user = form.get_user()
        if user.status != 1 or not user.is_active:
            messages.error(self.request, "Your account is currently inactive. Contact system administrator.")
            return self.form_invalid(form)
        login(self.request, user)
        messages.success(self.request, f"Welcome back, {user.first_name or user.username}!")
        if not user.is_staff and hasattr(user, 'supplier_profile'):
            return redirect('supplier_po_list')
        return redirect(self.get_success_url())


class UserLogoutView(LogoutView):
    next_page = reverse_lazy('login')

    def dispatch(self, request, *args, **kwargs):
        messages.info(request, "You have been successfully logged out.")
        return super().dispatch(request, *args, **kwargs)

class UserProfileView(LoginRequiredMixin, DetailView):
    model = User
    template_name = 'accounts/user_profile.html'
    context_object_name = 'user_obj'

    def get_object(self, queryset=None):
        return self.request.user


# --- ADMIN USER MANAGEMENT (CRUD) ---

class AdminUserListView(RBACPermissionMixin, ListView):
    model = User
    template_name = 'accounts/admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 15

    # RBAC permission
    module_name = 'accounts'
    required_permission = 'view'

    def get_queryset(self):
        queryset = User.objects.select_related('role').all().order_by('-date_joined')
        query = self.request.GET.get('q', '').strip()
        role_filter = self.request.GET.get('role', '').strip()

        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )

        if role_filter:
            queryset = queryset.filter(role__role_name=role_filter)

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['roles'] = Role.objects.order_by('role_name')
        context['query'] = self.request.GET.get('q', '').strip()
        context['selected_role'] = self.request.GET.get('role', '').strip()
        return context


class RoleListView(RBACPermissionMixin, ListView):
    model = Role
    template_name = 'accounts/admin/role_list.html'
    context_object_name = 'roles'

    module_name = 'accounts'
    required_permission = 'view'

    def get_queryset(self):
        return Role.objects.annotate(user_count=Count('customuser')).order_by('role_name')


class AdminUserDetailView(RBACPermissionMixin, DetailView):
    model = User
    template_name = 'accounts/admin/user_detail.html'
    context_object_name = 'user_obj'
    pk_url_kwarg = 'user_id'

    # RBAC permission
    module_name = 'accounts'
    required_permission = 'view'

class AdminUserSearchView(RBACPermissionMixin, ListView):
    model = User
    template_name = 'accounts/admin/user_list.html'
    context_object_name = 'users'
    paginate_by = 10

    # RBAC Mixin Settings
    module_name = 'accounts'
    required_permission = 'view'

    def get_queryset(self):
        queryset = User.objects.select_related('role').all()
        query = self.request.GET.get('q', '').strip()

        if query:
            queryset = queryset.filter(
                Q(username__icontains=query) |
                Q(first_name__icontains=query) |
                Q(last_name__icontains=query) |
                Q(email__icontains=query) |
                Q(phone__icontains=query)
            )

        role_filter = self.request.GET.get('role', '').strip()
        if role_filter:
            queryset = queryset.filter(role__role_name=role_filter)

        return queryset.order_by('-date_joined')

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('format') == 'json':
            queryset = self.get_queryset()
            rows_html = render_to_string(
                'accounts/admin/user_rows.html', 
                {'users': queryset}, 
                request=self.request
            )
            return JsonResponse({
                'rows_html': rows_html,
                'showing_count': queryset.count(),
            })

        return super().render_to_response(context, **response_kwargs)


class AdminUserCreateView(RBACPermissionMixin, CreateView):
    model = User
    form_class = AdminUserCreationForm
    template_name = 'accounts/admin/user_form.html'
    success_url = reverse_lazy('user_list')

    # RBAC permission
    module_name = 'accounts'
    required_permission = 'add'   

    def form_valid(self, form):
        messages.success(self.request, f"User '{form.cleaned_data['username']}' created successfully!")
        return super().form_valid(form)


class AdminUserUpdateView(RBACPermissionMixin, UpdateView):
    model = User
    form_class = AdminUserUpdateForm
    template_name = 'accounts/admin/user_form.html'
    pk_url_kwarg = 'user_id'
    success_url = reverse_lazy('user_list')

    # RBAC permission
    module_name = 'accounts'
    required_permission = 'edit'

    def form_valid(self, form):
        messages.success(self.request, f"User '{self.object.username}' updated successfully!")
        return super().form_valid(form)


class AdminUserDeleteView(RBACPermissionMixin, DeleteView):
    model = User
    pk_url_kwarg = 'user_id'
    success_url = reverse_lazy('user_list')
     # RBAC permission
    module_name = 'accounts'
    required_permission = 'delete'

    def delete(self, request, *args, **kwargs):
        user_to_delete = self.get_object()

        if user_to_delete == request.user:
            messages.error(request, "You cannot delete your own active admin account!")
            return redirect('user_list')

        #delete the user
        user_to_delete.delete()

        messages.success(request, f"User '{user_to_delete.username}' deleted successfully.")
        return redirect(self.success_url)



class AdminUserPasswordResetView(RBACPermissionMixin, FormView):
    template_name = 'accounts/admin/admin_password_change.html'
    form_class = AdminResetPasswordForm
    success_url = reverse_lazy('user_list')

    # RBAC permission
    module_name = 'accounts'
    required_permission = 'edit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['target_user'] = get_object_or_404(User, pk=self.kwargs['user_id'])
        return context

    def form_valid(self, form):
        target_user = get_object_or_404(User, pk=self.kwargs['user_id'])
        new_pass = form.cleaned_data['new_password']
        target_user.set_password(new_pass)
        target_user.save()
        update_session_auth_hash(self.request, self.request.user)
        messages.success(self.request, f"Password for user '{target_user.username}' reset successfully.")
        return super().form_valid(form)


@login_required
def manage_role_permissions(request, role_id):
    if not request.user.is_superuser:
        user_role = getattr(request.user, 'role', None)
        if not user_role:
            raise PermissionDenied("You do not have permission to manage roles.")
        try:
            account_permission = ModulePermission.objects.get(
                role=user_role,
                module_name='accounts',
            )
        except ModulePermission.DoesNotExist:
            raise PermissionDenied("You do not have permission to manage roles.")

        required_permission = 'can_edit' if request.method == 'POST' else 'can_view'
        if not getattr(account_permission, required_permission):
            raise PermissionDenied("You do not have permission to manage roles.")

    role = get_object_or_404(Role, pk=role_id)
    modules = [m[0] for m in ModulePermission.MODULE_CHOICES]

    # Ensure permission rows exist for all modules
    for mod in modules:
        ModulePermission.objects.get_or_create(role=role, module_name=mod)

    permissions = ModulePermission.objects.filter(role=role)

    if request.method == 'POST':
        for perm in permissions:
            perm.can_view = request.POST.get(f'can_view_{perm.id}') == 'on'
            perm.can_add = request.POST.get(f'can_add_{perm.id}') == 'on'
            perm.can_edit = request.POST.get(f'can_edit_{perm.id}') == 'on'
            perm.can_delete = request.POST.get(f'can_delete_{perm.id}') == 'on'
            perm.save()

        messages.success(request, f"Permissions for role '{role.role_name}' updated successfully.")
        return redirect('manage_role_permissions', role_id=role.role_id)

    return render(request, 'accounts/admin/role_permissions.html', {
        'role': role,
        'permissions': permissions
    })