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



class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'level', 'duration_years', 'coordinator', 'monthly_fee', 'enrollment_fee', 'taxa_iva']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-input rounded-xl border-slate-200 w-full'}),
            'monthly_fee': forms.NumberInput(attrs={
                'class': 'w-full pl-4 pr-12 py-3 bg-white border-2 border-indigo-200 rounded-2xl font-black text-indigo-700 focus:ring-4 focus:ring-indigo-500/20 transition text-lg',
                'step': '0.01'
            }),
            # Novo Widget para Matrícula
            'enrollment_fee': forms.NumberInput(attrs={
                'class': 'w-full pl-4 pr-12 py-3 bg-emerald-50 border-2 border-emerald-200 rounded-2xl font-black text-emerald-700 focus:ring-4 focus:ring-emerald-500/20 transition text-lg',
                'step': '0.01',
                'placeholder': 'Valor da Matrícula'
            }),
            # NOVO CAMPO COM ESTILO SOTARQ
            'taxa_iva': forms.Select(attrs={
                'class': 'w-full p-3 bg-slate-50 border-2 border-slate-200 rounded-xl font-bold text-slate-700 focus:border-indigo-500 transition'
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filtra apenas taxas ativas para não escolher taxas obsoletas
        self.fields['taxa_iva'].queryset = self.fields['taxa_iva'].queryset.filter(ativo=True)
        self.fields['taxa_iva'].empty_label = "Selecione a Taxa (Ex: Isento M02)"


# O Coração da edição em massa:
# O Coração da edição em massa por percentagem:
GradeLevelFormSet = inlineformset_factory(
    Course, 
    GradeLevel, 
    fields=['name', 'level_index', 'fee_percentage_increase'], # Alterado para percentagem
    extra=0,
    can_delete=True,
    widgets={
        'name': forms.TextInput(attrs={'class': 'form-input text-xs rounded-lg border-slate-200', 'readonly': 'readonly'}),
        'fee_percentage_increase': forms.NumberInput(attrs={
            'class': 'form-input text-xs font-black text-indigo-600 rounded-lg border-indigo-200',
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
    class Meta:
        model = GradeLevel
        fields = ['name', 'course', 'level_index']
        
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none transition',
                'placeholder': 'Ex: 10ª Classe'
            }),
            'course': forms.Select(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none transition'
            }),
            'level_index': forms.NumberInput(attrs={
                'class': 'w-full px-4 py-3 rounded-xl border border-slate-200 dark:border-slate-700 dark:bg-slate-900 focus:ring-2 focus:ring-indigo-500 outline-none transition',
                'min': '1',
                'placeholder': '1'
            }),
        }

    def __init__(self, *args, **kwargs):
        # Capturamos a escola enviada pela View
        school = kwargs.pop('school', None)
        super().__init__(*args, **kwargs)
        
        if school:
            # FILTRO CRÍTICO: Garante que apenas cursos desta escola apareçam
            self.fields['course'].queryset = self.fields['course'].queryset.filter(school=school)



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



