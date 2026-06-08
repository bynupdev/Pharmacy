from django import forms
from django.utils import timezone
from .models import Drug, Batch, Supplier, StockAlert
from datetime import date

from django import forms
from .models import Drug

class DrugForm(forms.ModelForm):
    class Meta:
        model = Drug
        fields = ['name', 'generic_name', 'form', 'strength', 'manufacturer', 'requires_prescription']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Amoxicillin'
            }),
            'generic_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Amoxicillin'
            }),
            'form': forms.Select(attrs={
                'class': 'form-select'
            }),
            'strength': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 500mg'
            }),
            'manufacturer': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Pfizer (optional)'
            }),
            'requires_prescription': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        help_texts = {
            'manufacturer': 'Optional',
        }


class BatchForm(forms.ModelForm):
    class Meta:
        model = Batch
        fields = ['supplier', 'batch_number', 'quantity', 'purchase_price', 
                 'selling_price', 'manufacture_date', 'expiry_date']
        widgets = {
            'supplier': forms.Select(attrs={
                'class': 'form-select'
            }),
            'batch_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Batch/Lot Number'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'placeholder': 'Quantity'
            }),
            'purchase_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': 'Purchase Price'
            }),
            'selling_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 0,
                'step': '0.01',
                'placeholder': 'Selling Price'
            }),
            'manufacture_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
            'expiry_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        manufacture_date = cleaned_data.get('manufacture_date')
        expiry_date = cleaned_data.get('expiry_date')
        
        if manufacture_date and expiry_date:
            if expiry_date <= manufacture_date:
                raise forms.ValidationError("Expiry date must be after manufacture date")
            
            if expiry_date <= timezone.now().date():
                raise forms.ValidationError("Cannot add already expired batch")
        
        return cleaned_data
    
    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity < 0:
            raise forms.ValidationError("Quantity cannot be negative")
        return quantity
    
    def clean_prices(self):
        purchase_price = self.cleaned_data.get('purchase_price')
        selling_price = self.cleaned_data.get('selling_price')
        
        if purchase_price and selling_price and selling_price < purchase_price:
            raise forms.ValidationError("Selling price should be greater than purchase price")
        
        return self.cleaned_data

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = ['name', 'contact_person', 'email', 'phone', 'address']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Supplier Name'
            }),
            'contact_person': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Contact Person'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone Number'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Full Address'
            }),
        }
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and Supplier.objects.filter(email=email).exclude(pk=self.instance.pk).exists():
            raise forms.ValidationError("A supplier with this email already exists")
        return email

class StockAlertForm(forms.ModelForm):
    class Meta:
        model = StockAlert
        fields = ['alert_type', 'message', 'is_resolved']
        widgets = {
            'alert_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'message': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'readonly': True
            }),
            'is_resolved': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }

class BatchSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by drug name or batch number...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Batches'),
            ('active', 'Active'),
            ('expiring', 'Expiring Soon'),
            ('expired', 'Expired'),
            ('low_stock', 'Low Stock'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    supplier = forms.ModelChoiceField(
        required=False,
        queryset=Supplier.objects.all(),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

class InventoryAdjustmentForm(forms.Form):
    ADJUSTMENT_TYPES = [
        ('add', 'Add Stock'),
        ('remove', 'Remove Stock'),
        ('damage', 'Damaged Goods'),
        ('return', 'Customer Return'),
        ('correction', 'Inventory Correction'),
    ]
    
    adjustment_type = forms.ChoiceField(
        choices=ADJUSTMENT_TYPES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    quantity = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Quantity'
        })
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Reason for adjustment'
        })
    )