# apps/academic/forms.py
from django import forms
from .models import AcademicGlobal, AcademicYear, AcademicEvent, Course, Class, GradeLevel, Subject
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


from django import forms
from django.forms import inlineformset_factory
from .models import Course, GradeLevel

"""

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        # REMOVIDOS: monthly_fee e enrollment_fee (Agora são FeeTypes)
        fields = ['name', 'code', 'level', 'duration_years', 'coordinator', 'taxa_iva']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-3 bg-white border border-slate-200 rounded-xl font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition'
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-3 bg-white border border-slate-200 rounded-xl font-bold text-slate-700'
            }),
            'level': forms.Select(attrs={
                'class': 'w-full p-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),
            'duration_years': forms.NumberInput(attrs={
                'class': 'w-full p-3 bg-white border border-slate-200 rounded-xl'
            }),
            'coordinator': forms.Select(attrs={
                'class': 'w-full p-3 bg-white border border-slate-200 rounded-xl'
            }),
            'taxa_iva': forms.Select(attrs={
                'class': 'w-full p-3 bg-slate-50 border-2 border-slate-200 rounded-xl font-bold text-slate-700 focus:border-indigo-500 transition'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtro de conformidade AGT: Apenas taxas de IVA ativas
        if 'taxa_iva' in self.fields:
            self.fields['taxa_iva'].queryset = self.fields['taxa_iva'].queryset.filter(ativo=True)
            self.fields['taxa_iva'].empty_label = "Selecione a Taxa (Ex: Isento M02)"

"""


class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        # Unificamos os campos de configuração e os campos de tarifário
        fields = [
            'name', 'code', 'level', 'duration_years', 
            'coordinator', 'taxa_iva', 
            'default_monthly_fee_type', 'default_enrollment_fee_type'
        ]
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full p-3 bg-white border border-slate-200 rounded-xl font-bold text-slate-700 focus:ring-2 focus:ring-indigo-500 transition'
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full p-3 bg-white border border-slate-200 rounded-xl font-bold text-slate-700'
            }),
            'level': forms.Select(attrs={
                'class': 'w-full p-3 bg-slate-50 border border-slate-200 rounded-xl'
            }),
            'duration_years': forms.NumberInput(attrs={
                'class': 'w-full p-3 bg-white border border-slate-200 rounded-xl',
                'step': '0.01',
                'readonly': 'readonly' # Definido pelo JS do template
            }),
            'coordinator': forms.Select(attrs={
                'class': 'w-full p-3 bg-white border border-slate-200 rounded-xl'
            }),
            'taxa_iva': forms.Select(attrs={
                'class': 'w-full p-3 bg-slate-50 border-2 border-slate-200 rounded-xl font-bold text-slate-700 focus:border-indigo-500 transition'
            }),
            # Widgets para as taxas (ID sincronizado com o JS que te enviei antes)
            'default_monthly_fee_type': forms.Select(attrs={
                'id': 'id_fee_type',
                'class': 'w-full p-3 rounded-xl border-none bg-white shadow-sm focus:ring-2 focus:ring-indigo-500'
            }),
            'default_enrollment_fee_type': forms.Select(attrs={
                'class': 'w-full p-3 rounded-xl border-none bg-white shadow-sm focus:ring-2 focus:ring-emerald-500'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Rigor Multi-tenant: Captura a escola
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        if school:
            # Filtro de Coordenadores da Escola
            if 'coordinator' in self.fields:
                self.fields['coordinator'].queryset = Teacher.objects.filter(school=school, user__is_active=True)
            
            # Filtro de Taxas do Tarifário da Escola
            if 'default_monthly_fee_type' in self.fields:
                self.fields['default_monthly_fee_type'].queryset = self.fields['default_monthly_fee_type'].queryset.filter(
                    school=school, recurring=True
                )
            
            if 'default_enrollment_fee_type' in self.fields:
                self.fields['default_enrollment_fee_type'].queryset = self.fields['default_enrollment_fee_type'].queryset.filter(
                    school=school, recurring=False # Geralmente matrícula não é recorrente mensal
                )

        # Conformidade AGT
        if 'taxa_iva' in self.fields:
            self.fields['taxa_iva'].queryset = self.fields['taxa_iva'].queryset.filter(ativo=True)
            self.fields['taxa_iva'].empty_label = "Selecione a Taxa (Ex: Isento M02)"



class CourseFeeAssociationForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['default_monthly_fee_type', 'default_enrollment_fee_type']
        widgets = {
            'default_monthly_fee_type': forms.Select(attrs={'class': 'p-2 bg-slate-800 text-white rounded-lg border-slate-700 text-xs'}),
            'default_enrollment_fee_type': forms.Select(attrs={'class': 'p-2 bg-slate-800 text-white rounded-lg border-slate-700 text-xs'}),
        }




# Mantenha como está se o modelo suportar, mas garanta o estilo SOTARQ
GradeLevelFormSet = inlineformset_factory(
    Course, 
    GradeLevel, 
    fields=['name', 'level_index', 'fee_percentage_increase'],
    extra=0,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={
            'class': 'form-input text-xs rounded-lg border-slate-200 bg-slate-50', 
            'readonly': 'readonly'
        }),
        'fee_percentage_increase': forms.NumberInput(attrs={
            'class': 'form-input text-xs font-black text-indigo-600 rounded-lg border-indigo-200 focus:ring-indigo-500',
            'step': '0.01',
            'placeholder': '0.00'
        }),
        'level_index': forms.NumberInput(attrs={'class': 'form-input text-xs w-16 rounded-lg'}),
    }
)



class ClassForm(forms.ModelForm):
    class Meta:
        model = Class
        fields = [
            'name', 'academic_year', 'grade_level', 
            'main_teacher', 'capacity', 'period', 'room_number'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900', 'placeholder': 'Ex: 10ª A'}),
            'academic_year': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900'}),
            'grade_level': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900'}),
            'main_teacher': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900'}),
            'capacity': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900'}),
            'period': forms.Select(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900'}),
            'room_number': forms.TextInput(attrs={'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900', 'placeholder': 'Ex: Sala 04'}),
        }


class GradeLevelForm(forms.ModelForm):
    # DEFINIÇÃO PRIORITÁRIA: required=False mata o erro de validação
    total_monthly_fee = forms.DecimalField(
        required=False, # Essencial para não barrar o POST
        max_digits=12, 
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'readonly': 'readonly',
            'class': 'total-monthly-fee-input w-full p-2 bg-slate-100 font-black text-emerald-600 rounded-lg border-none text-right',
            'step': '0.01'
        })
    )

    class Meta:
        model = GradeLevel
        # Unimos Identidade + Finanças
        fields = ['name', 'level_index', 'fee_percentage_increase', 'total_monthly_fee']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 font-bold',
                'readonly': 'readonly'
            }),
            'level_index': forms.NumberInput(attrs={
                'class': 'hidden',
            }),
            'fee_percentage_increase': forms.NumberInput(attrs={
                'class': 'w-full p-2 bg-white border border-slate-200 rounded-lg text-center font-bold focus:ring-2 focus:ring-indigo-500',
                'step': '0.01'
            }),
            # O widget do total_monthly_fee aqui na Meta será sobrescrito 
            # pela definição do campo lá em cima, o que é o comportamento desejado.
        }


# Factory para garantir que as GradeLevels sigam o Course
from django.forms import inlineformset_factory

GradeLevelFormSet = inlineformset_factory(
    Course, 
    GradeLevel, 
    form=GradeLevelForm, 
    extra=0, 
    can_delete=False # Segurança: Não permite deletar classes durante a edição de preços
)


class SubjectForm(forms.ModelForm):
    class Meta:
        model = Subject
        fields = ['name', 'code', 'grade_level', 'workload_hours']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none transition',
                'placeholder': 'Ex: Matemática'
            }),
            'code': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none transition',
                'placeholder': 'Ex: MAT-10'
            }),
            'grade_level': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none transition'
            }),
            'workload_hours': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none transition',
                'min': '1'
            }),
        }
        labels = {
            'name': 'Nome da Disciplina',
            'code': 'Código Sigla',
            'grade_level': 'Nível Académico / Classe',
            'workload_hours': 'Carga Horária Anual (Horas)'
        }



