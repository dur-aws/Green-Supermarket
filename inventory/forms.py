from django import forms
from .models import StockAdjustment

class StockAdjustmentForm(forms.ModelForm):
    class Meta:
        model = StockAdjustment
        fields = ['reason_code', 'quantity_change', 'notes']
        widgets = {
            'reason_code': forms.Select(attrs={'class': 'form-select'}),
            'quantity_change': forms.NumberInput(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean_quantity_change(self):
        qty = self.cleaned_data.get('quantity_change')
        if qty == 0:
            raise forms.ValidationError("Adjustment quantity cannot be zero.")
        return qty

# class StockInForm(forms.Form):
#     product = forms.ModelChoiceField(
#         queryset=Product.objects.filter(status=1).order_by('product_name'),
#         label="Product"
#     )
#     quantity = forms.IntegerField(min_value=1, label="Quantity Received")
#     reason = forms.CharField(
#         max_length=255, required=False,
#         widget=forms.TextInput(attrs={'placeholder': 'e.g. Purchase received, Stock correction'})
#     )


# class StockOutForm(forms.Form):
#     product = forms.ModelChoiceField(
#         queryset=Product.objects.filter(status=1).order_by('product_name'),
#         label="Product"
#     )
#     quantity = forms.IntegerField(min_value=1, label="Quantity Removed")
#     reason = forms.CharField(
#         max_length=255, required=False,
#         widget=forms.TextInput(attrs={'placeholder': 'e.g. Damaged, Sample given, Sold offline'})
#     )

#     def clean(self):
#         cleaned = super().clean()
#         product = cleaned.get('product')
#         quantity = cleaned.get('quantity')
#         if product and quantity:
#             try:
#                 current_stock = product.inventory_batch.quantity
#             except Inventory.DoesNotExist:
#                 current_stock = 0
#             if quantity > current_stock:
#                 self.add_error('quantity', f"Cannot remove {quantity} units — only {current_stock} in stock.")
#         return cleaned

