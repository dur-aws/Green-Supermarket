from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.generic import ListView

from accounts.mixins import RBACPermissionMixin
from .models import FiscalYear, JournalEntry
from .forms import FiscalYearForm
from .services import FiscalYearService

def fiscal_year_list(request):
    fiscal_years = FiscalYear.objects.all()
    return render(request, 'accounting/fy_list.html', {'fiscal_years': fiscal_years})


def fiscal_year_create(request):
    if request.method == 'POST':
        form = FiscalYearForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Fiscal Year created successfully.")
            return redirect('fiscal_year_list')
    else:
        # Pre-fill defaults using the service
        defaults = FiscalYearService.get_current_fy_info()
        form = FiscalYearForm(initial=defaults)
        
    return render(request, 'accounting/fy_form.html', {'form': form, 'title': 'Create Fiscal Year'})

def fiscal_year_activate(request, pk):
    FiscalYearService.set_active_fiscal_year(pk)
    messages.success(request, "Active fiscal year updated.")
    return redirect('fiscal_year_list')

def fiscal_year_toggle_close(request, pk):
    fy = FiscalYearService.toggle_close_status(pk)
    status = "closed" if fy.is_closed else "re-opened"
    messages.info(request, f"Fiscal Year {fy.name} has been {status}.")
    return redirect('fiscal_year_list')

class JournalListView(RBACPermissionMixin, ListView):
    model = JournalEntry
    template_name = 'journal.html'
    context_object_name = 'journals'

    paginate_by = 14
    module_name = 'accounting'
    required_permission = 'view'

    # Latest journal entry first
    ordering = ['-entry_id']

    

    def get_queryset(self):
        queryset = (
            JournalEntry.objects
            .select_related('fiscal_year', 'created_by')
            .prefetch_related('items__account')
            .order_by('-entry_id')
        )

        # Date filters
        from_date = self.request.GET.get('from_date')
        to_date = self.request.GET.get('to_date')

        if from_date:
            queryset = queryset.filter(
                entry_date__gte=from_date
            )

        if to_date:
            queryset = queryset.filter(
                entry_date__lte=to_date
            )

        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        context['from_date'] = self.request.GET.get(
            'from_date', ''
        )

        context['to_date'] = self.request.GET.get(
            'to_date', ''
        )

        return context