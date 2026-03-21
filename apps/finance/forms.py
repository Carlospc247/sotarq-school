# apps/finance/forms.py
from django import forms
from decimal import Decimal
from .models import FeeType



class FeeTypeForm(forms.ModelForm):
    class Meta:
        model = FeeType
        fields = ['name', 'amount', 'recurring']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-3 bg-slate-50 border border-slate-200 rounded-xl font-bold',
                'placeholder': 'Ex: Taxa de Certificado'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'w-full p-3 bg-slate-50 border border-slate-200 rounded-xl font-bold',
                'placeholder': '0.00'
            }),
            'recurring': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500'
            }),
        }

class PriceUpdateForm(forms.Form):
    fee_id = forms.IntegerField(widget=forms.HiddenInput())
    amount = forms.DecimalField(
        max_digits=12, 
        decimal_places=2,
        min_value=Decimal('0.00'),
        widget=forms.NumberInput(attrs={
            'class': 'flex-1 px-4 py-2 rounded-xl border-none ring-1 ring-slate-200 focus:ring-2 focus:ring-indigo-600 font-bold text-slate-700',
            'placeholder': '0,00'
        })
    )

    def clean_amount(self):
        amount = self.cleaned_data.get('amount')
        if amount < 0:
            raise forms.ValidationError("O preço não pode ser negativo.")
        return amount


