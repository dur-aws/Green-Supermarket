from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, FormView, ListView

from accounts.mixins import RBACPermissionMixin

from .forms import RefundForm, ReturnInspectionForm, SalesReturnForm
from .models import CreditMemo, InventoryReturnReceipt, SalesReturn
from .returns import confirm_refund, create_refund, create_rma, receive_and_inspect_return
from .returns import remaining_returnable_quantity


class SalesReturnListView(RBACPermissionMixin, ListView):
    model = SalesReturn
    template_name = 'sales_return_list.html'
    context_object_name = 'returns'
    paginate_by = 25
    module_name = 'sales'
    required_permission = 'view'

    def get_queryset(self):
        return SalesReturn.objects.select_related('sale', 'customer', 'created_by').order_by('-created_at')


class SalesReturnCreateView(RBACPermissionMixin, FormView):
    template_name = 'return_form.html'
    form_class = SalesReturnForm
    module_name = 'sales'
    required_permission = 'add'

    def get_initial(self):
        initial = super().get_initial()
        initial['invoice_no'] = self.request.GET.get('invoice_no', '')
        return initial

    def form_valid(self, form):
        sale = form.cleaned_data['sale']
        items = []
        for key, value in self.request.POST.items():
            if not key.startswith('quantity_') or not value:
                continue
            try:
                sale_item_id = int(key.split('_', 1)[1])
            except ValueError:
                continue
            items.append({'sale_item_id': sale_item_id, 'quantity': value})
        try:
            rma = create_rma(
                sale_id=sale.pk,
                items=items,
                user=self.request.user,
                reason=form.cleaned_data.get('reason', ''),
            )
        except Exception as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'{rma.rma_number} created.')
        return redirect('sales_return_detail', pk=rma.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        invoice_no = self.request.GET.get('invoice_no') or self.request.POST.get('invoice_no')
        if invoice_no:
            sale = context['form'].cleaned_data.get('sale') if context['form'].is_bound and context['form'].is_valid() else None
            if sale is None:
                from .models import Sale
                sale = Sale.objects.filter(invoice_no=invoice_no).first()
            context['sale'] = sale
            if sale:
                context['sale_items'] = sale.items.select_related('variant', 'batch')
                for item in context['sale_items']:
                    item.remaining_returnable_quantity = remaining_returnable_quantity(item)
        return context


class SalesReturnDetailView(RBACPermissionMixin, DetailView):
    model = SalesReturn
    template_name = 'return_detail.html'
    context_object_name = 'rma'
    module_name = 'sales'
    required_permission = 'view'

    def get_queryset(self):
        return SalesReturn.objects.select_related('sale', 'customer', 'created_by').prefetch_related('items__sale_item__variant')


class ReturnReceiveView(RBACPermissionMixin, FormView):
    template_name = 'return_receive.html'
    form_class = ReturnInspectionForm
    module_name = 'sales'
    required_permission = 'edit'

    def dispatch(self, request, *args, **kwargs):
        self.rma = get_object_or_404(SalesReturn, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['rma'] = self.rma
        return kwargs

    def form_valid(self, form):
        inspections = {}
        for item in self.rma.items.all():
            inspections[item.pk] = {
                'quantity': form.cleaned_data[f'quantity_{item.pk}'],
                'condition': form.cleaned_data[f'condition_{item.pk}'],
                'note': form.cleaned_data.get(f'note_{item.pk}', ''),
            }
        try:
            receipt, memo = receive_and_inspect_return(
                rma_id=self.rma.pk, inspections=inspections, user=self.request.user
            )
        except Exception as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'{receipt.receipt_number} and {memo.memo_number} created.')
        return redirect('inventory_return_receipt', pk=receipt.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['rma'] = self.rma
        return context


class InventoryReturnReceiptView(RBACPermissionMixin, DetailView):
    model = InventoryReturnReceipt
    template_name = 'inventory_return_receipt.html'
    context_object_name = 'receipt'
    module_name = 'sales'
    required_permission = 'view'

    def get_queryset(self):
        return InventoryReturnReceipt.objects.select_related('rma__sale', 'received_by', 'inspected_by').prefetch_related('items__return_item__sale_item__variant')


class CreditMemoView(RBACPermissionMixin, DetailView):
    model = CreditMemo
    template_name = 'credit_memo.html'
    context_object_name = 'credit_memo'
    module_name = 'sales'
    required_permission = 'view'

    def get_queryset(self):
        return CreditMemo.objects.select_related('sale', 'receipt__rma', 'created_by').prefetch_related('receipt__items__return_item__sale_item__variant')


class RefundCreateView(RBACPermissionMixin, FormView):
    template_name = 'refund_form.html'
    form_class = RefundForm
    module_name = 'sales'
    required_permission = 'edit'

    def dispatch(self, request, *args, **kwargs):
        self.credit_memo = get_object_or_404(CreditMemo, pk=kwargs['pk'])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            refund = create_refund(
                credit_memo_id=self.credit_memo.pk,
                method=form.cleaned_data['method'],
                user=self.request.user,
            )
        except Exception as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f'Refund {refund.refund_reference} is pending confirmation.')
        return redirect('credit_memo', pk=self.credit_memo.pk)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['credit_memo'] = self.credit_memo
        return context


class RefundConfirmView(RBACPermissionMixin, View):
    module_name = 'sales'
    required_permission = 'edit'

    def post(self, request, *args, **kwargs):
        refund = get_object_or_404(
            CreditMemo.objects.select_related('payment_refund'), pk=kwargs['pk']
        ).payment_refund
        try:
            confirm_refund(refund_id=refund.pk, user=request.user)
        except Exception as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, 'Refund confirmed and posted as paid.')
        return redirect('credit_memo', pk=kwargs['pk'])
