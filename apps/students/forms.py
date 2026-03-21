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


from django import forms
from .models import Student, StudentGuardian
from apps.academic.models import Course, GradeLevel, Class

class StudentInternalForm(forms.ModelForm):
    # --- CAMPOS DO ALUNO (EXTRAS) ---
    course = forms.ModelChoiceField(
        queryset=Course.objects.none(),
        label="Curso", 
        required=True,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )
    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.none(),
        label="Classe", 
        required=True,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )
    email = forms.EmailField(
        required=True, 
        label="Email do Aluno (Login)",
        widget=forms.EmailInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'})
    )

    # --- CAMPOS DO ENCARREGADO (PARA A VIEW) ---
    guardian_name = forms.CharField(
        max_length=255, required=True, label="Nome do Encarregado",
        widget=forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm', 'placeholder': 'Nome completo'})
    )
    guardian_phone = forms.CharField(
        max_length=20, required=True, label="Telefone do Encarregado",
        widget=forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'})
    )
    guardian_email = forms.EmailField(
        required=True, label="Email do Encarregado",
        widget=forms.EmailInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'})
    )
    relationship = forms.ChoiceField(
        choices=StudentGuardian.RELATIONSHIP_CHOICES,
        label="Parentesco",
        required=True,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )

    # --- DOCUMENTOS ---
    doc_bi_file = forms.FileField(required=True, label="Cópia do BI")
    doc_health_file = forms.FileField(required=False, label="Atestado Médico")
    doc_certificate_file = forms.FileField(required=False, label="Certificado")
    photo_passport_file = forms.ImageField(required=False, label="Foto Passe")

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
        self.tenant = kwargs.pop('tenant', None) 
        super().__init__(*args, **kwargs)
        
        # Filtros de Queryset
        self.fields['course'].queryset = Course.objects.all()
        self.fields['grade_level'].queryset = GradeLevel.objects.all()
        self.fields['current_class'].queryset = Class.objects.none()

        # Lógica de encadeamento (Classe dependendo do Nível)
        if 'grade_level' in self.data:
            try:
                gl_id = int(self.data.get('grade_level'))
                self.fields['current_class'].queryset = Class.objects.filter(grade_level_id=gl_id)
            except (ValueError, TypeError):
                pass
        
        # Lógica para Edição
        if self.instance and self.instance.pk:
            if self.instance.user:
                self.fields['email'].initial = self.instance.user.email
            
            # Travar BI na edição para evitar fraude
            self.fields['bi_number'].widget.attrs['readonly'] = True
            self.fields['bi_number'].widget.attrs['class'] += ' bg-slate-100 cursor-not-allowed'

            if self.instance.current_class:
                self.fields['current_class'].queryset = Class.objects.filter(
                    grade_level=self.instance.current_class.grade_level
                )



class ReconfirmationAuthForm(forms.Form):
    # Formulário para validar aluno antes da reconfirmação presencial.
    student_id = forms.CharField(label="Nº Processo / ID", widget=forms.TextInput(attrs={'class': 'w-full p-3 border rounded-lg'}))
    birth_date = forms.DateField(label="Data de Nascimento", widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border rounded-lg'}))


