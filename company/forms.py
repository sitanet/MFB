from django import forms
from .models import Company, Branch

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = '__all__'

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = [
            'branch_code', 'branch_name', 'company', 
            'session_date', 'system_date_date', 'session_status'
        ]


from django import forms
from .models import Company, Branch

class EndSession(forms.ModelForm):
    class Meta:
        model = Branch  # Change this to the Branch model
        fields = ['session_date', 'session_status']

    SESSION_STATUS_CHOICES = (
        ('Open', 'Open'),
        ('Closed', 'Closed'),
    )
    session_status = forms.ChoiceField(choices=SESSION_STATUS_CHOICES, widget=forms.Select)
