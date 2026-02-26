# apps/core/forms.py
from django import forms
from django.contrib.auth import get_user_model

from apps.teachers.models import Teacher
from .models import JobApplication, Role, SchoolConfiguration
from django.core.validators import FileExtensionValidator


User = get_user_model()

class UserManagementForm(forms.ModelForm):
    """
    Formulário Enterprise para Criação/Edição de Funcionários.
    """
    first_name = forms.CharField(required=True, label="Nome")
    last_name = forms.CharField(required=True, label="Sobrenome")
    email = forms.EmailField(required=True, label="E-mail Institucional")
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={'placeholder': 'Definir senha inicial'}),
        required=False, 
        help_text="Deixe em branco para manter a senha atual na edição."
    )
    
    # Filtra apenas Roles de Staff (exclui alunos/pais para segurança)
    current_role = forms.ChoiceField(
        choices=[
            (Role.Type.ADMIN, 'Administrador'),
            (Role.Type.DIRECTOR, 'Diretor'),
            (Role.Type.TEACHER, 'Professor'),
            (Role.Type.SECRETARY, 'Secretaria'),
        ],
        label="Perfil de Acesso"
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'email', 'current_role', 'is_active',
            'pode_acessar_academic_page', 'pode_ver_pautas_boletins', 
            'pode_ver_documentos_academics', 'pode_baixar_pautas', 'pode_baixar_boletins'
            ]

    def clean_email(self):
        # Validação Enterprise: Email único por Tenant ou Global
        email = self.cleaned_data.get('email')
        qs = User.objects.filter(email=email)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Este e-mail já está em uso no sistema.")
        return email





class UserImportForm(forms.Form):
    """
    Formulário para upload de arquivo Excel com validação de extensão.
    """
    file = forms.FileField(
        label="Ficheiro Excel (.xlsx)",
        help_text="O arquivo deve conter as colunas: username, first_name, last_name, email, role, employee_number, academic_degree",
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls'])]
    )





class SchoolSettingsForm(forms.ModelForm):
    # Campo auxiliar para passar o JSON de cards (AlpineJS -> Django)
    site_info_cards_json = forms.CharField(widget=forms.HiddenInput(), required=False)

    #break_exceptions = forms.ModelMultipleChoiceField(queryset=Teacher.objects.filter(is_active=True), required=False, widget=forms.CheckboxSelectMultiple(attrs={'class': 'grid grid-cols-2 gap-2 text-sm'}))

    class Meta:
        model = SchoolConfiguration
        fields = [
            # 1. Identidade e Cores do Sistema
            'school_name', 'logo', 'favicon', 'primary_color',
            'secondary_color', 'weight_mac', 'weight_npp', 'weight_npt',
            
            # 2. Personalização do Site Institucional (Cores e Layout)
            'site_header_bg', 'site_header_text', 'site_footer_bg', 'site_footer_text',
            'site_info_cards', 'hero_mode', 'hero_title', 'hero_subtitle', 
            'hero_image_1', 'hero_image_2', 'hero_image_3',
            'news_ticker', 'custom_html_content',
            
            # 4. Contactos e Redes
            'phone_contact', 'official_email', 'address', 'website_link',
            'facebook_link', 'instagram_link', 'linkedin_link',
            
            # 5. Calendário Académico e Permissões (Matrículas/Reconfirmações)
            'is_enrollment_open', 'enrollment_start_date', 'enrollment_end_date',
            'is_reconfirmation_open', 'reconfirmation_start_date', 'reconfirmation_end_date',
            
            # 6. Permissões de Exportação
            'allow_secretary_export', 'allow_secretary_import', 'allow_teacher_export',
        ]
        
        widgets = {
            # --- WIDGETS VISUAIS (Color Pickers) ---
            'primary_color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 p-1 rounded cursor-pointer border border-slate-300'}),
            'secondary_color': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-20 p-1 rounded cursor-pointer border border-slate-300'}),
            'site_header_bg': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-full p-1 rounded cursor-pointer border border-slate-300'}),
            'site_header_text': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-full p-1 rounded cursor-pointer border border-slate-300'}),
            'site_footer_bg': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-full p-1 rounded cursor-pointer border border-slate-300'}),
            'site_footer_text': forms.TextInput(attrs={'type': 'color', 'class': 'h-10 w-full p-1 rounded cursor-pointer border border-slate-300'}),

            # --- WIDGETS DE CALENDÁRIO (Date Pickers) ---
            'enrollment_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'enrollment_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'reconfirmation_start_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'reconfirmation_end_date': forms.DateInput(attrs={'type': 'date', 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),

            # --- WIDGETS DE TEXTO E ÁREA ---
            'address': forms.Textarea(attrs={'rows': 3, 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'hero_subtitle': forms.Textarea(attrs={'rows': 2, 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'custom_html_content': forms.Textarea(attrs={'rows': 5, 'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm font-mono', 'placeholder': '<div>Código HTML ou Embed aqui...</div>'}),
            
            # --- INPUTS PADRÃO (Tailwind Styled) ---
            'school_name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'iban_primary': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'bank_name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'hero_title': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'news_ticker': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'phone_contact': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'official_email': forms.EmailInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'website_link': forms.URLInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'facebook_link': forms.URLInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'instagram_link': forms.URLInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'linkedin_link': forms.URLInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            
            # Selects
            'hero_mode': forms.Select(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'}),
        }

    def clean(self):
        cleaned_data = super().clean()
        
        # Validação de Datas (Fim não pode ser antes do Início)
        e_start = cleaned_data.get('enrollment_start_date')
        e_end = cleaned_data.get('enrollment_end_date')
        if e_start and e_end and e_end < e_start:
            self.add_error('enrollment_end_date', "A data de fim deve ser posterior à data de início.")

        r_start = cleaned_data.get('reconfirmation_start_date')
        r_end = cleaned_data.get('reconfirmation_end_date')
        if r_start and r_end and r_end < r_start:
            self.add_error('reconfirmation_end_date', "A data de fim deve ser posterior à data de início.")

        return cleaned_data


class PublicVerificationForm(forms.Form):
    verification_code = forms.CharField(
        label="Código de Verificação",
        widget=forms.TextInput(attrs={
            'class': 'w-full p-4 border-2 border-slate-200 rounded-xl text-lg font-mono text-center tracking-widest focus:border-brand-500 focus:ring-0 uppercase',
            'placeholder': 'EX: 2010-01-01#2024001#999'
        }),
        help_text="Insira o código hash fornecido no documento ou cartão."
    )

    


class JobApplicationForm(forms.ModelForm):
    area_selection = forms.ChoiceField(choices=[], required=False, label="Área de Interesse")

    # Esta linha já define o widget, as classes e o required=False. É a Mestra.
    applied_area = forms.CharField(
        required=False, 
        widget=forms.TextInput(attrs={
            'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm', 
            'placeholder': 'Especifique a área caso tenha selecionado "Outra"'
        })
    )
    
    class Meta:
        model = JobApplication
        fields = ['full_name', 'email', 'phone', 'area_selection', 'applied_area', 'cv_file', 'bi_file', 'academic_cert']
        widgets = {
            'full_name': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'email': forms.EmailInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'phone': forms.TextInput(attrs={'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm'}),
            'cv_file': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100'}),
            'bi_file': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-slate-50 file:text-slate-700 hover:file:bg-slate-100'}),
            'academic_cert': forms.FileInput(attrs={'class': 'block w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-xs file:font-semibold file:bg-slate-50 file:text-slate-700 hover:file:bg-slate-100'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        config = SchoolConfiguration.objects.first()
        choices = []
        
        if config and config.available_job_areas:
            areas_list = [area.strip() for area in config.available_job_areas.split(',') if area.strip()]
            choices = [(area, area) for area in areas_list]
        
        choices.append(('Custom', 'Outra (Especificar)'))
        self.fields['area_selection'].choices = choices
        self.fields['area_selection'].widget.attrs.update({'class': 'w-full p-3 border border-slate-300 rounded-lg text-sm bg-white'})




