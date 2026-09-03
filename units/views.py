from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.views.generic import ListView, CreateView, UpdateView, View
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q

from .models import UnitOfMeasure
from .forms import UnitOfMeasureForm
from accounts.mixins import RBACPermissionMixin


# 1. Main List View
class UnitOfMeasureListView(RBACPermissionMixin, ListView):
    model = UnitOfMeasure
    template_name = 'units/unit_list.html'
    context_object_name = 'uoms'
    paginate_by = 10

    # RBAC Mixin Settings
    module_name = 'units'
    required_permission = 'view'

    def get_queryset(self):

        query = self.request.GET.get('q')
        if query:
            return UnitOfMeasure.objects.filter(unit_name__icontains=query)
        return UnitOfMeasure.objects.all().order_by('uom_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Always include query in context so template {{ query }} works
        context['query'] = self.request.GET.get('q', '')
        return context

# Helper function
def stats():
    all_units = UnitOfMeasure.objects.all()
    return {
        'total': all_units.count(),
    }


# 2. AJAX Search View
class UnitOfMeasureSearchView(RBACPermissionMixin, ListView):
    model = UnitOfMeasure
    template_name = 'units/unit_list.html'
    context_object_name = 'uoms'
    paginate_by = 10

    # RBAC Mixin Settings
    module_name = 'units'
    required_permission = 'view'

    def get_queryset(self):
        queryset = UnitOfMeasure.objects.all()
        query = self.request.GET.get('q', '').strip()

        if query:
            queryset = queryset.filter(
                Q(unit_name__icontains=query) | Q(notation__icontains=query)
            )

        return queryset.order_by('unit_name')

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('format') == 'json':
            queryset = self.get_queryset()
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


# 3. Create View
class UnitOfMeasureCreateView(RBACPermissionMixin, SuccessMessageMixin, CreateView):
    model = UnitOfMeasure
    form_class = UnitOfMeasureForm
    template_name = 'units/unit_form.html'
    success_url = reverse_lazy('uom_list')
    success_message = "Unit of Measure '%(unit_name)s' was created successfully."

    # RBAC Mixin Settings
    module_name = 'units'
    required_permission = 'add'

    def form_invalid(self, form):
        print("=== FORM VALIDATION ERRORS ===")
        print(form.errors)
        print("==============================")
        return super().form_invalid(form)


# 4. Update View (Edit Details)
class UnitOfMeasureUpdateView(RBACPermissionMixin, SuccessMessageMixin, UpdateView):
    model = UnitOfMeasure
    form_class = UnitOfMeasureForm
    template_name = 'units/unit_form.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('uom_list')
    success_message = "Unit of Measure '%(unit_name)s' was updated successfully."

    # RBAC Mixin Settings
    module_name = 'units'
    required_permission = 'edit'


# 5. Toggle Status View (Active / Inactive)
class UnitOfMeasureToggleStatusView(RBACPermissionMixin, View):
    # RBAC Mixin Settings
    module_name = 'units'
    required_permission = 'edit'

    def post(self, request, pk):
        uom = get_object_or_404(UnitOfMeasure, pk=pk)
        uom.is_active = not uom.is_active
        uom.save()
        
        status_str = "activated" if uom.is_active else "deactivated"
        messages.success(request, f"Unit '{uom.unit_name}' has been {status_str}.")

        return redirect('uom_list')