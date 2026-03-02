from django import forms
from django.utils import timezone
from .models import Prescription, PrescriptionItem, InteractionLog
from patients.models import Patient
from inventory.models import Drug

class PrescriptionForm(forms.ModelForm):
    class Meta:
        model = Prescription
        fields = ['patient', 'prescribed_by', 'prescribed_date', 'notes']
        widgets = {
            'patient': forms.Select(attrs={
                'class': 'form-select',
                'id': 'patient-select'
            }),
            'prescribed_by': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': "Doctor's Name"
            }),
            'prescribed_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': timezone.now().date().isoformat()
            }),
            'notes': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Additional notes or instructions'
            }),
        }
    
    def clean_prescribed_date(self):
        prescribed_date = self.cleaned_data.get('prescribed_date')
        if prescribed_date and prescribed_date > timezone.now().date():
            raise forms.ValidationError("Prescription date cannot be in the future")
        return prescribed_date

class PrescriptionItemForm(forms.ModelForm):
    drug = forms.ModelChoiceField(
        queryset=Drug.objects.all().order_by('name'),
        widget=forms.Select(attrs={
            'class': 'form-select drug-select',
            'required': True
        })
    )
    
    class Meta:
        model = PrescriptionItem
        fields = ['drug', 'dosage', 'frequency', 'duration', 'quantity', 'instructions']
        widgets = {
            'dosage': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 1 tablet'
            }),
            'frequency': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., twice daily'
            }),
            'duration': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., 7 days'
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'placeholder': 'Quantity'
            }),
            'instructions': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Special instructions (optional)'
            }),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        quantity = cleaned_data.get('quantity')
        duration = cleaned_data.get('duration')
        
        # Extract number from duration string
        if duration:
            import re
            numbers = re.findall(r'\d+', duration)
            if numbers:
                duration_days = int(numbers[0])
                # Rough check: quantity shouldn't be too high for the duration
                if quantity and quantity > duration_days * 4:  # Assuming max 4 doses per day
                    raise forms.ValidationError("Quantity seems high for the specified duration")
        
        return cleaned_data

class PrescriptionItemFormSet(forms.BaseFormSet):
    def clean(self):
        """Check that no two drugs are the same"""
        if any(self.errors):
            return
        
        drugs = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                drug = form.cleaned_data.get('drug')
                if drug in drugs:
                    raise forms.ValidationError(f"Duplicate drug: {drug.name}. Please combine quantities or remove duplicate.")
                drugs.append(drug)

class PrescriptionSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by Rx #, patient name...'
        })
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', 'All Status')] + list(Prescription.STATUS_CHOICES),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )

class PrescriptionVerifyForm(forms.Form):
    VERIFICATION_CHOICES = [
        ('verify', 'Verify and Approve'),
        ('reject', 'Reject Prescription'),
        ('modify', 'Request Modifications'),
    ]
    
    action = forms.ChoiceField(
        choices=VERIFICATION_CHOICES,
        widget=forms.RadioSelect(attrs={
            'class': 'form-check-input'
        })
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Add verification notes or reason for rejection...'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        notes = cleaned_data.get('notes')
        
        if action in ['reject', 'modify'] and not notes:
            raise forms.ValidationError("Please provide a reason when rejecting or requesting modifications")
        
        return cleaned_data

class InteractionOverrideForm(forms.Form):
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Please provide a clinical reason for overriding this interaction alert'
        })
    )
    confirm = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="I confirm that I have reviewed the interaction and accept clinical responsibility"
    )
    
    def clean_reason(self):
        reason = self.cleaned_data.get('reason')
        if len(reason) < 20:
            raise forms.ValidationError("Please provide a detailed clinical reason (minimum 20 characters)")
        return reason

class PrescriptionDispenseForm(forms.Form):
    pharmacist_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Additional dispensing notes (optional)'
        })
    )
    counsel_patient = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="I have counseled the patient on proper medication use"
    )
    verify_instructions = forms.BooleanField(
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label="I have verified the dosage instructions are correct"
    )
    
    def clean(self):
        cleaned_data = super().clean()
        if not cleaned_data.get('verify_instructions'):
            raise forms.ValidationError("You must verify the dosage instructions before dispensing")
        return cleaned_data

class PrescriptionRefillForm(forms.Form):
    refill_quantity = forms.IntegerField(
        min_value=1,
        max_value=30,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Refill quantity'
        })
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 2,
            'placeholder': 'Reason for refill'
        })
    )
    authorized_by = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': "Prescribing doctor's name"
        })
    )