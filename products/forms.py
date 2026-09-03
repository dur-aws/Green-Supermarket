from django import forms
from django.forms import inlineformset_factory
from decimal import Decimal

from products.utils import generate_barcode, generate_sku
from .models import Product, ProductVariant, Category, UnitOfMeasure
from django.core.validators import RegexValidator

class ProductForm(forms.ModelForm):
    
    class Meta:
        model = Product
        fields = [
            'category',
            'brand',
            'product_name',
            'is_organic',
            'is_eco_friendly',
            'shelf_life_days',
            'status',
        ]
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select select2'}),
            'brand': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Local Farm, Fresh Agro'}),
            'product_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Potato (आलु)'}),
            'is_organic': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_eco_friendly': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'shelf_life_days': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'e.g., 7'}),
            'status': forms.CheckboxInput(attrs={'class': 'form-check-input', 'role': 'switch'}),
        }
sku_validator = RegexValidator(
regex=r'^PD\d{5}$',
message="SKU must be in the format PD followed by 5 digits, e.g. PD00001."
)
barcode_validator = RegexValidator(
regex=r'^\d{9}$',
    message="Barcode must be exactly 9 digits."
        )
class ProductVariantForm(forms.ModelForm):
    """Form for individual Product Variants (SKU, UOM, PriciFng, & Stock limits)."""
    class Meta:
        model = ProductVariant
        fields = [
            'variant_name',
            'sku',
            'barcode',
            'primary_uom',
            'secondary_uom',
            'cost_price',
            'selling_price',
            'is_vatable',
            'reorder_level',
            'target_stock_level',
            'abc_class',
            'is_catch_weight',
            'is_active',
        ]
        widgets = {
            'variant_name': forms.TextInput(attrs={'class': 'form-control' }),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Barcode/EAN'}),
            'primary_uom': forms.Select(attrs={'class': 'form-select'}),
            'secondary_uom': forms.Select(attrs={'class': 'form-select'}),
            'cost_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'is_vatable': forms.CheckboxInput(attrs={'class': 'form-check-input is-vatable-checkbox'}),
            'reorder_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'target_stock_level': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'}),
            'abc_class': forms.Select(attrs={'class': 'form-select'}),
            'is_catch_weight': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['sku'].validators.append(sku_validator)
        self.fields['barcode'].validators.append(barcode_validator)

        # DISABLED (not just readonly): Django completely ignores whatever
        # value the browser submits for a disabled field, and instead uses
        # self.initial at save time. This makes the server the single
        # source of truth for sku/barcode, no matter what happens client-side.
        self.fields['sku'].disabled = True
        self.fields['barcode'].disabled = True

        if self.instance.pk:
            # Existing variant: initial already comes from the real DB row
            # (Django populates this automatically from the instance), so
            # the disabled field always resolves back to its own true value.
            # This is what makes self-exclusion irrelevant — the value can
            # never appear "changed" or collide with itself.
            pass
        else:
            # Brand-new variant (no pk yet), whether this is the initial
            # page-load empty row or a row added via "+ Add Variant":
            # always hand it a guaranteed-fresh code, generated right now,
            # ignoring anything the client may have shown/sent.
            new_sku = generate_sku()
            new_barcode = generate_barcode()
            self.initial['sku'] = new_sku
            self.initial['barcode'] = new_barcode

    def clean_sku(self):
        # With sku disabled, cleaned_data['sku'] already equals self.initial['sku'].
        # This exclusion is kept as a defense-in-depth safety net only.
        sku = self.cleaned_data.get('sku')
        qs = ProductVariant.objects.filter(sku=sku)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This SKU already exists.")
        return sku

    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')
        qs = ProductVariant.objects.filter(barcode=barcode)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("This barcode already exists.")
        return barcode




# Formset for handling Multiple Variants inside one Product Form
ProductVariantFormSet = inlineformset_factory(
    Product,
    ProductVariant,
    form=ProductVariantForm,
    fk_name='product',
    extra=1,
    can_delete=True
)