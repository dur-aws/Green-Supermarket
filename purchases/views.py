from decimal import Decimal
from django.db import transaction
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string
from accounts.mixins import RBACPermissionMixin
from .models import PurchaseOrder, PurchaseDetail
from .forms import PurchaseOrderForm, PurchaseDetailFormSet
from django.http import JsonResponse

from decimal import Decimal, InvalidOperation
from django.views import View
from .services import calculate_po_totals

class PurchaseOrderListView(RBACPermissionMixin, ListView):
    model = PurchaseOrder
    template_name = 'purchases/po_list.html'
    context_object_name = 'orders'
    paginate_by = 15

    module_name = 'purchases'
    required_permission = 'view'

    def get_queryset(self):
        queryset = PurchaseOrder.objects.select_related('supplier', 'received_by_user')
        query = self.request.GET.get('q')
        if query:
            return queryset.filter(invoice_number__icontains=query)
        return queryset.order_by('purchase_id')

class PurchaseOrderSearchView(RBACPermissionMixin, ListView):
    model = PurchaseOrder
    template_name = 'purchases/po_list.html'
    context_object_name = 'orders'
    paginate_by = 10

    # RBAC Mixin Settings
    module_name = 'orders'
    required_permission = 'view'

    def get_queryset(self):
        queryset = PurchaseOrder.objects.select_related('supplier', 'received_by_user')
        query = self.request.GET.get('q', '').strip()

        if query:
            queryset = queryset.filter(
                Q(invoice_number__icontains=query) |
                Q(supplier__supplier_name__icontains=query) |
                Q(purchase_id__icontains=query)
            )

        return queryset.order_by('purchase_id')

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('format') == 'json':
            queryset = self.get_queryset()
            rows_html = render_to_string(
                'purchases/po_rows.html', 
                {'orders': queryset}, 
                request=self.request
            )
            return JsonResponse({
                'rows_html': rows_html,
                'showing_count': queryset.count(),
            })

        return super().render_to_response(context, **response_kwargs)



class PurchaseOrderCreateView(RBACPermissionMixin, SuccessMessageMixin, CreateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    template_name = 'purchases/po_form.html'
    success_url = reverse_lazy('po_list')
    success_message = "Purchase Order created successfully."

    module_name = 'purchases'
    required_permission = 'add'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = PurchaseDetailFormSet(self.request.POST)
        else:
            context['formset'] = PurchaseDetailFormSet()
        return context
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']
        if not form.is_valid():
            print("Master Form Errors:", form.errors)
        if not formset.is_valid():
            print("Formset Errors:", formset.errors)

        if formset.is_valid():
            with transaction.atomic():
                self.object = form.save(commit=False)
                self.object.received_by_user = self.request.user

            line_items = [
                {'quantity': f.cleaned_data['received_quantity'] or f.cleaned_data['ordered_quantity'],
                 'unit_price': f.cleaned_data['actual_unit_price'] or f.cleaned_data['agreed_unit_price']}
                for f in formset.forms if not f.cleaned_data.get('DELETE')
            ]
            totals = calculate_po_totals(line_items, form.cleaned_data['tds_rate'])

            # Server-computed values overwrite whatever the browser submitted
            for field, value in totals.items():
                setattr(self.object, field, value)

            self.object.save()
            formset.instance = self.object
            formset.save()

            messages.success(self.request, 'Purchase order saved')
            return redirect(self.get_success_url())
        else:
        # Re-render context with formset errors if invalid
            return self.render_to_response(self.get_context_data(form=form, formset=formset))
    
        

class PurchaseOrderCalculateView(RBACPermissionMixin, View):
    """Live recalculation endpoint — the browser previews this, but the
    same function runs again server-side on actual save, so it can't be spoofed."""

    module_name = 'purchases'
    required_permission = 'view'

    def post(self, request, *args, **kwargs):
        try:
            tds_rate = Decimal(request.POST.get('tds_rate', '0') or '0')
            items = []
            index = 0
            while f'items[{index}][quantity]' in request.POST:
                qty = request.POST.get(f'items[{index}][quantity]', '0') or '0'
                price = request.POST.get(f'items[{index}][unit_price]', '0') or '0'
                items.append({'quantity': qty, 'unit_price': price})
                index += 1

            totals = calculate_po_totals(items, tds_rate)
            return JsonResponse({k: str(v) for k, v in totals.items()})

        except (InvalidOperation, ValueError) as e:
            return JsonResponse({'error': 'Invalid number in calculation.'}, status=400)
        
class PurchaseOrderUpdateView(RBACPermissionMixin, SuccessMessageMixin, UpdateView):
    model = PurchaseOrder
    form_class = PurchaseOrderForm
    pk_url_kwarg = 'pk'  # Ensure URL route passes <int:pk> or update to 'purchase_id'
    template_name = 'purchases/po_form.html'
    success_url = reverse_lazy('po_list')
    success_message = "Receiving records and inventory updated successfully."

    module_name = 'purchases'
    required_permission = 'edit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['formset'] = PurchaseDetailFormSet(self.request.POST, instance=self.object)
        else:
            context['formset'] = PurchaseDetailFormSet(instance=self.object)
        
        return context
    
    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['formset']

        if not formset.is_valid():
            return self.render_to_response(self.get_context_data(form=form, formset=formset))

        with transaction.atomic():
            old_status = PurchaseOrder.objects.get(pk=self.object.pk).order_status
            self.object = form.save(commit=False)

            # Handle deleted items
            for deleted_form in formset.deleted_forms:
                if deleted_form.instance.pk:
                    deleted_form.instance.delete()

            items = formset.save(commit=False)
            line_items_data = []

            for item in items:
                item.purchase = self.object
                qty = item.received_quantity or item.ordered_quantity or Decimal('0.00')
                price = item.actual_unit_price or item.agreed_unit_price or Decimal('0.00')
                item.subtotal = qty * price
                item.save()
                line_items_data.append({'quantity': qty, 'unit_price': price})

            formset.save_m2m()
            print("Line items data:", line_items_data)

            # Totals
            totals = calculate_po_totals(line_items_data, self.object.tds_rate or Decimal('0.00'))
            for field, value in totals.items():
                setattr(self.object, field, value)

            # Stock update
            if old_status != 'RECEIVED' and self.object.order_status == 'RECEIVED':
                for item in formset.cleaned_data:
                    if item and not item.get('DELETE'):
                        rec_qty = item.get('received_quantity') or Decimal('0.00')
                        if rec_qty > 0:
                            print('rec_quantit', rec_qty)
                            from inventory.services import create_inventory_batches_from_po
                            create_inventory_batches_from_po(self.object)
            self.object.save()

            
        messages.success(self.request, self.success_message)
        return super().form_valid(form)  

class PurchaseOrderDetailView(RBACPermissionMixin, DetailView):
    model = PurchaseOrder
    pk_url_kwarg = 'pk'
    template_name = 'purchases/po_detail.html'
    context_object_name = 'order'

    module_name = 'purchases'
    required_permission = 'view'