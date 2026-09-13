from django import forms
import nepali_datetime
from .models import FiscalYear
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