from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, PasswordChangeForm
from django.core.validators import RegexValidator, EmailValidator, MinLengthValidator
from django.utils import timezone
from .models import UserProfile, Pharmacy, PendingUserRequest
import re


class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username or Email',
            'autofocus': True
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password'
        })
    )

class PharmacyRegistrationForm(UserCreationForm):
    pharmacy_name = forms.CharField(
        max_length=200,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Pharmacy Name'
        })
    )
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    phone_number = forms.CharField(
        max_length=15,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number (optional)'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError('This email is already registered. Please login instead.')
        return email
    
    def clean_pharmacy_name(self):
        pharmacy_name = self.cleaned_data.get('pharmacy_name')
        if not pharmacy_name:
            raise forms.ValidationError('Please enter a pharmacy name')
        return pharmacy_name.strip()
    

class AdminApprovalForm(forms.Form):
    role = forms.ChoiceField(
        choices=UserProfile.USER_ROLES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    approve = forms.BooleanField(required=False, widget=forms.HiddenInput)
    reject = forms.BooleanField(required=False, widget=forms.HiddenInput)
    rejection_reason = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'Reason for rejection (optional)'
        })
    )


class UserRoleUpdateForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'})
        }

class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'})
        }
        
class UserRegistrationForm(UserCreationForm):
    pharmacy_name = forms.CharField(max_length=200, required=True, label='Pharmacy Name')

    username = forms.CharField(
        max_length=150,
        min_length=3,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Username',
            'autocomplete': 'username',
            'pattern': '[a-zA-Z0-9_]+',
            'title': 'Only letters, numbers, and underscores allowed'
        }),
        validators=[MinLengthValidator(3)]
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address',
            'autocomplete': 'email'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    
    password1 = forms.CharField(
        label='Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Password',
            'autocomplete': 'new-password'
        })
    )
    
    password2 = forms.CharField(
        label='Confirm Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm Password',
            'autocomplete': 'new-password'
        })
    )
    
    phone_number = forms.CharField(
        max_length=15,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Phone Number',
            'data-mask': '(000) 000-0000'
        }),
        validators=[RegexValidator(
            regex=r'^\+?1?\d{9,15}$',
            message='Enter a valid phone number'
        )]
    )
    
    license_number = forms.CharField(
        max_length=50,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'License Number (if applicable)'
        })
    )
    
    role = forms.ChoiceField(
        choices=UserProfile.USER_ROLES,
        initial='technician',
        widget=forms.Select(attrs={
            'class': 'form-select'
        })
    )
    
    accept_terms = forms.BooleanField(
        required=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        }),
        label='I accept the terms and conditions'
    )
    
    class Meta:
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 
                 'password1', 'password2')
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            username = username.lower()
            if User.objects.filter(username__iexact=username).exists():
                raise forms.ValidationError('This username is already taken.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            if User.objects.filter(email__iexact=email).exists():
                raise forms.ValidationError('This email is already registered.')
        return email
    
    def clean_password1(self):
        password = self.cleaned_data.get('password1')
        if password:
            # Password strength validation
            if len(password) < 8:
                raise forms.ValidationError('Password must be at least 8 characters long.')
            if not re.search(r'[A-Z]', password):
                raise forms.ValidationError('Password must contain at least one uppercase letter.')
            if not re.search(r'[a-z]', password):
                raise forms.ValidationError('Password must contain at least one lowercase letter.')
            if not re.search(r'[0-9]', password):
                raise forms.ValidationError('Password must contain at least one number.')
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                raise forms.ValidationError('Password must contain at least one special character.')
        return password
    
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            # Create pharmacy
            from .models import Pharmacy
            pharmacy = Pharmacy.objects.create(
                name=self.cleaned_data['pharmacy_name']
            )
            # DON'T create UserProfile here - the signal will do it
            # Just update the profile that the signal created
            profile = user.profile  # This gets the profile created by signal
            profile.pharmacy = pharmacy
            profile.role = 'admin'
            profile.save()
        return user
    
    # def save(self, commit=True):
    #     user = super().save(commit=False)
    #     user.email = self.cleaned_data['email'].lower()
    #     user.username = self.cleaned_data['username'].lower()
    #     if commit:
    #         user.save()
    #         # Create pharmacy
    #         from .models import Pharmacy
    #         pharmacy = Pharmacy.objects.create(
    #             name=self.cleaned_data['pharmacy_name']
    #         )
    #         # Create profile with pharmacy
    #         UserProfile.objects.create(
    #             user=user,
    #             role='admin',
    #             phone_number='',
    #             pharmacy=pharmacy
    #         )
    #     return user

class UserUpdateForm(forms.ModelForm):
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Email Address'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First Name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last Name'
        })
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'email')
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.lower()
            if User.objects.filter(email__iexact=email).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError('This email is already registered.')
        return email

class PasswordResetRequestForm(forms.Form):
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address',
            'autocomplete': 'email'
        })
    )

class SetPasswordForm(forms.Form):
    new_password1 = forms.CharField(
        label='New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'New Password',
            'autocomplete': 'new-password'
        })
    )
    
    new_password2 = forms.CharField(
        label='Confirm New Password',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm New Password',
            'autocomplete': 'new-password'
        })
    )
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Passwords do not match.')
        
        # Password strength validation
        if password1:
            if len(password1) < 8:
                raise forms.ValidationError('Password must be at least 8 characters long.')
            if not re.search(r'[A-Z]', password1):
                raise forms.ValidationError('Password must contain at least one uppercase letter.')
            if not re.search(r'[a-z]', password1):
                raise forms.ValidationError('Password must contain at least one lowercase letter.')
            if not re.search(r'[0-9]', password1):
                raise forms.ValidationError('Password must contain at least one number.')
        
        return cleaned_data

# Keep your existing forms
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'is_active']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Last Name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email Address'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['role', 'license_number', 'phone_number']
        widgets = {
            'role': forms.Select(attrs={'class': 'form-select'}),
            'license_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'License Number'}),
            'phone_number': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Phone Number'}),
        }