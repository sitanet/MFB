from django import forms
from accounts_admin.models import Account

from company.models import Company, Branch
from .models import User, UserProfile
from .validators import allow_only_images_validator


from django import forms
from .models import User, Company , Branch # Assuming Company model exists

class UserForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Enter Password', 'required': 'required'}))
    confirm_password = forms.CharField(widget=forms.PasswordInput(attrs={'placeholder': 'Confirm Password', 'required': 'required'}))
    first_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter First Name', 'required': 'required'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter Last Name', 'required': 'required'}))
    username = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter Username', 'required': 'required'}))
    email = forms.EmailField(widget=forms.EmailInput(attrs={'placeholder': 'Enter Email', 'required': 'required'}))
    phone_number = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter Phone Number', 'required': 'required'}))
    
    # If the branch field is needed:
    # branch = forms.ModelChoiceField(queryset=Branch.objects.all(), empty_label="Select Branch", required=True)
    
    cashier_gl = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter Cashier GL', 'required': 'required'}))
    cashier_ac = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Enter Cashier AC', 'required': 'required'}))

    class Meta:
        model = User
        fields = ['profile_picture', 'first_name', 'last_name', 'username', 'email', 'role', 'phone_number', 'password', 'cashier_gl', 'cashier_ac']  # Add branch to the list of fields

    def clean(self):
        cleaned_data = super(UserForm, self).clean()
        password = cleaned_data.get('password')
        confirm_password = cleaned_data.get('confirm_password')

        if password != confirm_password:
            raise forms.ValidationError("Password does not match!")

        return cleaned_data


class EdituserForm(forms.ModelForm):

     class Meta:
        model = User
        fields = ['profile_picture','first_name', 'last_name', 'username', 'email', 'role', 'phone_number','cashier_gl','cashier_ac']
       
class UserProfileForm(forms.ModelForm):
   

    
    
    class Meta:
        model = UserProfile
        fields = []

class UserProfilePictureForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ['profile_picture']




