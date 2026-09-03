# Create your views here.
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from django.db.models import F
from django.core.paginator import Paginator
from .forms import StockAdjustmentForm


from .services import process_stock_adjustment
from accounts.mixins import RBACPermissionMixin
from django.views.generic import ListView, FormView
from .models import InventoryBatch, StockAdjustment

class InventoryStockListView(RBACPermissionMixin, ListView):
    model = InventoryBatch
    template_name = 'inventory/stock_list.html'
    context_object_name = 'batches'

    
    module_name = 'inventory'
    required_permission = 'view'
    

    def get_queryset(self):
        return InventoryBatch.objects.select_related('variant',  'supplier')\
                                     .filter(batch_status='ACTIVE')\
                                     .order_by('batch_id')

class StockAdjustmentCreateView(RBACPermissionMixin, FormView):
    template_name = 'inventory/stock_adjustment_form.html'
    form_class = StockAdjustmentForm

    module_name = "inventory"
    required_permission = "edit"

    def dispatch(self, request, *args, **kwargs):
        self.batch = get_object_or_404(InventoryBatch, pk=self.kwargs['batch_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['batch'] = self.batch
        return context

    def form_valid(self, form):
        try:
            process_stock_adjustment(
                batch_id=self.batch.pk,
                user=self.request.user,
                quantity_change=form.cleaned_data['quantity_change'],
                reason_code=form.cleaned_data['reason_code'],
                notes=form.cleaned_data['notes']
            )
            print("HI")
            messages.success(self.request, f"Stock adjustment saved for batch {self.batch.batch_number}.")
            return redirect('stock_list')
        except Exception as e:
            messages.error(self.request, f"Error adjusting stock: {str(e)}")
            return self.form_invalid(form)

class StockAdjustmentHistoryListView(RBACPermissionMixin, ListView):
    model = StockAdjustment
    template_name = 'inventory/adjustment_history.html'
    context_object_name = 'adjustments'
    paginate_by = 50

    module_name = "inventory"
    permission_required = "view"
