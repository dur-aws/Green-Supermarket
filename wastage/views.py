from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import ValidationError
from django.views.generic import FormView, ListView

from accounts.mixins import RBACPermissionMixin
from inventory.models import InventoryBatch
from inventory.services import process_stock_adjustment

from .forms import WastageForm
from .models import Wastages


class WastageListView(RBACPermissionMixin, ListView):
	model = Wastages
	template_name = 'wastage/list.html'
	context_object_name = 'wastages'
	paginate_by = 25
	module_name = 'inventory'
	required_permission = 'view'


class WastageCreateView(RBACPermissionMixin, FormView):
	template_name = 'wastage/form.html'
	form_class = WastageForm
	module_name = 'inventory'
	required_permission = 'edit'

	def dispatch(self, request, *args, **kwargs):
		self.batch = get_object_or_404(InventoryBatch, pk=kwargs['batch_id'])
		return super().dispatch(request, *args, **kwargs)

	def get_form_kwargs(self):
		kwargs = super().get_form_kwargs()
		kwargs['batch'] = self.batch
		return kwargs

	def get_context_data(self, **kwargs):
		context = super().get_context_data(**kwargs)
		context['batch'] = self.batch
		return context

	def form_valid(self, form):
		try:
			process_stock_adjustment(
				self.batch.pk,
				self.request.user,
				-form.cleaned_data['quantity'],
				'WASTAGE',
				f"{form.cleaned_data['reason']}: {form.cleaned_data['notes']}".strip(': '),
			)
		except ValidationError as error:
			form.add_error(None, error.message)
			return self.form_invalid(form)
		messages.success(self.request, 'Wastage recorded and stock adjusted.')
		return redirect('wastage_list')
