from django import forms
import nepali_datetime

from accounting.models import FiscalYear
from .models import Expense


class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = [
            'expense_date', 'bs_date', 'expense_type', 'amount',
            'payment_account_code', 'description', 'reference_number', 'fiscal_year',
        ]
        widgets = {
            'expense_date': forms.DateInput(attrs={'type': 'date', 'class': 'form-control'}),
            'bs_date': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}),
            'expense_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'min': '0.01', 'step': '0.01'}),
            'payment_account_code': forms.Select(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'What was this expense for?'}),
            'reference_number': forms.TextInput(attrs={'class': 'form-control'}),
            'fiscal_year': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['fiscal_year'].queryset = FiscalYear.objects.order_by('-start_date_bs')
        self.fields['fiscal_year'].empty_label = 'Select fiscal year'

    def clean_bs_date(self):
        value = self.cleaned_data['bs_date'].strip()
        parts = value.split('-')
        if len(parts) != 3 or any(not part.isdigit() for part in parts):
            raise forms.ValidationError('Use a valid Nepali date in YYYY-MM-DD format.')
        try:
            parsed = nepali_datetime.date(*(int(part) for part in parts))
        except (TypeError, ValueError):
            raise forms.ValidationError('Enter a valid Nepali date in YYYY-MM-DD format.')
        return value

    def clean(self):
        cleaned_data = super().clean()
        bs_date = cleaned_data.get('bs_date')
        fiscal_year = cleaned_data.get('fiscal_year')
        if bs_date and fiscal_year and not (
            fiscal_year.start_date_bs <= bs_date <= fiscal_year.end_date_bs
        ):
            self.add_error('bs_date', 'The B.S. date must be inside the selected Fiscal Year.')
        return cleaned_data
