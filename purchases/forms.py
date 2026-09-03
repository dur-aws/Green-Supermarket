from django import forms
from django.forms import inlineformset_factory

from products.models import ProductVariant
from .models import PurchaseOrder, PurchaseDetail, Supplier



class PurchaseOrderForm(forms.ModelForm):
    """Master form for Purchase Order header metadata and Tax/TDS calculations."""
    ORDER_STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('RECEIVED', 'Received'),
        ('CANCELLED', 'Cancelled'),
    ]

    PAYMENT_STATUS_CHOICES = [
        ('UNPAID', 'Unpaid'),
        ('PARTIAL', 'Partially Paid'),
        ('PAID', 'Paid'),
    ]

    order_status = forms.ChoiceField(
        choices=ORDER_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    payment_status = forms.ChoiceField(
        choices=PAYMENT_STATUS_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    class Meta:
        model = PurchaseOrder
        fields = [
            'supplier',
            'invoice_number',
            'order_date',
            'delivery_date',
            'received_date',
            
            'order_status',
            'payment_status',
            'subtotal',
            'vat_amount',
            'tds_rate',
            'tds_amount',
            'total_amount',
            'net_payable_amount',
        ]
        widgets = {
            'supplier': forms.Select(attrs={'class': 'form-select'}),
            'invoice_number': forms.TextInput(attrs={'class': 'form-control'}),
            'order_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'delivery_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'received_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            
            'order_status': forms.Select(attrs={'class': 'form-select'}),
            'payment_status': forms.Select(attrs={'class': 'form-select'}),
            'subtotal': forms.NumberInput(attrs={'class': 'form-control readonly-calc', 'readonly': 'readonly'}),
            'vat_amount': forms.NumberInput(attrs={'class': 'form-control readonly-calc', 'readonly': 'readonly'}),
            'tds_rate': forms.NumberInput(attrs={'class': 'form-control'}),
            'tds_amount': forms.NumberInput(attrs={'class': 'form-control readonly-calc', 'readonly': 'readonly'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control readonly-calc', 'readonly': 'readonly'}),
            'net_payable_amount': forms.NumberInput(attrs={'class': 'form-control readonly-calc', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active suppliers only
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=1)

class VariantChoiceField(forms.ModelChoiceField):
    def label_from_instance(self, obj):
        return f"{obj.product.product_name} - {obj.variant_name}"
class PurchaseDetailForm(forms.ModelForm):
    """Line-item form for purchase details (PO vs GRN variance handling)."""
    variant = VariantChoiceField(
        queryset=ProductVariant.objects.all(),
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    class Meta:
        model = PurchaseDetail
        fields = [
            'purchase_detail_id',
            'variant',
            'manufacture_date',
            'harvest_date',
            'ordered_quantity',
            'agreed_unit_price',
            'received_quantity',
            'actual_unit_price',
            'expiry_date',
            'subtotal',
        ]
        widgets = {
            'variant': forms.Select(attrs={'class': 'form-select variant-selector'}),
            'manufacture_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'harvest_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'ordered_quantity': forms.NumberInput(attrs={'class': 'form-control ordered-qty', 'step': '0.001'}),
            'agreed_unit_price': forms.NumberInput(attrs={'class': 'form-control agreed-price', 'step': '0.01'}),
            'received_quantity': forms.NumberInput(attrs={
                'class': 'form-control received-qty', 
                'step': '0.001', 
                'placeholder': 'Actual Received'
            }),
            'actual_unit_price': forms.NumberInput(attrs={
                'class': 'form-control actual-price', 
                'step': '0.01', 
                'placeholder': 'Actual Price'
            }),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'subtotal': forms.NumberInput(attrs={
                'class': 'form-control line-subtotal',
                'readonly': 'readonly'
            }),
        }


# ==========================================
# MASTER-DETAIL INLINE FORMSET
# ==========================================
PurchaseDetailFormSet = inlineformset_factory(
    PurchaseOrder,
    PurchaseDetail,
    form=PurchaseDetailForm,
    fk_name='purchase',
    extra=1,
    can_delete=True
)