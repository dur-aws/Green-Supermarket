from django import forms
from .models import Category

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = [
            'category_name', 
            'parent', 
            'requires_expiry_tracking', 
            'requires_batch_tracking', 
            'requires_catch_weight'
        ]
        widgets = {
            'category_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Dairy, Fresh Produce'}),
            'parent': forms.Select(attrs={'class': 'form-select'}),
            'requires_expiry_tracking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_batch_tracking': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'requires_catch_weight': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Prevent selecting itself as a parent category when updating
        if self.instance and self.instance.pk:
            self.fields['parent'].queryset = Category.objects.exclude(pk=self.instance.pk)