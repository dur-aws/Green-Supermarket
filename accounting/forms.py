from django import forms
import nepali_datetime
from .models import Account, FiscalYear, JournalEntry, JournalItem
from django.core.exceptions import ValidationError

class FiscalYearForm(forms.ModelForm):
    class Meta:
        model = FiscalYear
        fields = ['name', 'start_date_bs', 'end_date_bs', 'is_active', 'is_closed']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'start_date_bs': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}),
            'end_date_bs': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'YYYY-MM-DD'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_closed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    # def clean_start_date_bs(self):
    #     date_str = self.cleaned_data.get('start_date_bs')
    #     try:
    #         nepali_datetime.date.from_str(date_str)
    #     except Exception:
    #         raise ValidationError("Invalid Nepali date format. Use YYYY-MM-DD.")
    #     return date_str

    # def clean_end_date_bs(self):
    #     date_str = self.cleaned_data.get('end_date_bs')
    #     try:
    #         nepali_datetime.date.from_str(date_str)
    #     except Exception:
    #         raise ValidationError("Invalid Nepali date format. Use YYYY-MM-DD.")
    #     return date_str


class JournalEntryForm(forms.ModelForm):
    class Meta:
        model = JournalEntry
        fields = ['entry_date', 'bs_date', 'description', 'fiscal_year']
        widgets = {
            'entry_date': forms.DateInput(attrs={'type': 'date'}),
            'bs_date': forms.TextInput(attrs={'placeholder': 'YYYY-MM-DD'}),
            'description': forms.TextInput(),
        }


class JournalItemForm(forms.ModelForm):
    class Meta:
        model = JournalItem
        fields = ['account', 'debit', 'credit']
        widgets = {
            'account': forms.Select(),
            'debit': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
            'credit': forms.NumberInput(attrs={'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['account'].queryset = Account.objects.filter(is_active=True).order_by('account_code')

    def clean(self):
        cleaned = super().clean()
        debit = cleaned.get('debit') or 0
        credit = cleaned.get('credit') or 0
        if debit and credit:
            raise forms.ValidationError('A line can contain a debit or a credit, not both.')
        if not debit and not credit and not self.cleaned_data.get('DELETE'):
            raise forms.ValidationError('Enter a debit or credit amount.')
        return cleaned