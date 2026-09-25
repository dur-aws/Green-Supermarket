from django.contrib import messages
from django.db.models import Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView

from accounts.mixins import RBACPermissionMixin
from .forms import ExpenseForm
from .models import Expense
from .services import post_expense


class ExpenseListView(RBACPermissionMixin, ListView):
	model = Expense
	template_name = 'expenses/expense_list.html'
	context_object_name = 'expenses'
	paginate_by = 25
	module_name = 'accounting'
	required_permission = 'view'

	def get_queryset(self):
		queryset = Expense.objects.select_related('fiscal_year', 'created_by', 'journal_entry')
		query = self.request.GET.get('q', '').strip()
		if query:
			queryset = queryset.filter(
				Q(description__icontains=query)
				| Q(reference_number__icontains=query)
				| Q(expense_type__icontains=query)
			)
		return queryset


class ExpenseCreateView(RBACPermissionMixin, CreateView):
	model = Expense
	form_class = ExpenseForm
	template_name = 'expenses/expense_form.html'
	success_url = reverse_lazy('expense_list')
	module_name = 'accounting'
	required_permission = 'add'

	def form_valid(self, form):
		form.instance.created_by = self.request.user
		response = super().form_valid(form)
		try:
			post_expense(self.object, self.request.user)
		except Exception as exc:
			self.object.delete()
			form.add_error(None, str(exc))
			return self.form_invalid(form)
		messages.success(self.request, 'Expense recorded and posted to the General Ledger.')
		return response
