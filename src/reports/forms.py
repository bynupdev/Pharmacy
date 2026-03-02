from django import forms
from django.utils import timezone
from datetime import datetime, timedelta

class DateRangeForm(forms.Form):
    DATE_PRESETS = [
        ('today', 'Today'),
        ('yesterday', 'Yesterday'),
        ('this_week', 'This Week'),
        ('last_week', 'Last Week'),
        ('this_month', 'This Month'),
        ('last_month', 'Last Month'),
        ('this_quarter', 'This Quarter'),
        ('last_quarter', 'Last Quarter'),
        ('this_year', 'This Year'),
        ('last_year', 'Last Year'),
        ('custom', 'Custom Range'),
    ]
    
    date_preset = forms.ChoiceField(
        choices=DATE_PRESETS,
        required=False,
        initial='this_month',
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id': 'date-preset'
        })
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'date-from'
        })
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date',
            'id': 'date-to'
        })
    )
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set default date range to current month
        today = timezone.now().date()
        self.fields['date_from'].initial = today.replace(day=1)
        self.fields['date_to'].initial = today
    
    def clean(self):
        cleaned_data = super().clean()
        date_preset = cleaned_data.get('date_preset')
        date_from = cleaned_data.get('date_from')
        date_to = cleaned_data.get('date_to')
        
        if date_preset == 'custom':
            if not date_from or not date_to:
                raise forms.ValidationError("Both start and end dates are required for custom range")
            if date_from > date_to:
                raise forms.ValidationError("Start date must be before end date")
        
        return cleaned_data
    
    def get_date_range(self):
        """Calculate actual date range based on preset"""
        cleaned_data = self.cleaned_data
        date_preset = cleaned_data.get('date_preset')
        today = timezone.now().date()
        
        if date_preset == 'custom':
            return cleaned_data.get('date_from'), cleaned_data.get('date_to')
        
        ranges = {
            'today': (today, today),
            'yesterday': (today - timedelta(days=1), today - timedelta(days=1)),
            'this_week': (today - timedelta(days=today.weekday()), today),
            'last_week': (
                today - timedelta(days=today.weekday() + 7),
                today - timedelta(days=today.weekday() + 1)
            ),
            'this_month': (today.replace(day=1), today),
            'last_month': (
                (today.replace(day=1) - timedelta(days=1)).replace(day=1),
                today.replace(day=1) - timedelta(days=1)
            ),
            'this_quarter': (self._get_quarter_start(today), today),
            'last_quarter': (
                self._get_quarter_start(today) - timedelta(days=90),
                self._get_quarter_start(today) - timedelta(days=1)
            ),
            'this_year': (today.replace(month=1, day=1), today),
            'last_year': (
                today.replace(year=today.year-1, month=1, day=1),
                today.replace(year=today.year-1, month=12, day=31)
            ),
        }
        
        return ranges.get(date_preset, (today.replace(day=1), today))
    
    def _get_quarter_start(self, date):
        """Get the first day of the current quarter"""
        quarter_months = [1, 4, 7, 10]
        quarter_start_month = quarter_months[(date.month - 1) // 3]
        return date.replace(month=quarter_start_month, day=1)

class ReportExportForm(forms.Form):
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('excel', 'Excel'),
        ('pdf', 'PDF'),
    ]
    
    format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        initial='csv',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    include_charts = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    email_report = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    email_address = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email address'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('email_report') and not cleaned_data.get('email_address'):
            raise forms.ValidationError("Email address is required when emailing report")
        return cleaned_data

class InventoryReportForm(forms.Form):
    SORT_BY = [
        ('name', 'Drug Name'),
        ('stock', 'Stock Level'),
        ('value', 'Inventory Value'),
        ('expiry', 'Expiry Date'),
    ]
    
    category = forms.ChoiceField(
        required=False,
        choices=[('all', 'All Categories')] + list(Drug.DRUG_FORMS),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    manufacturer = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by manufacturer'
        })
    )
    low_stock_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    expiring_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    sort_by = forms.ChoiceField(
        choices=SORT_BY,
        initial='name',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )

class SalesReportForm(forms.Form):
    GROUP_BY = [
        ('day', 'Daily'),
        ('week', 'Weekly'),
        ('month', 'Monthly'),
        ('quarter', 'Quarterly'),
        ('year', 'Yearly'),
    ]
    
    group_by = forms.ChoiceField(
        choices=GROUP_BY,
        initial='day',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    payment_method = forms.ChoiceField(
        required=False,
        choices=[('all', 'All Methods')] + list(Sale.PAYMENT_METHODS),
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    prescription_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    show_tax_details = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )

class InteractionReportForm(forms.Form):
    SEVERITY_CHOICES = [('all', 'All Severities')] + list(InteractionLog.SEVERITY_CHOICES)
    
    severity = forms.ChoiceField(
        required=False,
        choices=SEVERITY_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    interaction_type = forms.ChoiceField(
        required=False,
        choices=[('all', 'All Types'), 
                ('drug-drug', 'Drug-Drug'),
                ('drug-allergy', 'Drug-Allergy'),
                ('contraindication', 'Contraindication'),
                ('dosage-warning', 'Dosage Warning')],
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    show_overridden_only = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    drug_filter = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Filter by drug name'
        })
    )

class DashboardCustomizationForm(forms.Form):
    WIDGETS = [
        ('sales_summary', 'Sales Summary'),
        ('inventory_alerts', 'Inventory Alerts'),
        ('recent_prescriptions', 'Recent Prescriptions'),
        ('expiring_medications', 'Expiring Medications'),
        ('interaction_stats', 'Interaction Statistics'),
        ('top_drugs', 'Top Selling Drugs'),
        ('revenue_chart', 'Revenue Chart'),
        ('patient_demographics', 'Patient Demographics'),
    ]
    
    refresh_interval = forms.ChoiceField(
        choices=[('30', '30 seconds'), ('60', '1 minute'), 
                ('300', '5 minutes'), ('900', '15 minutes')],
        initial='300',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    widgets = forms.MultipleChoiceField(
        choices=WIDGETS,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'form-check-input'
        }),
        initial=[w[0] for w in WIDGETS]
    )
    show_charts = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )