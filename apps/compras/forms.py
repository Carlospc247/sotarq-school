# apps/compras/forms.py
from django import forms
from django.forms import inlineformset_factory
from .models import Product, Purchase, PurchaseItem, StockWaste

# Classes padrão do Tailwind para inputs
TW_INPUT = "mt-1 block w-full rounded-md border-gray-300 shadow-sm focus:border-indigo-500 focus:ring-indigo-500 sm:text-sm py-2 px-3 border"

class PurchaseForm(forms.ModelForm):
    class Meta:
        model = Purchase
        fields = ['supplier', 'date', 'invoice_ref']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date', 'class': TW_INPUT}),
            'supplier': forms.Select(attrs={'class': TW_INPUT}),
            'invoice_ref': forms.TextInput(attrs={'class': TW_INPUT, 'placeholder': 'Ex: FT 2026/001'}),
        }

class PurchaseItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseItem
        fields = ['product', 'quantity', 'unit_price']
        widgets = {
            'product': forms.Select(attrs={'class': TW_INPUT}),
            'quantity': forms.NumberInput(attrs={'class': TW_INPUT, 'step': '1'}),
            'unit_price': forms.NumberInput(attrs={'class': TW_INPUT, 'step': '0.01'}),
        }

PurchaseItemFormSet = inlineformset_factory(
    Purchase, PurchaseItem,
    form=PurchaseItemForm,
    extra=1,
    can_delete=True
)



class StockWasteForm(forms.ModelForm):
    class Meta:
        model = StockWaste
        fields = ['product', 'quantity', 'reason', 'photo_evidence', 'description']
        
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Rigor Visual: Injeção de classes Tailwind em todos os campos
        common_classes = "w-full mt-2 p-4 bg-slate-50 border-none rounded-2xl font-bold text-slate-700 focus:ring-2 focus:ring-red-500"
        
        for field_name in self.fields:
            self.fields[field_name].widget.attrs.update({'class': common_classes})
        
        # Filtro de sanidade: Apenas produtos ativos
        self.fields['product'].queryset = Product.objects.filter(is_active=True)
        self.fields['description'].widget.attrs.update({'rows': 3, 'placeholder': 'Descreva detalhadamente o ocorrido...'})

    def clean_quantity(self):
        quantity = self.cleaned_data.get('quantity')
        if quantity <= 0:
            raise forms.ValidationError("A quantidade para baixa deve ser superior a zero.")
        return quantity


