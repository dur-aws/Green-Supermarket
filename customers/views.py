from django.contrib import messages
from django.db import transaction
from django.db.models import Avg, Count, Exists, OuterRef, Q, Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView, View

from accounts.mixins import RBACPermissionMixin
from payments.models import Payment
from sales.models import Sale

from .forms import CustomerForm, MembershipForm, QuickCustomerForm
from .models import Customer, CustomerScheme, Membership


def generate_customer_code():
    last = Customer.objects.order_by('-customer_id').first()
    next_id = (last.customer_id + 1) if last else 1
    return f'CUST-{next_id:04d}'


class CustomerListView(RBACPermissionMixin, ListView):
    module_name = 'customers'
    required_permission = 'view'
    model = Customer
    template_name = 'customers/customer_list.html'
    context_object_name = 'customers'
    paginate_by = 25

    def get_queryset(self):
        customers = Customer.objects.annotate(
            has_active_membership=Exists(
                Membership.objects.filter(customer_id=OuterRef('pk'), status='ACTIVE')
            )
        ).order_by('customer_id')
        query = self.request.GET.get('q', '').strip()
        if query:
            customers = customers.filter(
                Q(customer_code__icontains=query) |
                Q(customer_name__icontains=query) |
                Q(phone__icontains=query) |
                Q(email__icontains=query)
            )
        status_filter = self.request.GET.get('status', '')
        if status_filter:
            customers = customers.filter(status=status_filter)
        member_filter = self.request.GET.get('member', '')
        if member_filter == 'member':
            customers = customers.filter(has_active_membership=True)
        elif member_filter == 'non_member':
            customers = customers.filter(has_active_membership=False)
        return customers

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'query': self.request.GET.get('q', '').strip(),
            'status_filter': self.request.GET.get('status', ''),
            'member_filter': self.request.GET.get('member', ''),
            'total_count': Customer.objects.count(),
            'active_count': Customer.objects.filter(status='ACTIVE').count(),
            'member_count': Customer.objects.filter(memberships__status='ACTIVE').distinct().count(),
        })
        return context

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest':
            rows_html = render_to_string(
                'customers/customer_rows.html',
                {'customers': context['customers']},
                request=self.request,
            )
            return JsonResponse({'rows_html': rows_html})
        return super().render_to_response(context, **response_kwargs)


class CustomerCreateView(RBACPermissionMixin, CreateView):
    module_name = 'customers'
    required_permission = 'add'
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customer_list')

    def get_initial(self):
        initial = super().get_initial()
        initial.update({'customer_code': generate_customer_code(), 'status': 'ACTIVE'})
        return initial

    def form_valid(self, form):
        if not form.instance.customer_code:
            form.instance.customer_code = generate_customer_code()
        response = super().form_valid(form)
        messages.success(self.request, f'Customer {self.object.customer_code} registered successfully.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Add Customer'
        return context


class CustomerUpdateView(RBACPermissionMixin, UpdateView):
    module_name = 'customers'
    required_permission = 'edit'
    model = Customer
    form_class = CustomerForm
    template_name = 'customers/customer_form.html'
    success_url = reverse_lazy('customer_list')

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Customer {self.object.customer_code} updated.')
        return response

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Edit Customer'
        return context


class CustomerDeactivateView(RBACPermissionMixin, View):
    module_name = 'customers'
    required_permission = 'edit'

    def post(self, request, pk):
        customer = get_object_or_404(Customer, pk=pk)
        customer.status = 'INACTIVE' if customer.status == 'ACTIVE' else 'ACTIVE'
        customer.save(update_fields=['status'])
        messages.success(request, f'Customer {customer.customer_code} status changed to {customer.status}.')
        return redirect('customer_list')

    def get(self, request, pk):
        return redirect('customer_list')


class CustomerQuickAddView(RBACPermissionMixin, View):
    module_name = 'customers'
    required_permission = 'add'

    def post(self, request):
        form = QuickCustomerForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'errors': form.errors}, status=400)
        customer = form.save()
        return JsonResponse({
            'id': customer.customer_id,
            'code': customer.customer_code,
            'name': customer.customer_name,
            'phone': customer.phone or '',
            'email': customer.email or '',
            'pan_vat_number': customer.pan_vat_number or '',
        }, status=201)


class CustomerProfileView(RBACPermissionMixin, DetailView):
    module_name = 'customers'
    required_permission = 'view'
    model = Customer
    template_name = 'customers/customer_profile.html'
    context_object_name = 'customer'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        customer = self.object
        context.update({
            'memberships': customer.memberships.all().order_by('-start_date'),
            'sales': Sale.objects.filter(customer=customer).select_related('user').order_by('-sale_date'),
            'transaction_count': customer.transaction_count,
            'current_scheme': customer.current_scheme,
            'is_member': customer.is_member,
            'total_spending': customer.total_spending,
            'average_bill': customer.average_bill,
            'total_discount': customer.total_discount,
            'last_purchase': customer.last_purchase,
        })
        return context


class MembershipCreateView(RBACPermissionMixin, CreateView):
    module_name = 'customers'
    required_permission = 'add'
    model = Membership
    form_class = MembershipForm
    template_name = 'customers/membership_form.html'

    def dispatch(self, request, *args, **kwargs):
        self.customer = get_object_or_404(Customer, pk=kwargs['customer_id'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.customer = self.customer
        with transaction.atomic():
            response = super().form_valid(form)
        messages.success(self.request, f'Membership registered for {self.customer.customer_name}.')
        return response

    def get_success_url(self):
        return reverse_lazy('customer_profile', kwargs={'pk': self.customer.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


class MembershipStatusView(RBACPermissionMixin, View):
    module_name = 'customers'
    required_permission = 'edit'

    def post(self, request, pk, new_status):
        membership = get_object_or_404(Membership, pk=pk)
        if new_status not in {'ACTIVE', 'EXPIRED', 'CANCELLED'}:
            return redirect('customer_list')
        membership.status = new_status
        membership.save()
        messages.success(request, f'Membership status set to {new_status}.')
        return redirect('customer_profile', pk=membership.customer.pk)

    def get(self, request, pk, new_status):
        return redirect('customer_list')


class CustomerSearchAPIView(RBACPermissionMixin, View):
    module_name = 'customers'
    required_permission = 'view'

    def get(self, request):
        query = request.GET.get('q', '').strip()
        customers = Customer.objects.none()
        if query:
            customers = Customer.objects.filter(
                Q(customer_code__icontains=query) |
                Q(customer_name__icontains=query) |
                Q(phone__icontains=query) |
                Q(email__icontains=query),
                status='ACTIVE',
            )[:10]
        return JsonResponse({'results': [
            {
                'id': customer.customer_id,
                'code': customer.customer_code,
                'name': customer.customer_name,
                'phone': customer.phone or '',
                'email': customer.email or '',
            }
            for customer in customers
        ]})


class CustomerPurchaseHistoryView(RBACPermissionMixin, ListView):
    module_name = 'customers'
    required_permission = 'view'
    template_name = 'customers/purchase_history.html'
    context_object_name = 'sales'
    paginate_by = 25
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['pk'])
        return Sale.objects.filter(customer=self.customer).select_related('user').order_by('-sale_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


class CustomerPaymentHistoryView(RBACPermissionMixin, ListView):
    module_name = 'customers'
    required_permission = 'view'
    template_name = 'customers/payment_history.html'
    context_object_name = 'payments'
    paginate_by = 25
    def get_queryset(self):
        self.customer = get_object_or_404(Customer, pk=self.kwargs['pk'])
        return Payment.objects.filter(sale__customer=self.customer).select_related('sale').order_by('-created_at')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['customer'] = self.customer
        return context


class CRMDashboardView(RBACPermissionMixin, TemplateView):
    module_name = 'customers'
    required_permission = 'view'
    template_name = 'customers/crm_dashboard.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        completed = Sale.objects.filter(sale_status='COMPLETED')
        context.update({
            'customer_count': Customer.objects.count(),
            'member_count': Customer.objects.filter(memberships__status='ACTIVE').distinct().count(),
            'transaction_count': completed.count(),
            'total_spending': completed.aggregate(total=Sum('grand_total'))['total'] or 0,
            'average_bill': completed.aggregate(average=Avg('grand_total'))['average'] or 0,
            'scheme_count': CustomerScheme.objects.filter(status='ACTIVE').count(),
        })
        return context


class CRMReportsView(RBACPermissionMixin, ListView):
    module_name = 'customers'
    required_permission = 'view'
    template_name = 'customers/crm_reports.html'
    context_object_name = 'customers'

    def get_queryset(self):
        report_type = self.request.GET.get('type', 'spending')
        customers = Customer.objects.all()
        if report_type == 'transactions':
            return customers.annotate(
                report_transactions=Count('sale', filter=Q(sale__sale_status='COMPLETED'))
            ).order_by('-report_transactions', 'customer_name')
        if report_type == 'membership':
            return customers.annotate(
                report_memberships=Count('memberships'),
                report_active_memberships=Count('memberships', filter=Q(memberships__status='ACTIVE')),
            ).order_by('-report_active_memberships', 'customer_name')
        if report_type == 'loyalty':
            return customers.order_by('-customer_type', '-customer_name')
        return customers.order_by('customer_name')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        report_type = self.request.GET.get('type', 'spending')
        titles = {
            'spending': 'Customer Spending Report',
            'transactions': 'Customer Transaction Report',
            'membership': 'Membership Report',
            'loyalty': 'Loyalty Report',
        }
        context['report_type'] = report_type if report_type in titles else 'spending'
        context['title'] = titles.get(report_type, titles['spending'])
        return context
