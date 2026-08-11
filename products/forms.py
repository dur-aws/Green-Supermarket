from django import forms
from .models import Product, Category, Unit, Inventory

class ProductForm(forms.ModelForm):
    initial_stock = forms.IntegerField(
        required=False, 
        initial=0, 
        min_value=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'})
    )
    reorder_level = forms.IntegerField(
        required=False, 
        initial=0, 
        min_value=0, 
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0'})
    )

    class Meta:
        model = Product
        fields = [
            'product_name', 'category', 'brand', 'unit', 
            'barcode', 'purchase_price', 'selling_price', 
            'vat_percent', 'expiry_date', 'status'
        ]
        widgets = {
            'product_name': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-select'}),
            'brand': forms.TextInput(attrs={'class': 'form-control'}),
            'unit': forms.Select(attrs={'class': 'form-select'}),
            'barcode': forms.TextInput(attrs={'class': 'form-control'}),
            'purchase_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'selling_price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'vat_percent': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'status': forms.Select(choices=[(1, 'Active'), (0, 'Disabled')], attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            try:
                inv = self.instance.inventory
                self.fields['initial_stock'].initial = inv.quantity
                self.fields['reorder_level'].initial = inv.reorder_level
            except Inventory.DoesNotExist:
                pass

    def save(self, commit=True):
        product = super().save(commit=commit)
        if commit:
            quantity = self.cleaned_data.get('initial_stock') or 0
            reorder = self.cleaned_data.get('reorder_level') or 0
            Inventory.objects.update_or_create(
                product=product,
                defaults={'quantity': quantity, 'reorder_level': reorder}
            )
        return product