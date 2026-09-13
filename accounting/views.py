from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import FiscalYear
from .forms import FiscalYearForm
from .services import FiscalYearService

def fiscal_year_list(request):
    fiscal_years = FiscalYear.objects.all()
    return render(request, 'accounting/fy_list.html', {'fiscal_years': fiscal_years})

#
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