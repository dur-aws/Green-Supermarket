from decimal import Decimal

from django import forms
from django.forms import inlineformset_factory

from products.models import ProductVariant
from .models import PurchaseOrder, PurchaseDetail, Supplier
from payments.choices import PAYMENT_METHOD_CHOICES

from django.core.exceptions import ValidationError

class PurchaseOrderForm(forms.ModelForm):
    """Master form for Purchase Order header metadata and Tax/TDS calculations."""
    ORDER_STATUS_CHOICES = PurchaseOrder.ORDER_STATUS_CHOICES

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
            'freight_charge',
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
            'freight_charge': forms.NumberInput(attrs={'class': 'form-control', 'min': '0', 'step': '0.01'}),
            'total_amount': forms.NumberInput(attrs={'class': 'form-control readonly-calc', 'readonly': 'readonly'}),
            'net_payable_amount': forms.NumberInput(attrs={'class': 'form-control readonly-calc', 'readonly': 'readonly'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active suppliers only
        self.fields['supplier'].queryset = Supplier.objects.filter(is_active=1)
        # These values are recalculated from line items on the server.
        for field_name in ('subtotal', 'vat_amount', 'tds_amount', 'total_amount', 'net_payable_amount'):
            self.fields[field_name].required = False

    def clean(self):
            cleaned_data = super().clean()
            order_date = cleaned_data.get('order_date')
            received_date = cleaned_data.get('received_date')

            if received_date and order_date and received_date < order_date:
                        self.add_error('received_date', "Received date cannot be earlier than Order date.")
            return cleaned_data
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
            'batch_no',
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
            'batch_no': forms.TextInput(attrs={'class': 'form-control'}),
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




    def clean(self):
        cleaned_data = super().clean()
        
        manufacture_date = cleaned_data.get('manufacture_date')
        expiry_date = cleaned_data.get('expiry_date')
        harvest_date = cleaned_data.get('harvest_date')

        
        if expiry_date and manufacture_date and harvest_date and (expiry_date <= manufacture_date or expiry_date <= harvest_date):
            self.add_error('expiry_date', "Expiry date must be greater than Manufacturing/Harvest date.")

        return cleaned_data

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


class PurchaseReturnForm(forms.Form):
    quantity = forms.DecimalField(
        min_value=Decimal('0.001'), max_digits=10, decimal_places=3,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    reason = forms.CharField(
        max_length=255, initial='Supplier return',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def __init__(self, *args, batch=None, existing_return=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch = batch
        self.existing_return = existing_return

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.batch and self.batch.current_quantity <= Decimal('0.000'):
            raise forms.ValidationError('This batch has no active stock available for return.')
        available_quantity = self.batch.current_quantity if self.batch else Decimal('0.000')
        if self.existing_return:
            available_quantity += self.existing_return.quantity
        if self.batch and quantity > available_quantity:
            raise forms.ValidationError(
                f'Return quantity cannot exceed available stock ({available_quantity}).'
            )
        return quantity


class PurchasePaymentForm(forms.Form):
    amount = forms.DecimalField(
        min_value=Decimal('0.01'), max_digits=12, decimal_places=2,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'})
    )
    payment_method = forms.ChoiceField(
        choices=[choice for choice in PAYMENT_METHOD_CHOICES if choice[0] != 'CREDIT'],
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    reference = forms.CharField(required=False, max_length=150)

    def __init__(self, *args, purchase=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.purchase = purchase

    def clean_amount(self):
        amount = self.cleaned_data['amount']
        if self.purchase and amount > self.purchase.due_amount:
            raise forms.ValidationError(
                f'Payment cannot exceed the due amount ({self.purchase.due_amount}).'
            )
        return amount