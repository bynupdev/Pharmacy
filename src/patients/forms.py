from django import forms
from django.core.validators import RegexValidator, EmailValidator
from .models import Patient, Allergy
from datetime import date

class PatientForm(forms.ModelForm):
    class Meta:
        model = Patient
        fields = [
            'first_name', 'last_name', 'date_of_birth', 'gender',
            'phone', 'email', 'address', 'allergies'
        ]
        widgets = {
            'first_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'First name'
            }),
            'last_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Last name'
            }),
            'date_of_birth': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date',
                'max': date.today().isoformat()
            }),
            'gender': forms.Select(attrs={
                'class': 'form-select'
            }),
            'phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Phone number'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email (optional)'
            }),
            'address': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Address (optional)'
            }),
            'allergies': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'List allergies (separate with commas)'
            }),
        }
        labels = {
            'date_of_birth': 'Date of birth',
            'phone': 'Phone number',
        }
        required = ['first_name', 'last_name', 'date_of_birth', 'gender', 'phone']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make email and address optional
        self.fields['email'].required = False
        self.fields['address'].required = False
        self.fields['allergies'].required = False

class AllergyForm(forms.ModelForm):
    class Meta:
        model = Allergy
        fields = ['allergen', 'severity', 'reaction', 'diagnosed_date']
        widgets = {
            'allergen': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Allergen (e.g., Penicillin, Peanuts)'
            }),
            'severity': forms.Select(attrs={
                'class': 'form-select'
            }),
            'reaction': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 2,
                'placeholder': 'Describe the reaction'
            }),
            'diagnosed_date': forms.DateInput(attrs={
                'class': 'form-control',
                'type': 'date'
            }),
        }
    
    def clean_allergen(self):
        allergen = self.cleaned_data.get('allergen')
        if allergen:
            # Check if this allergen already exists for this patient
            patient = self.instance.patient if self.instance.pk else None
            if patient and Allergy.objects.filter(patient=patient, allergen__iexact=allergen).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError("This allergy has already been recorded for this patient")
        return allergen

class PatientSearchForm(forms.Form):
    query = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search by name, phone, or email...'
        })
    )
    age_min = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min Age'
        })
    )
    age_max = forms.IntegerField(
        required=False,
        min_value=0,
        max_value=150,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max Age'
        })
    )
    blood_type = forms.ChoiceField(
        required=False,
        choices=[('', 'All Blood Types')] + list(Patient.BLOOD_TYPES),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

class PatientAllergyCheckForm(forms.Form):
    drug_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter drug name to check against allergies'
        })
    )
    
    def clean_drug_name(self):
        drug_name = self.cleaned_data.get('drug_name')
        if len(drug_name) < 3:
            raise forms.ValidationError("Please enter at least 3 characters")
        return drug_name

class EmergencyContactForm(forms.Form):
    contact_name = forms.CharField(
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contact Name'
        })
    )
    contact_phone = forms.CharField(
        max_length=15,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Contact Phone'
        })
    )
    relationship = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Relationship to patient'
        })
    )