from django import forms
from .models import Company, Branch

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = '__all__'




import random
from django import forms
from .models import Branch

class BranchForm(forms.ModelForm):
    session_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )
    system_date_date = forms.DateField(
        widget=forms.DateInput(attrs={'type': 'date'}),
        required=False
    )

    class Meta:
        model = Branch
        fields = [
            'company',  # 👈 use the FK, not company_name
            'branch_code', 'branch_name', 'logo', 'address',
            'cac_number', 'license_number', 'company_type', 'bvn_number', 'plan',
            'session_date', 'system_date_date', 'session_status'
        ]
        widgets = {
            'branch_name': forms.TextInput(attrs={'placeholder': 'e.g. Akobo Branch'}),
            'address': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Full branch address'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.instance.pk:
            # Auto-generate unique 4-digit branch code
            self.fields['branch_code'].initial = self.generate_branch_code()

        for field_name, field in self.fields.items():
            field.widget.attrs.setdefault('class', 'form-control')

    def generate_branch_code(self):
        existing_codes = Branch.objects.values_list('branch_code', flat=True)
        while True:
            code = str(random.randint(1000, 9999))
            if code not in existing_codes:
                return code



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
