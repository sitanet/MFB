from django import forms
from accounts_admin.models import Account

from company.models import Company, Branch
from .models import User, UserProfile
from .validators import allow_only_images_validator


from django import forms
from .models import User, Company , Branch # Assuming Company model exists

import random, string
from django.utils.text import slugify

from customers.models import Customer

class UserForm(forms.ModelForm):
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
    branch = forms.ModelChoiceField(
        queryset=Branch.objects.all(),
        empty_label="Select Branch",
        required=True
    )
    role = forms.TypedChoiceField(
        choices=User.ROLE_CHOICE,   # ✅ show all roles
        coerce=int,
        empty_value=None,
        widget=forms.Select(attrs={'class': 'form-select', 'required': 'required'})
    )

    # ✅ Now optional
    cashier_gl = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Cashier GL'})
    )
    cashier_ac = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Enter Cashier AC'})
    )

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(label='C'),  # ✅ Only customers with type='C'
        required=False,  # Not compulsory
        empty_label="Select Customer",
        widget=forms.Select(attrs={'class': 'form-select'})
    )


    class Meta:
        model = User
        fields = [
            'profile_picture', 'first_name', 'last_name',
            'username', 'email', 'role', 'branch',
            'phone_number', 'password', 'cashier_gl', 'cashier_ac','customer'
        ]

    def clean(self):
        cleaned_data = super(UserForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError("Password does not match!")

        return cleaned_data

    def save(self, commit=True):
        """Custom save to set password and activation code for customers"""
        user = super(UserForm, self).save(commit=False)
        password = self.cleaned_data.get('password')
        user.set_password(password)  # ✅ securely hash password

        # ✅ Auto-generate activation_code if role is Customer
        if user.role == User.CUSTOMER and user.branch:
            if not user.activation_code:  # only create if missing
                branch_code = slugify(user.branch.branch_name)[:3].upper()
                random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=7))
                user.activation_code = f"{branch_code}{random_part}"

        if commit:
            user.save()
        return user


class EdituserForm(forms.ModelForm):
     customer = forms.ModelChoiceField(
        queryset=Customer.objects.filter(label='C'),  # Only customers with type='C'
        required=False,  # Optional
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


     class Meta:
        model = User
        fields = ['profile_picture','first_name', 'last_name', 'username', 'email', 'role', 'phone_number','cashier_gl','cashier_ac','customer']
       
class UserProfileForm(forms.ModelForm):
   

    
    
    class Meta:
        model = UserProfile
        fields = []

class UserProfilePictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_picture']




