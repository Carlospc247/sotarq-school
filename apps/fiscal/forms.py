# apps/fiscal/forms.py
from django import forms
from .models import FiscalConfig, TaxaIVAAGT


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



class TaxaIVAAGTForm(forms.ModelForm):
    class Meta:
        model = TaxaIVAAGT
        fields = ['nome', 'tax_type', 'tax_code', 'tax_percentage', 'exemption_reason', 'ativo']
        widgets = {
            'nome': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 transition-all outline-none text-sm font-bold',
                'placeholder': 'Ex: IVA REGIME GERAL 14%'
            }),
            'tax_type': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500 transition-all outline-none text-sm font-bold appearance-none'
            }),
            'tax_code': forms.Select(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500 transition-all outline-none text-sm font-bold appearance-none'
            }),
            'tax_percentage': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500 transition-all outline-none text-sm font-mono font-black',
                'step': '0.01'
            }),
            'exemption_reason': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 bg-slate-50 border border-slate-200 rounded-2xl focus:ring-2 focus:ring-indigo-500 transition-all outline-none text-sm font-mono',
                'placeholder': 'Ex: M02'
            }),
            'ativo': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500'
            }),
        }

        def clean(self):
            cleaned_data = super().clean()
            tax_code = cleaned_data.get('tax_code')
            exemption_reason = cleaned_data.get('exemption_reason')
            tax_percentage = cleaned_data.get('tax_percentage')

            # REGRA AGT 01: Isentos/Não Sujeitos PRECISAM de motivo legal
            if tax_code in ['ISE', 'NSU'] and not exemption_reason:
                self.add_error('exemption_reason', "ERRO FISCAL: Códigos ISE/NSU requerem motivo legal (ex: M02).")

            # REGRA AGT 02: Se for Normal/Intercalar, a percentagem deve ser > 0
            if tax_code in ['NOR', 'INT'] and tax_percentage <= 0:
                self.add_error('tax_percentage', "ERRO: Taxas normais/intercalares devem ter percentagem positiva.")

            return cleaned_data


