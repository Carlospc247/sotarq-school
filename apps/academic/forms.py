# apps/academic/forms.py
from django import forms
from .models import AcademicGlobal, AcademicYear, AcademicEvent
from apps.teachers.models import Teacher


class AcademicYearForm(forms.ModelForm):
    class Meta:
        model = AcademicYear
        fields = ['name', 'start_date', 'end_date', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm', 
                'placeholder': 'Ex: 2025/2026'
            }),
            'start_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm',
                'placeholder': 'AAAA-MM-DD'  # <--- DICA VISUAL
            }),
            'end_date': forms.DateInput(attrs={
                'type': 'date', 
                'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm',
                'placeholder': 'AAAA-MM-DD'  # <--- DICA VISUAL
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded'
            }),
        }

    def clean(self):
        cleaned_data = super().clean()
        start = cleaned_data.get('start_date')
        end = cleaned_data.get('end_date')

        if start and end and end < start:
            self.add_error('end_date', "A data de fim deve ser posterior à data de início.")
        
        return cleaned_data
    


class PedagogicalLockForm(forms.ModelForm):
    break_exceptions = forms.ModelMultipleChoiceField(
        queryset=Teacher.objects.filter(user__is_active=True),
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={
            'class': 'grid grid-cols-2 gap-2 text-sm p-4 bg-slate-50 rounded-xl border border-slate-200'
        }),
        label="Professores Autorizados"
    )

    class Meta:
        model = AcademicGlobal
        fields = ['is_pedagogical_break', 'break_exceptions']  # <- remove executive_report_emails
        widgets = {
            'is_pedagogical_break': forms.CheckboxInput(attrs={
                'class': 'w-5 h-5 text-indigo-600 border-slate-300 rounded focus:ring-indigo-500'
            }),
        }

class AcademicEventEmailsForm(forms.ModelForm):
    class Meta:
        model = AcademicEvent
        fields = ['executive_report_emails']
        widgets = {
            'executive_report_emails': forms.Textarea(attrs={
                'rows': 2,
                'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm',
                'placeholder': 'direcao@escola.ao, bi@escola.ao'
            }),
        }


