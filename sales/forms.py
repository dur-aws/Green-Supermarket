from django import forms

from .models import InventoryReturnItem, SalesReturn, Sale


class SalesReturnForm(forms.Form):
    invoice_no = forms.CharField(max_length=50, label='Sales invoice')
    reason = forms.CharField(widget=forms.Textarea(attrs={'rows': 3}), required=False)

    def clean_invoice_no(self):
        invoice_no = self.cleaned_data['invoice_no'].strip()
        sale = Sale.objects.filter(invoice_no=invoice_no).first()
        if sale is None:
            raise forms.ValidationError('Sales invoice was not found.')
        if sale.sale_status == 'CANCELLED':
            raise forms.ValidationError('Cancelled invoices cannot be returned.')
        self.cleaned_data['sale'] = sale
        return invoice_no


class ReturnInspectionForm(forms.Form):
    def __init__(self, *args, rma=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.rma = rma
        for item in rma.items.select_related('sale_item__variant'):
            label = item.sale_item.variant.variant_name
            self.fields[f'quantity_{item.pk}'] = forms.DecimalField(
                label=f'{label} quantity received',
                min_value=0.001,
                max_value=item.quantity_requested,
                decimal_places=3,
                max_digits=10,
            )
            self.fields[f'condition_{item.pk}'] = forms.ChoiceField(
                label=f'{label} condition', choices=InventoryReturnItem.Condition.choices
            )
            self.fields[f'note_{item.pk}'] = forms.CharField(required=False, label=f'{label} inspection note')


class RefundForm(forms.Form):
    method = forms.ChoiceField(choices=(
        ('CASH_ON_HAND', 'Cash On Hand'),
        ('QR_ACCOUNT', 'QR Account'),
    ))
