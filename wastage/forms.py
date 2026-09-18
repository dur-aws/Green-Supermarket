from decimal import Decimal

from django import forms


class WastageForm(forms.Form):
    quantity = forms.DecimalField(
        min_value=Decimal('0.001'), max_digits=10, decimal_places=3,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'step': '0.001'})
    )
    reason = forms.ChoiceField(
        choices=(
            ('EXPIRED', 'Expired'),
            ('DAMAGED', 'Damaged / Broken'),
            ('SPOILED', 'Spoiled / Quality Failure'),
            ('THEFT', 'Stolen / Missing'),
            ('OTHER', 'Other'),
        ),
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )

    def __init__(self, *args, batch=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.batch = batch

    def clean_quantity(self):
        quantity = self.cleaned_data['quantity']
        if self.batch and quantity > self.batch.current_quantity:
            raise forms.ValidationError(
                f"Wastage cannot exceed available stock ({self.batch.current_quantity})."
            )
        return quantity