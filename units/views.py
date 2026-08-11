from django.shortcuts import render, redirect, get_object_or_404
from .models import Unit
from django.contrib.auth.decorators import login_required
from .forms import UnitForm
from django.db.models import Q, ProtectedError
from django.core.paginator import Paginator
from django.contrib import messages

@login_required
def unit_list(request):
    query = request.GET.get('q')
    if query:
        units = Unit.objects.filter(name__icontains=query)
    else:
        units = Unit.objects.all()

    paginator = Paginator(units, 10)  # 10 per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'units/unit_list.html', {
        'page_obj': page_obj,
        'query': query,
        'title': 'Units'
    })


# Add new unit
@login_required
def unit_add(request):
    if request.method == "POST":
        form = UnitForm(request.POST)
        if form.is_valid():
            unit = form.save(commit=False)
        unit.save()
        return redirect('unit_list')
    form = UnitForm() 
    return render(request, 'units/unit_form.html', {'form': form, 'title': 'Add Unit'})


# Update unit
@login_required
def unit_edit(request, pk):
    unit = get_object_or_404(Unit, pk=pk)
    if request.method == 'POST':
        form = UnitForm(request.POST, instance=unit)
        if form.is_valid():
            form.save()
            messages.success(request, f'Unit "{unit.unit_name}" updated successfully.')
            return redirect('unit_list')
    else:
        form = UnitForm(instance=unit)
 
    return render(request, 'units/unit_form.html', {'form': form, 'title': 'Edit Unit'})
 

@login_required
def unit_toggle_status(request, pk):
    """Soft delete / reactivate — the safe default for products
    that already have transaction history."""
    p = get_object_or_404(Unit, pk=pk)
    Unit.status = 0 if Unit.status == 1 else 1
    Unit.save()
   
    return redirect('unit_list')