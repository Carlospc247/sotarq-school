# apps/students/forms.py
from django import forms

from apps.core.models import User
from .models import EnrollmentRequest, Student
from apps.academic.models import Class, Course, GradeLevel
from django.core.validators import FileExtensionValidator
from django import forms
from .models import Student
from apps.academic.models import Course, GradeLevel, Class



class StudentImportForm(forms.Form):
    file = forms.FileField(
        label="Ficheiro Excel (.xlsx)",
        help_text="Selecione o ficheiro com a lista de alunos (Máx 1.500 linhas).",
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls'])]
    )




class ReconfirmationForm(forms.ModelForm):
    """Formulário simplificado para Reconfirmação (Requisito 2)."""
    class Meta:
        model = EnrollmentRequest
        fields = ['doc_bi', 'doc_health', 'doc_payment_proof']
        widgets = {
            'doc_bi': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100'}),
            'doc_health': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100'}),
            'doc_payment_proof': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-emerald-50 file:text-emerald-700 hover:file:bg-emerald-100'}),
        }





class StudentInternalForm(forms.ModelForm):
    # Campos Virtuais para Navegação AJAX
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(), 
        label="Curso", 
        required=True,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )
    
    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.all(), # Permitimos todos aqui para validação de POST, o AJAX filtra no front
        label="Classe", 
        required=True,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )

    email = forms.EmailField(required=True, label="Email do Aluno/Encarregado")
    photo_passport_file = forms.ImageField(required=False, label="Alterar Foto")

    class Meta:
        model = Student
        fields = ['full_name', 'birth_date', 'gender', 'current_class', 'bi_number']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'gender': forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'}),
            'current_class': forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'}),
            'bi_number': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Lógica de Edição: Preencher campos virtuais com dados do banco
        if self.instance and self.instance.pk:
            if self.instance.user:
                self.fields['email'].initial = self.instance.user.email
            
            # Bloqueio de BI para evitar fraude em edição (Rigor SOTARQ)
            self.fields['bi_number'].widget.attrs['readonly'] = True
            self.fields['bi_number'].widget.attrs['class'] += ' bg-slate-100 cursor-not-allowed'

            if self.instance.current_class:
                current_class = self.instance.current_class
                grade = current_class.grade_level
                course = grade.course

                self.fields['course'].initial = course.id
                self.fields['grade_level'].initial = grade.id
                
                # Restringir querysets para o que é válido para este aluno específico
                self.fields['grade_level'].queryset = GradeLevel.objects.filter(course=course)
                self.fields['current_class'].queryset = Class.objects.filter(grade_level=grade)

    def clean(self):
        cleaned_data = super().clean()
        grade_level = cleaned_data.get('grade_level')
        current_class = cleaned_data.get('current_class')

        # Validação Cruzada: A turma selecionada pertence à classe selecionada?
        if grade_level and current_class:
            if current_class.grade_level != grade_level:
                raise forms.ValidationError("A turma selecionada não pertence à classe escolhida.")
        
        return cleaned_data




class ReconfirmationAuthForm(forms.Form):
    # Formulário para validar aluno antes da reconfirmação presencial.
    student_id = forms.CharField(label="Nº Processo / ID", widget=forms.TextInput(attrs={'class': 'w-full p-3 border rounded-lg'}))
    birth_date = forms.DateField(label="Data de Nascimento", widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border rounded-lg'}))


