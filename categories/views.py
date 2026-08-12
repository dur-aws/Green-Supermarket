from django.urls import reverse_lazy
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, View
from .models import Category
from .forms import CategoryForm
from django.shortcuts import get_object_or_404, redirect
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.db.models import Q

class CategoryListView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

    def get_queryset(self):
        query = self.request.GET.get('q')
        if query:
            return Category.objects.filter(category_name__icontains=query)
        return Category.objects.all().order_by('category_id')

def stats():
    all_categories = Category.objects.select_related('category')
    return {
        'total': all_categories.count(),
    }


class CategorySearchView(LoginRequiredMixin, ListView):
    model = Category
    template_name = 'categories/category_list.html'
    context_object_name = 'categories'
    paginate_by = 10

    def get_queryset(self):
        queryset = Category.objects.select_related('parent').all()
        query = self.request.GET.get('q', '').strip()

        if query:
            queryset = queryset.filter(
                Q(category_name__icontains=query) | Q(parent__category_name__icontains=query)
            )

        return queryset.order_by('category_name')

    def render_to_response(self, context, **response_kwargs):
        if self.request.headers.get('x-requested-with') == 'XMLHttpRequest' or self.request.GET.get('format') == 'json':
            queryset = self.get_queryset()
            rows_html = render_to_string(
                'categories/partials/_category_table_rows.html', 
                {'categories': queryset}, 
                request=self.request
            )
            return JsonResponse({
                'rows_html': rows_html,
                'showing_count': queryset.count(),
            })

        return super().render_to_response(context, **response_kwargs)


class CategoryCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    success_url = reverse_lazy('category_list')
    permission_required = "categories.change_category"
    success_message = "Category '%(category_name)s' was created successfully."
    
    def form_invalid(self, form):
        print("=== FORM VALIDATION ERRORS ===")
        print(form.errors)
        print("==============================")
        return super().form_invalid(form)

class CategoryUpdateView(LoginRequiredMixin, PermissionRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'categories/category_form.html'
    pk_url_kwarg = 'pk'
    success_url = reverse_lazy('category_list')
    permission_required = 'categories.change_category'
    success_message = "Category '%(category_name)s' was updated successfully."

class CategoryDeleteView(LoginRequiredMixin, PermissionRequiredMixin, View):
    permission_required = 'categories.delete_category'

    def get(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.is_active = False 
        category.save()
        messages.success(request, f"Cateogry '{category.category_name}' has been deactivated.")
        return redirect('cateogry_list')