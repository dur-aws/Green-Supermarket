from django import forms
from products.models import Product, Inventory


class StockInForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(status=1).order_by('product_name'),
        label="Product"
    )
    quantity = forms.IntegerField(min_value=1, label="Quantity Received")
    reason = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Purchase received, Stock correction'})
    )


class StockOutForm(forms.Form):
    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(status=1).order_by('product_name'),
        label="Product"
    )
    quantity = forms.IntegerField(min_value=1, label="Quantity Removed")
    reason = forms.CharField(
        max_length=255, required=False,
        widget=forms.TextInput(attrs={'placeholder': 'e.g. Damaged, Sample given, Sold offline'})
    )

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get('product')
        quantity = cleaned.get('quantity')
        if product and quantity:
            try:
                current_stock = product.inventory.quantity
            except Inventory.DoesNotExist:
                current_stock = 0
            if quantity > current_stock:
                self.add_error('quantity', f"Cannot remove {quantity} units — only {current_stock} in stock.")
        return cleaned


class StockAdjustmentForm(forms.Form):
    ADJUSTMENT_CHOICES = [
        ('increase', 'Increase Stock'),
        ('decrease', 'Decrease Stock'),
        ('set', 'Set Exact Quantity'),
    ]

    product = forms.ModelChoiceField(
        queryset=Product.objects.filter(status=1).order_by('product_name'),
        label="Product"
    )
    adjustment_type = forms.ChoiceField(choices=ADJUSTMENT_CHOICES, label="Adjustment Type")
    quantity = forms.IntegerField(min_value=0, label="Quantity")
    reason = forms.CharField(
        max_length=255, required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Reason for adjustment (required)'}),
        label="Reason"
    )

    def clean(self):
        cleaned = super().clean()
        product = cleaned.get('product')
        adj_type = cleaned.get('adjustment_type')
        quantity = cleaned.get('quantity')

        if product and adj_type == 'decrease' and quantity is not None:
            try:
                current_stock = product.inventory.quantity
            except Inventory.DoesNotExist:
                current_stock = 0
            if quantity > current_stock:
                self.add_error('quantity', f"Cannot decrease by {quantity} — only {current_stock} in stock.")
        return cleaned