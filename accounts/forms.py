"""
User Forms for Multi-Database Architecture

This module contains forms for user management.
Company and Branch models are imported from company.models (vendor database).
Users are stored in client database but reference branches by ID.
"""

from django import forms
from accounts_admin.models import Account
from company.models import Company, Branch
from .models import User, UserProfile
from .validators import allow_only_images_validator

import random
import string
from django.utils.text import slugify

from customers.models import Customer


class UserForm(forms.ModelForm):
    """
    Form for creating new users with multi-database support.
    Handles branch selection from vendor database and converts to branch_id.
    """
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password', 'required': 'required'})
    )
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'required': 'required'})
    )
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter First Name', 'required': 'required'})
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter Last Name', 'required': 'required'})
    )
    username = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter Username', 'required': 'required'})
    )
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={'placeholder': 'Enter Email', 'required': 'required'})
    )
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter Phone Number', 'required': 'required'})
    )
    
    # Branch selection from vendor database
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.using('vendor_db').all(),
        empty_label="Select Branch",
        required=True,
        help_text="Branch from vendor database"
    )
    
    role = forms.TypedChoiceField(
        choices=User.ROLE_CHOICE,
        coerce=int,
        empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select', 'required': 'required'})
    )

    # Optional cashier fields
    cashier_gl = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Cashier GL'})
    )
    cashier_ac = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Cashier AC'})
    )

    # Customer selection (optional)
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(label='C'),
        required=False,
        empty_label="Select Customer",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # GL and AC numbers for user accounts
    gl_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter GL Number'})
    )
    ac_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter AC Number'})
    )

    class Meta:
        model = User
        fields = [
            'profile_picture', 'first_name', 'last_name',
            'username', 'email', 'role', 'phone_number', 
            'password', 'cashier_gl', 'cashier_ac', 'customer',
            'gl_no', 'ac_no'
        ]
        # Note: 'branch' is handled separately as it's not a direct model field

    def __init__(self, *args, **kwargs):
        """Initialize form with branch choices from vendor database"""
        super().__init__(*args, **kwargs)
        
        # If editing existing user, set initial branch selection
        if self.instance.pk and self.instance.branch_id:
            try:
                initial_branch = Branch.objects.using('vendor_db').get(id=self.instance.branch_id)
                self.fields['branch'].initial = initial_branch
            except Branch.DoesNotExist:
                pass

    def clean(self):
        """Validate form data"""
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        # Password confirmation validation
        if password != confirm_password:
            raise forms.ValidationError("Password does not match!")

        # Validate branch selection
        branch = cleaned_data.get('branch')
        if not branch:
            raise forms.ValidationError("Branch selection is required!")

        return cleaned_data

    def save(self, commit=True):
        """
        Custom save to handle branch_id conversion and activation code generation
        """
        user = super().save(commit=False)
        password = self.cleaned_data.get('password')
        branch = self.cleaned_data.get('branch')
        
        # Set password securely
        user.set_password(password)

        # Convert branch object to branch_id for storage
        if branch:
            user.branch_id = str(branch.id)

        # Auto-generate activation_code if role is Customer
        if user.role == User.CUSTOMER and branch:
            if not user.activation_code:
                branch_code = slugify(branch.branch_name)[:3].upper()
                random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                user.activation_code = f"{branch_code}{random_part}"

        if commit:
            user.save()
        return user


class EdituserForm(forms.ModelForm):
    """
    Form for editing existing users with multi-database support.
    Note: Keeping the old name for compatibility with existing views.
    """
    
    # Branch selection from vendor database
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.using('vendor_db').all(),
        empty_label="Select Branch",
        required=True,
        help_text="Branch from vendor database"
    )
    
    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(label='C'),
        required=False,
        empty_label="Select Customer",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    cashier_ac = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Cashier AC'})
    )

    cashier_gl = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Cashier GL'})
    )

    # GL and AC numbers
    gl_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter GL Number'})
    )
    ac_no = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter AC Number'})
    )

    class Meta:
        model = User
        fields = [
            'profile_picture', 'first_name', 'last_name', 'username', 
            'email', 'role', 'phone_number', 'cashier_gl', 'cashier_ac', 
            'customer', 'gl_no', 'ac_no'
        ]

    def __init__(self, *args, **kwargs):
        """Initialize form with current branch selection"""
        super().__init__(*args, **kwargs)
        
        # Set initial branch selection for existing users
        if self.instance.pk and self.instance.branch_id:
            try:
                initial_branch = Branch.objects.using('vendor_db').get(id=self.instance.branch_id)
                self.fields['branch'].initial = initial_branch
            except Branch.DoesNotExist:
                pass

    def save(self, commit=True):
        """Custom save to handle branch_id conversion"""
        user = super().save(commit=False)
        branch = self.cleaned_data.get('branch')
        
        # Convert branch object to branch_id for storage
        if branch:
            user.branch_id = str(branch.id)
        
        if commit:
            user.save()
        return user


class UserProfileForm(forms.ModelForm):
    """
    Form for user profile information.
    """
    first_name = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter First Name', 'required': 'required'})
    )
    last_name = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter Last Name', 'required': 'required'})
    )
    phone_number = forms.CharField(
        widget=forms.TextInput(attrs={'placeholder': 'Enter Phone Number', 'required': 'required'})
    )
    address = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Address'})
    )
    country = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Country'})
    )
    state = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter State'})
    )
    city = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter City'})
    )

    class Meta:
        model = UserProfile
        fields = ['address', 'country', 'state', 'city']

    def save(self, user, commit=True):
        """Save profile and update related user fields"""
        profile = super().save(commit=False)
        
        # Update user fields if provided
        if hasattr(self, 'cleaned_data'):
            if self.cleaned_data.get('first_name'):
                user.first_name = self.cleaned_data['first_name']
            if self.cleaned_data.get('last_name'):
                user.last_name = self.cleaned_data['last_name']
            if self.cleaned_data.get('phone_number'):
                user.phone_number = self.cleaned_data['phone_number']
            
            if commit:
                user.save()
        
        # Link profile to user
        profile.user = user
        
        if commit:
            profile.save()
        return profile


class UserProfilePictureForm(forms.ModelForm):
    """
    Form for updating user profile picture.
    """
    profile_picture = forms.ImageField(
        validators=[allow_only_images_validator],
        widget=forms.FileInput(attrs={'class': 'form-control'})
    )

    class Meta:
        model = User
        fields = ['profile_picture']