from django.db import IntegrityError, transaction
from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy
from django.contrib import messages
from django.db.models import Q, F, Count, ProtectedError, Sum, DecimalField, Value
from django.template.loader import render_to_string
from django.http import JsonResponse
from django.views import View
from django.views.generic import ListView, CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from accounts.mixins import RBACPermissionMixin
from django.contrib.auth.decorators import login_required
from .models import Product, ProductVariant, Category, UnitOfMeasure
from .forms import ProductForm, ProductVariantForm, ProductVariantFormSet

from decimal import Decimal
from django.db.models.functions import Coalesce
from django.utils import timezone

from .utils import generate_sku, generate_barcode

@login_required
def generate_variant_codes(request):
    exclude_skus = [s for s in request.GET.get('exclude_skus', '').split(',') if s]
    exclude_barcodes = [b for b in request.GET.get('exclude_barcodes', '').split(',') if b]
    return JsonResponse({
        'sku': generate_sku(exclude=exclude_skus),
        'barcode': generate_barcode(exclude=exclude_barcodes),
    })


class ProductFilterMixin:
 
    def get_filtered_queryset(self):
        today = timezone.now().date()

        # 1. Annotate total unexpired active batch stock per variant
        queryset = ProductVariant.objects.annotate(
            calculated_stock=Coalesce(
                Sum(
                    'batches__current_quantity',
                    filter=Q(
                        batches__batch_status='ACTIVE',
                        batches__expiry_date__gte=today,
                        batches__current_quantity__gt=0
                    )
                ),
                Value(Decimal('0.000')),
                output_field=DecimalField()
            )
        )

        query = self.request.GET.get('q', '').strip()
        category_id = self.request.GET.get('category', '')
        stock_status = self.request.GET.get('stock_status', '').strip()

        # 2. Search Logic
        if query:
            search_conditions = (
                Q(product__product_name__icontains=query) |
                Q(variant_name__icontains=query) |
                Q(sku__icontains=query) |
                Q(product__brand__icontains=query)
            )

            # Extract numeric ID for code searches (e.g., P-001)
            cleaned_query = query.upper().replace('P-', '').replace('P', '').strip()
            if cleaned_query.isdigit():
                search_conditions |= Q(product__product_id=int(cleaned_query))

            queryset = queryset.filter(search_conditions).distinct()

        # 3. Category Filter
        if category_id:
            queryset = queryset.filter(product__category_id=category_id)

        # 4. Stock Status Filter (Using product__status)
        if stock_status == 'disable':
            queryset = queryset.filter(product__status=False)
        elif stock_status == 'out-of-stock':
            queryset = queryset.filter(
                product__status=True, 
                calculated_stock__lte=0
            )
        elif stock_status == 'low-stock':
            queryset = queryset.filter(
                product__status=True, 
                calculated_stock__gt=0, 
                calculated_stock__lte=models.F('reorder_level')
            )
        elif stock_status == 'active':
            queryset = queryset.filter(
                product__status=True, 
                calculated_stock__gt=models.F('reorder_level')
            )

        return queryset, query, category_id, stock_status
    def get_stats(self):
        """
        Calculates catalog statistics in a single aggregated DB query.
        Calculates stats on the base search/category filter (ignoring the stock_status filter).
        """
        today = timezone.now().date()

        # Base queryset with calculated stock for stats
        base_qs = ProductVariant.objects.annotate(
            calculated_stock=Coalesce(
                Sum(
                    'batches__current_quantity',
                    filter=Q(
                        batches__batch_status='ACTIVE',
                        batches__expiry_date__gte=today,
                        batches__current_quantity__gt=0
                    )
                ),
                Value(Decimal('0.000')),
                output_field=DecimalField()
            )
        )

        # Apply search and category filters if present
        query = self.request.GET.get('q', '').strip()
        category_id = self.request.GET.get('category', '')

        if query:
            search_conditions = (
                Q(product__product_name__icontains=query) |
                Q(variant_name__icontains=query) |
                Q(sku__icontains=query) |
                Q(product__brand__icontains=query)
            )
            cleaned_query = query.upper().replace('P-', '').replace('P', '').strip()
            if cleaned_query.isdigit():
                search_conditions |= Q(product__product_id=int(cleaned_query))
            base_qs = base_qs.filter(search_conditions).distinct()

        if category_id:
            base_qs = base_qs.filter(product__category_id=category_id)
        # Force checking both fields directly in aggregate expressions
        active_cond = Q(is_active=True) & Q(product__status=True)
        disabled_cond = Q(is_active=False) | Q(product__status=False)
        # Execute single aggregation pass
        stats = base_qs.aggregate(
            total=Count('variant_id'),
            active=Count(
                'variant_id',
                filter=active_cond & Q(
                    product__status=True, 
                    calculated_stock__gt=models.F('reorder_level')
                )
            ),
            low_stock=Count(
                'variant_id',
                filter=active_cond & Q(
                    product__status=True, 
                    calculated_stock__gt=0, 
                    calculated_stock__lte=models.F('reorder_level')
                )
            ),
            out_of_stock=Count(
                'variant_id',
                filter=active_cond & Q(
                    product__status=True, 
                    calculated_stock__lte=0
                )
            ),
            disabled=Count(
                'variant_id',
                filter=disabled_cond &Q(product__status=False)
            )
        )

        return stats
    

class ProductListView(RBACPermissionMixin, LoginRequiredMixin, ProductFilterMixin, ListView):
    """Initial Full Page Load for Products Catalog."""
    model = ProductVariant
    template_name = 'products/product_list.html'
    context_object_name = 'products'
    paginate_by = 100

    module_name = 'products'
    required_permission = 'view'

    def get_queryset(self):
        queryset, _, _, _ = self.get_filtered_queryset()
        # Attach prefetch_related to the filtered queryset to optimize FEFO property lookups
        return queryset.prefetch_related('batches').order_by('product_id')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        _, query, category_id, stock_status = self.get_filtered_queryset()
        
        context['categories'] = Category.objects.all()
        context['query'] = query
        context['selected_category'] = category_id
        context['selected_stock_status'] = stock_status
        
        # Avoid running full count query twice; use the paginator's count
        context['total_filtered'] = self.object_list.count() if hasattr(self, 'object_list') else self.get_queryset().count()
        context['stats'] = self.get_stats()

        return context



class ProductSearchView(RBACPermissionMixin, LoginRequiredMixin, ProductFilterMixin, View):
    """AJAX endpoint for Live Product Filtering."""
    module_name = 'products'
    required_permission = 'view'

    def get(self, request, *args, **kwargs):
        try:
            queryset, _, _, _ = self.get_filtered_queryset()
            total_filtered = queryset.count()
            products_page = queryset[:100]

            rows_html = render_to_string(
                'products/product_rows.html',
                {'products': products_page},
                request=request
            )

            return JsonResponse({
                'rows_html': rows_html,
                'total_filtered': total_filtered,
                'showing_count': min(total_filtered, 100),
            })
        except Exception as e:
            return JsonResponse({
                'rows_html': f'<tr><td colspan="10" class="text-center text-danger">Error filtering products: {str(e)}</td></tr>',
                'total_filtered': 0,
                'showing_count': 0
            }, status=400)


class ProductCreateView(RBACPermissionMixin, LoginRequiredMixin, CreateView):
    """Create Product Master + one or more Variants in a single transaction."""
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('product_list')

    module_name = 'products'
    required_permission = 'add'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if self.request.POST:
            context['variant_formset'] = ProductVariantFormSet(self.request.POST)
        else:
            context['variant_formset'] = ProductVariantFormSet()
        context['title'] = 'Add New Product & Variants'
        return context

    def form_valid(self, form):
        context = self.get_context_data()
        formset = context['variant_formset']

        if formset.is_valid():
            with transaction.atomic():
                self.object = form.save()
                formset.instance = self.object
                formset.save()
            messages.success(
                self.request,
                f'Product "{self.object.product_name}" and its variants were created successfully.'
            )
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, 'Please correct the errors in the variant(s) below.')
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors in the product form.')
        return self.render_to_response(self.get_context_data(form=form))


class ProductUpdateView(RBACPermissionMixin, LoginRequiredMixin, UpdateView):
    """Edit existing Product Details + its Variants."""
    model = Product
    form_class = ProductForm
    template_name = 'products/product_form.html'
    success_url = reverse_lazy('product_list')

    module_name = 'products'
    required_permission = 'edit'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Reuse the form already built by get_form()/kwargs whenever it's
        # available instead of silently constructing a second, separate
        # ProductForm instance every time this method runs.
        if 'form' not in kwargs:
            kwargs['form'] = context.get('form') or self.get_form()

        if self.request.method == 'POST':
            context['variant_formset'] = ProductVariantFormSet(
                self.request.POST, instance=self.object
            )
        else:
            context['variant_formset'] = ProductVariantFormSet(instance=self.object)

        context['title'] = 'Edit Product'
        return context

    def form_valid(self, form):
        context = self.get_context_data(form=form)
        formset = context['variant_formset']

        if formset.is_valid():
        
            try:
                with transaction.atomic():
                    self.object = form.save()
                    formset.instance = self.object
                    formset.save()
            except IntegrityError:
                # Safety net for a genuine race condition (two people saving
                # at the same instant) — everyday duplicate SKU/barcode
                # entry is already caught earlier by formset.is_valid().
                messages.error(
                    self.request,
                    'That SKU or barcode was just taken by another save. Please refresh and try again.'
                )
                return self.render_to_response(self.get_context_data(form=form))

            messages.success(
                self.request,
                f'Product "{self.object.product_name}" and its variants were updated successfully.'
            )
            return redirect(self.get_success_url())
        else:
            messages.error(self.request, 'Please correct the errors in the variant(s) below.')
            return self.render_to_response(self.get_context_data(form=form))

    def form_invalid(self, form):
        messages.error(self.request, 'Please correct the errors in the product form.')
        return self.render_to_response(self.get_context_data(form=form))
class ProductToggleStatusView(RBACPermissionMixin, LoginRequiredMixin, View):
    """Soft Delete / Toggle Active Status without destroying Sales history."""
    module_name = 'products'
    required_permission = 'edit'

    def post(self, request, pk, *args, **kwargs):
        variant = get_object_or_404(ProductVariant, pk=pk)
        variant.is_active = not variant.is_active
        variant.save()

        status_str = "activated" if variant.is_active else "deactivated"
        messages.success(request, f'Product variant "{variant}" has been {status_str}.')
        return redirect('product_list')