from django import forms
from .models import Customer, Membership

class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ['customer_code', 'customer_name', 'phone', 'email', 'address', 'status']
        widgets = {
            'customer_code': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. CUST-0001'}),
            'customer_name': forms.TextInput(attrs={'class': 'form-control'}),
            'phone': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'address': forms.TextInput(attrs={'class': 'form-control'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')
        if phone:
            qs = Customer.objects.filter(phone=phone)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError("This phone number is already registered to another customer.")
        return phone


class MembershipForm(forms.ModelForm):
    class Meta:
        model = Membership
        fields = ['membership_type', 'start_date', 'expiry_date', 'membership_fee', 'status']
        widgets = {
            'membership_type': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g. Gold, Silver'}),
            'start_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'expiry_date': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'membership_fee': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'status': forms.Select(attrs={'class': 'form-control'}),
        }