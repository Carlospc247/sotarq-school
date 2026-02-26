# apps/students/forms.py
from django import forms

from apps.core.models import User
from .models import EnrollmentRequest, Student
from apps.academic.models import Class, Course, GradeLevel
from django.core.validators import FileExtensionValidator


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
    
    # Formulário para Matrícula Presencial (Uso exclusivo da Secretaria/Direção).
    
    # Campos do User
    email = forms.EmailField(required=True, label="Email do Aluno/Encarregado")
    
    # Campo BI (Texto) - Adicionado conforme pedido
    bi_number = forms.CharField(
        required=True, 
        label="Número do BI",
        widget=forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm', 'placeholder': 'Ex: 004728123LA042'})
    )

    # Campos Académicos
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(), 
        label="Curso", 
        required=True,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )
    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.all(), 
        label="Classe", 
        required=True,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )

    # Uploads (Campos não vinculados diretamente ao Student model neste form, processados na view)
    # BI é obrigatório conforme instrução ("EXCEPTO O BI")
    doc_bi_file = forms.FileField(
        required=True, 
        label="Cópia do BI (PDF/IMG)",
        widget=forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'})
    )
    # Outros opcionais na presencial
    doc_health_file = forms.FileField(
        required=False, 
        label="Atestado Médico",
        widget=forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'})
    )
    doc_certificate_file = forms.FileField(
        required=False, 
        label="Certificado/Declaração",
        widget=forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'})
    )
    photo_passport_file = forms.FileField(
        required=False, 
        label="Foto Tipo Passe",
        widget=forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'})
    )


    # NOVOS CAMPOS PARA EDIÇÃO
    course = forms.ModelChoiceField(
        queryset=Course.objects.all(), 
        label="Curso", 
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )
    grade_level = forms.ModelChoiceField(
        queryset=GradeLevel.objects.all(), 
        label="Classe", 
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )
    current_class = forms.ModelChoiceField(
        queryset=Class.objects.all(), 
        label="Turma", 
        required=False,
        widget=forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})
    )
    
    # Duração (Geralmente é um atributo do Curso, mas se quiser editar manualmente:)
    duration = forms.IntegerField(
        label="Duração (Anos)", 
        required=False,
        widget=forms.NumberInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'})
    )

    class Meta:
        model = Student
        fields = ['full_name', 'birth_date', 'gender', 'current_class']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'birth_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'gender': forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'}),
        }

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("Este email já está registado no sistema.")
        return email
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # SE ESTIVERMOS A EDITAR (instance existe e tem PK)
        if self.instance and self.instance.pk:
            # Se já tem turma, preenchemos o curso e a classe baseando-se nela
            if self.instance.current_class:
                self.fields['course'].initial = self.instance.current_class.grade_level.course
                self.fields['grade_level'].initial = self.instance.current_class.grade_level
            
            # Trava o BI como você solicitou anteriormente
            self.fields['bi_number'].widget.attrs['readonly'] = True
            self.fields['bi_number'].widget.attrs['class'] += ' bg-slate-100 text-slate-500 cursor-not-allowed'
            self.fields['bi_number'].help_text = "O Número do BI é único e não pode ser alterado."





class ReconfirmationAuthForm(forms.Form):
    # Formulário para validar aluno antes da reconfirmação presencial.
    student_id = forms.CharField(label="Nº Processo / ID", widget=forms.TextInput(attrs={'class': 'w-full p-3 border rounded-lg'}))
    birth_date = forms.DateField(label="Data de Nascimento", widget=forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border rounded-lg'}))
