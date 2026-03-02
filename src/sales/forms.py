from django import forms
from django.utils import timezone
from .models import Sale, SaleItem, Receipt
from inventory.models import Batch
from prescriptions.models import Prescription

class SaleForm(forms.ModelForm):
    class Meta:
        model = Sale
        fields = ['prescription', 'payment_method', 'payment_reference', 'discount', 'tax']
        widgets = {
            'prescription': forms.Select(attrs={
                'class': 'form-select'
            }),
            'payment_method': forms.Select(attrs={
                'class': 'form-select',
                'id': 'payment-method'
            }),
            'payment_reference': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Reference/Transaction ID'
            }),
            'discount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0,
                'value': 0,
                'id': 'discount-input'
            }),
            'tax': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': 0,
                'value': 0,
                'id': 'tax-input'
            }),
        }
    
    def clean_payment_reference(self):
        payment_method = self.cleaned_data.get('payment_method')
        payment_reference = self.cleaned_data.get('payment_reference')
        
        if payment_method != 'cash' and not payment_reference:
            raise forms.ValidationError("Payment reference is required for non-cash payments")
        
        return payment_reference

class SaleItemForm(forms.ModelForm):
    batch = forms.ModelChoiceField(
        queryset=Batch.objects.filter(
            quantity__gt=0,
            expiry_date__gt=timezone.now().date()
        ).select_related('drug'),
        widget=forms.Select(attrs={
            'class': 'form-select batch-select',
            'required': True
        })
    )
    
    class Meta:
        model = SaleItem
        fields = ['batch', 'quantity']
        widgets = {
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control quantity-input',
                'min': 1,
                'required': True
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        batch = cleaned_data.get('batch')
        quantity = cleaned_data.get('quantity')
        
        if batch and quantity:
            if quantity > batch.quantity:
                raise forms.ValidationError(
                    f"Only {batch.quantity} units available in stock"
                )
            
            # Auto-calculate prices
            unit_price = batch.selling_price
            total_price = quantity * unit_price
            
            cleaned_data['unit_price'] = unit_price
            cleaned_data['total_price'] = total_price
        
        return cleaned_data

class SaleItemFormSet(forms.BaseFormSet):
    def clean(self):
        """Check stock availability and prevent duplicates"""
        if any(self.errors):
            return
        
        batches = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                batch = form.cleaned_data.get('batch')
                quantity = form.cleaned_data.get('quantity')
                
                if batch in batches:
                    raise forms.ValidationError(
                        f"Duplicate item: {batch.drug.name}. Please combine quantities."
                    )
                batches.append(batch)
                
                # Double-check stock availability
                if quantity > batch.quantity:
                    raise forms.ValidationError(
                        f"Insufficient stock for {batch.drug.name}. Available: {batch.quantity}"
                    )

class PaymentForm(forms.Form):
    PAYMENT_METHODS = Sale.PAYMENT_METHODS
    
    amount_tendered = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'min': 0,
            'id': 'amount-tendered'
        })
    )
    payment_method = forms.ChoiceField(
        choices=PAYMENT_METHODS,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'payment-method'
        })
    )
    payment_reference = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Reference Number (for card/insurance)'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        amount_tendered = cleaned_data.get('amount_tendered')
        total = self.initial.get('total', 0)
        
        if amount_tendered and amount_tendered < total:
            raise forms.ValidationError(f"Amount tendered must be at least ${total}")
        
        return cleaned_data
    
    def calculate_change(self, total):
        amount_tendered = self.cleaned_data.get('amount_tendered', 0)
        return amount_tendered - total

class ReceiptForm(forms.ModelForm):
    class Meta:
        model = Receipt
        fields = ['sale']
        widgets = {
            'sale': forms.HiddenInput()
        }

class RefundForm(forms.Form):
    REFUND_REASONS = [
        ('damaged', 'Damaged Product'),
        ('wrong_item', 'Wrong Item Dispensed'),
        ('expired', 'Product Expired'),
        ('patient_refused', 'Patient Refused Medication'),
        ('doctor_change', 'Doctor Changed Prescription'),
        ('other', 'Other Reason'),
    ]
    
    items = forms.MultipleChoiceField(
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        label="Select items to refund"
    )
    reason = forms.ChoiceField(
        choices=REFUND_REASONS,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    reason_details = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional details (required for "Other" reason)'
        })
    )
    authorized_by = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Manager/Pharmacist Name'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        reason = cleaned_data.get('reason')
        reason_details = cleaned_data.get('reason_details')
        
        if reason == 'other' and not reason_details:
            raise forms.ValidationError("Please provide details for 'Other' reason")
        
        return cleaned_data

class DailyCloseForm(forms.Form):
    cash_on_hand = forms.DecimalField(
        min_value=0,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'step': '0.01',
            'placeholder': 'Actual cash in register'
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Any discrepancies or notes'
        })
    )
    
    def clean_cash_on_hand(self):
        cash = self.cleaned_data.get('cash_on_hand')
        expected_cash = self.initial.get('expected_cash', 0)
        
        if abs(cash - expected_cash) > 10:  # Tolerance of $10
            raise forms.ValidationError(
                f"Large discrepancy detected. Expected: ${expected_cash:.2f}"
            )
        
        return cash