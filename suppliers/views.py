from django.urls import reverse_lazy
from django.views.generic import ListView, CreateView, UpdateView, DeleteView, DetailView, View
from django.contrib.messages.views import SuccessMessageMixin
from django.db import transaction
from django.db.models import Q, Sum
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth import get_user_model

from accounts.mixins import RBACPermissionMixin
from .mixins import SupplierAccessMixin
from purchases.models import PurchaseOrder
from .models import Supplier
from .forms import SupplierAdminForm

User = get_user_model()


# ==========================================
# SUPPLIER PORTAL VIEWS (Portal Access)
# ==========================================

class SupplierPurchaseOrderListView(RBACPermissionMixin, SupplierAccessMixin, ListView):
    model = PurchaseOrder
    template_name = 'suppliers/supplier_po_list.html'
    context_object_name = 'purchase_orders'
    paginate_by = 10

    # RBAC Settings
    module_name = 'suppliers'
    required_permission = 'view'
    allow_staff = False

    def get_queryset(self):
        supplier = self.get_supplier()
        queryset = PurchaseOrder.objects.select_related('supplier')

        if supplier:
            # Strictly filter POs for the logged-in supplier only
            queryset = queryset.filter(supplier=supplier)

        status = self.request.GET.get('payment_status')
        if status:
            queryset = queryset.filter(payment_status=status)

        return queryset.order_by('-order_date')


class SupplierPayablesSummaryView(RBACPermissionMixin, SupplierAccessMixin, ListView):
    """View for supplier to track account payables and invoice statuses."""
    model = PurchaseOrder
    template_name = 'suppliers/admin/payables_summary.html'
    context_object_name = 'invoices'

    # RBAC Settings
    module_name = 'suppliers'
    required_permission = 'view'
    allow_staff = False

    def get_queryset(self):
        supplier = self.get_supplier()
        if supplier:
            return PurchaseOrder.objects.filter(
                supplier=supplier
            ).exclude(payment_status='PAID').order_by('order_date')
        return PurchaseOrder.objects.none()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        supplier = self.get_supplier()
        if supplier:
            unpaid_orders = PurchaseOrder.objects.filter(supplier=supplier).exclude(payment_status='PAID')
            total_payable = unpaid_orders.aggregate(total=Sum('net_payable_amount'))['total'] or 0
            context['total_payable'] = total_payable
            context['order_count'] = PurchaseOrder.objects.filter(supplier=supplier).count()
            context['paid_count'] = PurchaseOrder.objects.filter(supplier=supplier, payment_status='PAID').count()
        return context


class SupplierPurchaseOrderActionView(RBACPermissionMixin, SupplierAccessMixin, View):
    """Apply supplier actions only to a PO owned by the logged-in supplier."""

    module_name = 'suppliers'
    required_permission = 'edit'
    allow_staff = False

    transitions = {
        'accept': ('PENDING', 'ACCEPTED', 'Purchase order accepted.'),
        'deliver': ('ACCEPTED', 'RECEIVED', 'Purchase order marked as delivered.'),
    }

    def post(self, request, pk, action):
        if action not in self.transitions:
            return JsonResponse({'error': 'Unsupported action.'}, status=400)

        supplier = self.get_supplier()
        with transaction.atomic():
            order = get_object_or_404(
                PurchaseOrder.objects.select_for_update(),
                pk=pk,
                supplier=supplier,
            )
            expected_status, new_status, success_message = self.transitions[action]
            if order.order_status != expected_status:
                messages.error(request, 'This purchase order cannot be updated from its current status.')
            else:
                order.order_status = new_status
                order.save(update_fields=['order_status'])
                messages.success(request, success_message)

        return redirect('supplier_po_list')


# ==========================================
# ADMIN MANAGEMENT VIEWS (Admin Access)
# ==========================================

class SupplierListView(RBACPermissionMixin, ListView):
    model = Supplier
    template_name = 'suppliers/admin/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 10

    # RBAC Settings
    module_name = 'suppliers'
    required_permission = 'view'
    
    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Supplier.objects.filter(supplier_name__icontains=query)
        return Supplier.objects.all().order_by('supplier_id')


def stats():
    all_suppliers = Supplier.objects.all()
    return {
        'total': all_suppliers.count(),
    }


class SupplierSearchView(RBACPermissionMixin, ListView):
    model = Supplier
    template_name = 'suppliers/admin/supplier_list.html'
    context_object_name = 'suppliers'
    paginate_by = 10

    # RBAC Settings
    module_name = 'suppliers'
    required_permission = 'view'

    def get_queryset(self):
        queryset = Supplier.objects.select_related('user').all()
        query = self.request.GET.get('q', '').strip()
        organic_filter = self.request.GET.get('organic', '').strip()

        if query:
            queryset = queryset.filter(
                Q(supplier_name__icontains=query) |
                Q(contact_person__icontains=query) |
                Q(pan_vat_number__icontains=query) |
                Q(email__icontains=query)
            )

        if organic_filter == 'yes':
            queryset = queryset.filter(is_organic_certified=True)
        elif organic_filter == 'no':
            queryset = queryset.filter(is_organic_certified=False)

        return queryset.order_by('supplier_name')

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('format') == 'json':
            queryset = self.get_queryset()
            rows_html = render_to_string(
                'suppliers/admin/supplier_rows.html',
                {'suppliers': queryset},
                request=self.request
            )
            return JsonResponse({
                'rows_html': rows_html,
                'showing_count': queryset.count(),
            })

        return super().render_to_response(context, **response_kwargs)


class SupplierCreateView(RBACPermissionMixin, CreateView):
    model = Supplier
    form_class = SupplierAdminForm
    template_name = 'suppliers/admin/supplier_form.html'
    success_url = reverse_lazy('supplier_list')

    # RBAC Settings
    module_name = 'suppliers'
    required_permission = 'add'

    def form_invalid(self, form):
        print("=== FORM VALIDATION ERRORS ===")
        print(form.errors)
        print("==============================")
        return super().form_invalid(form)


class SupplierUpdateView(RBACPermissionMixin, SuccessMessageMixin, UpdateView):
    model = Supplier
    form_class = SupplierAdminForm
    template_name = 'suppliers/admin/supplier_form.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('supplier_list')
    success_message = "Supplier '%(supplier_name)s' was updated successfully."

    # RBAC Settings
    module_name = 'suppliers'
    required_permission = 'edit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['portal_account_exists'] = bool(
            self.object.user_id and User.objects.filter(pk=self.object.user_id).exists()
        )
        return context


class SupplierToggleStatusView(RBACPermissionMixin, View):
    # RBAC Mixin Settings
    module_name = 'suppliers'
    required_permission = 'edit'

    def post(self, request, pk):
        supplier = get_object_or_404(Supplier, pk=pk)
        supplier.is_active = not supplier.is_active
        supplier.save()
        
        status_str = "activated" if supplier.is_active else "deactivated"
        messages.success(request, f"Supplier '{supplier.supplier_name}' has been {status_str}.")

        return redirect('supplier_list')