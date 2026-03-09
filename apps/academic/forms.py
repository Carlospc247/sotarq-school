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



class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = ['name', 'code', 'level', 'duration_years', 'coordinator']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control rounded-xl border-slate-200 focus:border-indigo-500',
                'placeholder': 'Ex: Informática de Gestão'
            }),
            'code': forms.TextInput(attrs={
                'class': 'form-control rounded-xl border-slate-200 font-mono uppercase',
                'placeholder': 'INF-GEST'
            }),
            'level': forms.Select(attrs={'class': 'form-select rounded-xl border-slate-200'}),
            'duration_years': forms.NumberInput(attrs={'class': 'form-control rounded-xl border-slate-200', 'min': '1'}),
            'coordinator': forms.Select(attrs={'class': 'form-select rounded-xl border-slate-200'}),
        }

    def clean_code(self):
        code = self.cleaned_data.get('code').upper()
        # Validação de unicidade no Rigor SOTARQ
        if Course.objects.filter(code=code).exists():
            raise forms.ValidationError("Este código de curso já está em uso.")
        return code



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

#    def clean_capacity(self):
#        capacity = self.cleaned_data.get('capacity')
#        if capacity < 5:
#            raise forms.ValidationError("A capacidade mínima permitida é de 5 alunos.")
#        if capacity > 60:
#             raise forms.ValidationError("Alerta: Capacidade acima de 60 alunos viola as normas de conforto SOTARQ.")
#        return capacity

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



