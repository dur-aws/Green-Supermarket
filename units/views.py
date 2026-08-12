from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, View
from .models import UnitOfMeasure
from .forms import UnitOfMeasureForm
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q

class UnitOfMeasureListView(LoginRequiredMixin, ListView):
    model = UnitOfMeasure
    template_name = 'units/unit_list.html'
    context_object_name = 'uoms'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return UnitOfMeasure.objects.filter(unit_name__icontains=query)
        return UnitOfMeasure.objects.all().order_by('uom_id')

def stats():
    all_units = UnitOfMeasure.objects.select_related('unit_of_measure')
    return {
        'total': all_units.count(),
    }


class UnitOfMeasureSearchView(LoginRequiredMixin, ListView):
    model = UnitOfMeasure
    template_name = 'uom/uom_list.html'
    context_object_name = 'uoms'
    paginate_by = 10

    def get_queryset(self):
        queryset = UnitOfMeasure.objects.all()
        query = self.request.GET.get('q', '').strip()

        if query:
            queryset = queryset.filter(
                Q(unit_name__icontains=query) | Q(notation__icontains=query)
            )

        return queryset.order_by('unit_name')

    def render_to_response(self, context, **response_kwargs):
        # Check if the request is coming from JavaScript fetch/AJAX
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('format') == 'json':
            queryset = self.get_queryset()
            
            # Render only the table rows HTML partial
            rows_html = render_to_string(
                'units/unit_rows.html', 
                {'uoms': queryset}, 
                request=self.request
            )
            
            return JsonResponse({
                'rows_html': rows_html,
                'showing_count': queryset.count(),
            })

        return super().render_to_response(context, **response_kwargs)

class UnitOfMeasureCreateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, CreateView):
    model = UnitOfMeasure
    form_class = UnitOfMeasureForm
    template_name = 'units/unit_form.html'
    success_url = reverse_lazy('uom_list')
    permission_required = 'units.add_unitofmeasure'
    success_message = "Unit of Measure '%(unit_name)s' was created successfully."

    def form_invalid(self, form):
        print("=== FORM VALIDATION ERRORS ===")
        print(form.errors)
        print("==============================")
        return super().form_invalid(form)

class UnitOfMeasureUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = UnitOfMeasure
    form_class = UnitOfMeasureForm
    template_name = 'units/unit_form.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('uom_list')
    permission_required = 'units.change_unitofmeasure'
    success_message = "Unit of Measure '%(unit_name)s' was updated successfully."

class UnitOfMeasureDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'units.delete_unitofmeasure'

    def get(self, request, pk):
        uom = get_object_or_404(UnitOfMeasure, pk=pk)
        uom.is_active = False 
        uom.save()
        messages.success(request, f"Unit '{uom.unit_name}' has been deactivated.")
        return redirect('uom_list')