from django import forms
from .models import FixedAsset

class FixedAssetForm(forms.ModelForm):
    class Meta:
        model = FixedAsset
        fields = '__all__'  # Include all fields from the model
        widgets = {
            'date_of_purchase': forms.DateInput(attrs={'type': 'date'}),
            'assigned_date': forms.DateInput(attrs={'type': 'date'}),
            'depreciation_frequency': forms.Select(choices=FixedAsset.DEPRECIATION_FREQUENCY_CHOICES),
        }

    def clean_residual_value(self):
        residual_value = self.cleaned_data.get('residual_value')
        asset_cost = self.cleaned_data.get('asset_cost')

        if residual_value and asset_cost and residual_value > asset_cost:
            raise forms.ValidationError("Residual value cannot be greater than asset cost.")
        return residual_value




from django import forms
from .models import FixedAsset

class AssetRevaluationForm(forms.Form):
    new_value = forms.DecimalField(max_digits=15, decimal_places=2, label="New Asset Value")
    new_residual = forms.DecimalField(max_digits=15, decimal_places=2, label="New Residual Value", required=False)
    reason = forms.CharField(widget=forms.Textarea, required=False, label="Revaluation Reason")

    def clean_new_value(self):
        value = self.cleaned_data.get("new_value")
        if value <= 0:
            raise forms.ValidationError("Asset value must be greater than zero.")
        return value
