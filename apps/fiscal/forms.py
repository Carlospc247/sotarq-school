# apps/fiscal/forms.py
from django import forms
from .models import FiscalConfig

# Estilos Tailwind para manter o padrão "Máquina de Dinheiro"
TW_INPUT = "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 px-3 border"
TW_CHECKBOX = "h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"

class FiscalConfigForm(forms.ModelForm):
    class Meta:
        model = FiscalConfig
        # Ajustado para os nomes reais do seu modelo
        fields = ['saft_generation_day', 'auto_submit_agt', 'email_notification']
        
        widgets = {
            'saft_generation_day': forms.NumberInput(attrs={
                'class': TW_INPUT, 
                'min': 1, 
                'max': 28,
                'placeholder': 'Ex: 15'
            }),
            'email_notification': forms.EmailInput(attrs={
                'class': TW_INPUT, 
                'placeholder': 'contabilidade@escola.ao'
            }),
            'auto_submit_agt': forms.CheckboxInput(attrs={
                'class': TW_CHECKBOX
            }),
        }
        
        labels = {
            'saft_generation_day': 'Dia de Geração do SAFT',
            'auto_submit_agt': 'Submeter automaticamente à AGT',
            'email_notification': 'Email para Notificações',
        }