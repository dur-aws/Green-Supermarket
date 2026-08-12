from django import forms
from .models import UnitOfMeasure

class UnitOfMeasureForm(forms.ModelForm):
    class Meta:
        model = UnitOfMeasure
        fields = ['unit_name', 'notation', 'is_weight_based']
        widgets = {
            'unit_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Kilogram'}),
            'notation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. kg'}),
            'is_weight_based': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_unit_name(self):
        unit_name = self.cleaned_data.get('unit_name')
        if unit_name:
            unit_name = unit_name.strip()
            # Check for case-insensitive duplicate if creating a new instance
            if not self.instance.pk and UnitOfMeasure.objects.filter(unit_name__iexact=unit_name).exists():
                raise forms.ValidationError(f"A unit named '{unit_name}' already exists.")
        return unit_name