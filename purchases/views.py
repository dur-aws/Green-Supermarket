from decimal import Decimal
from django.db import transaction
from django.urls import reverse_lazy
from django.shortcuts import redirect
from django.views.generic import ListView, CreateView, UpdateView, DetailView
from django.views.generic.edit import ModelFormMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.db.models import Q
from django.template.loader import render_to_string
from accounts.mixins import RBACPermissionMixin
from inventory.services import create_inventory_batches_from_po, reconcile_po_inventory
from .models import PurchaseOrder, PurchaseDetail
from .forms import PurchaseOrderForm, PurchaseDetailFormSet
from django.http import JsonResponse

from decimal import Decimal, InvalidOperation
from django.views import View
from .services import calculate_po_totals
from django.core.exceptions import ValidationError

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
    module_name = 'purchases'
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
                supplier = form.cleaned_data.get('supplier')
                tds_rate = Decimal(str(form.cleaned_data.get('tds_rate') or '0.00')) if supplier and supplier.pan_vat_number else Decimal('0.00')
                line_items = [
                        {
                            'quantity': f.cleaned_data['received_quantity'] or f.cleaned_data['ordered_quantity'],
                            'unit_price': f.cleaned_data['actual_unit_price'] or f.cleaned_data['agreed_unit_price'],
                            'vat_percent': Decimal(getattr(f.cleaned_data.get('variant'), 'vat_status', '0'))
                        }
                        for f in formset.forms if not f.cleaned_data.get('DELETE')
                    ]

                totals = calculate_po_totals(line_items, tds_rate)

                for field, value in totals.items():
                    setattr(self.object, field, value)

                self.object.save()
                formset.instance = self.object
                formset.save()

                if self.object.order_status == 'RECEIVED':
                    create_inventory_batches_from_po(self.object)

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
            tds_rate = Decimal('0.00')
            items = []
            index = 0
            while f'items[{index}][quantity]' in request.POST:
                qty = request.POST.get(f'items[{index}][quantity]', '0') or '0'
                price = request.POST.get(f'items[{index}][unit_price]', '0') or '0'
                variant_id = request.POST.get(f'items[{index}][variant]')
                vat_percent = Decimal('0.00')
                if variant_id:
                    from products.models import ProductVariant
                    variant = ProductVariant.objects.filter(pk=variant_id).first()
                    if variant and getattr(variant, 'is_vatable', False):
                        vat_percent = Decimal(str(getattr(variant, 'vat_status', 0)))
                items.append({'quantity': qty, 'unit_price': price, 'vat_percent': str(vat_percent)})
                index += 1

            supplier_id = request.POST.get('supplier')
            if supplier_id:
                from suppliers.models import Supplier
                supplier = Supplier.objects.filter(pk=supplier_id).only('pan_vat_number').first()
                if supplier and supplier.pan_vat_number:
                    tds_rate = Decimal(str(request.POST.get('tds_rate', '0') or '0'))
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

        try:
            with transaction.atomic():
                # Get existing status from database before modification
                old_status = PurchaseOrder.objects.get(pk=self.object.pk).order_status if self.object.pk else None
                
                # Save parent PO instance
                self.object = form.save(commit=False)

                # 1. Handle deleted line items
                for deleted_form in formset.deleted_forms:
                    if deleted_form.instance.pk:
                        deleted_form.instance.delete()

                # 2. Save line items and aggregate totals
                items = formset.save(commit=False)
                line_items_data = []

                for item in items:
                    item.purchase = self.object
                    qty = item.received_quantity or item.ordered_quantity or Decimal('0.00')
                    price = item.actual_unit_price or item.agreed_unit_price or Decimal('0.00')
                    item.subtotal = qty * price
                    variant = item.variant
                    vat_percent = Decimal('0.00')
                    if variant and getattr(variant, 'is_vatable', False):
                        vat_percent = getattr(variant, 'vat_percent', Decimal('0.00')) or Decimal('0.00')
                    item.save()
                    line_items_data.append({'quantity': qty, 'unit_price': price, 'vat_percent': str(vat_percent)})

                formset.save_m2m()

                # 3. Recalculate PO Financial Totals
                if self.object.supplier and self.object.supplier.pan_vat_number:
                    tds_rate = self.object.tds_rate or Decimal('0.00')
                else:
                    tds_rate = Decimal('0.00')
                totals = calculate_po_totals(line_items_data, tds_rate)
                for field, value in totals.items():
                    setattr(self.object, field, value)

                self.object.save()

                # 4. Inventory Synchronization Logic
                new_status = self.object.order_status

                if old_status != 'RECEIVED' and new_status == 'RECEIVED':
                    # First time receiving: Create new inventory batches ONCE (outside items loop)
                    create_inventory_batches_from_po(self.object)
                    messages.success(self.request, "Purchase Order received and inventory batches created.")

                elif old_status == 'RECEIVED' and new_status == 'RECEIVED':
                    # Already received & updating: Reconcile existing inventory batches
                    reconcile_po_inventory(
                        purchase_order=self.object,
                        user=self.request.user
                    )
                    messages.success(self.request, "Purchase Order updated and inventory reconciled successfully.")

        except ValidationError as e:
            messages.error(self.request, e.message if hasattr(e, 'message') else str(e))
            return self.form_invalid(form)
        except Exception as e:
            messages.error(self.request, f"An error occurred: {str(e)}")
            return self.form_invalid(form)

        # Return standard FormView success redirect without re-saving form
        return super(ModelFormMixin, self).form_valid(form)
class PurchaseOrderDetailView(RBACPermissionMixin, DetailView):
    model = PurchaseOrder
    pk_url_kwarg = 'pk'
    template_name = 'purchases/po_detail.html'
    context_object_name = 'order'

    module_name = 'purchases'
    required_permission = 'view'