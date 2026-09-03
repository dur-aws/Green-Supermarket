from django import forms
from django.contrib.auth import get_user_model
from django.db import transaction
from .models import Supplier
from accounts.models import Role

User = get_user_model()

class SupplierAdminForm(forms.ModelForm):
    # Optional fields to auto-create user login credentials for the supplier portal
    create_portal_account = forms.BooleanField(
        required=False,
        initial=False,
        label="Create Portal Login Account",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    username = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Portal Username'})
    )
    password = forms.CharField(
        required=False,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Portal Password'})
    )

    class Meta:
        model = Supplier
        fields = [
            'supplier_name',
            'contact_person',
            'email',
            'phone',
            'pan_vat_number',
            'is_organic_certified',
            'certification_details',
            'address'
        ]
        widgets = {
            'supplier_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'e.g., Organic Farms Pvt Ltd'}),
            'contact_person': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact Person Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'vendor@example.com'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+977-9800000000'}),
            'pan_vat_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PAN / VAT Number'}),
            'is_organic_certified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'certification_details': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Cert # / Standards'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full Address'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        create_account = cleaned_data.get('create_portal_account')
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        has_linked_user = bool(
            self.instance.user_id and User.objects.filter(pk=self.instance.user_id).exists()
        )

        if create_account and not has_linked_user:
            if not username:
                self.add_error('username', 'Username is required to create a portal account.')
            if not password:
                self.add_error('password', 'Password is required to create a portal account.')
            if username and User.objects.filter(username=username).exists():
                self.add_error('username', 'This username is already taken.')

        return cleaned_data

    @transaction.atomic
    def save(self, commit=True):
        supplier = super().save(commit=False)
        create_account = self.cleaned_data.get('create_portal_account')
        username = self.cleaned_data.get('username')
        password = self.cleaned_data.get('password')
        has_linked_user = bool(
            supplier.user_id and User.objects.filter(pk=supplier.user_id).exists()
        )

        # Create linked User account if checked and missing
        if create_account and not has_linked_user and username and password:
            supplier_role, _ = Role.objects.get_or_create(role_name=Role.SUPPLIER)
            user = User.objects.create_user(
                username=username,
                email=supplier.email,
                phone = supplier.phone,
                password=password,
                role_name=supplier_role,
                status=1,
                is_active=True,
                is_staff=False,
                is_superuser=False,
            )
            
            supplier.user = user

        if commit:
            supplier.save()
        return supplier