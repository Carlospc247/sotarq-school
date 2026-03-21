# apps/core/models.py
from django.contrib.auth.models import AbstractUser, Permission
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from django.conf import settings
from cloudinary.models import CloudinaryField


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)

class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # For when we need to see deleted items

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        self.deleted_at = timezone.now()
        self.save()

    def hard_delete(self):
        super().delete()




class Role(models.Model):
    """
    Dynamic Roles for the Tenant.
    """
    class Type(models.TextChoices):
        ADMIN = 'ADMIN', 'Admin'
        DIRECTOR = 'DIRECTOR', 'Diretor Geral'
        PEDAGOGIC = 'PEDAGOGIC', 'Diretor Pedagógico'
        DIRECT_ADMIN = 'DIRECT_ADMIN', 'Dr. Administrativo'
        DIRECT_FINANC = 'DIRECT_FINANC', 'Dr. Financeiro'
        TEACHER = 'TEACHER', 'Professor'
        STUDENT = 'STUDENT', 'Aluno'
        GUARDIAN = 'GUARDIAN', 'Encarregado'
        SECRETARY = 'SECRETARY', 'Secretaria'
        VIGILANT = 'VIGILANT', 'Vigilante'
        
        # --- NOVOS ROLES (Especialistas) ---
        ACCOUNTANT = 'ACCOUNTANT', 'Contabilista'
        RH = 'RH', 'Recursos Humanos'
        
        CUSTOM = 'CUSTOM', 'Customizado'

    name = models.CharField(max_length=50)
    code = models.CharField(max_length=50, choices=Type.choices, default=Type.CUSTOM)
    description = models.TextField(blank=True)
    permissions = models.ManyToManyField(Permission, blank=True)
    is_system_role = models.BooleanField(default=False, help_text="System roles cannot be deleted.")

    def __str__(self):
        return self.name


class User(AbstractUser):
    # Retain the simple role field for quick access/legacy support, 
    # but the source of truth for permissions should be the M2M Role.
    # We can default this to the 'primary' role.
    current_role = models.CharField(max_length=20, choices=Role.Type.choices, default=Role.Type.ADMIN)
    roles = models.ManyToManyField(Role, through='UserRole', related_name='users')
    tenant = models.ForeignKey(
        'customers.Client', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True, 
        related_name='users',
        verbose_name="Escola/Instituição"
    )

    # PERMISSÕES ACADÊMICAS (Delegadas pelo Diretor)
    pode_acessar_academic_page = models.BooleanField(default=False)
    pode_ver_pautas_boletins = models.BooleanField(default=False)
    pode_ver_documentos_academics = models.BooleanField(default=False)
    pode_baixar_pautas = models.BooleanField(default=False)
    pode_baixar_boletins = models.BooleanField(default=False)

    def __str__(self):
        return self.username
        
    def has_role(self, role_code):
        return self.roles.filter(code=role_code).exists()
    
    @property
    def is_manager(self):
        """
        Retorna True se o usuário tiver poder de gestão (Admin ou Diretor).
        Útil para templates e permissões.
        """
        MANAGEMENT_ROLES = [Role.Type.ADMIN, Role.Type.DIRECTOR]
        return self.is_superuser or self.current_role in MANAGEMENT_ROLES
    

class UserRole(models.Model):
    """
    Explicit M2M link between User and Role.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    role = models.ForeignKey(Role, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ('user', 'role')

    def __str__(self):
        return f"{self.user} - {self.role}"


class SupportTicket(BaseModel):
    class Status(models.TextChoices):
        OPEN = 'open', 'Aberto'
        IN_PROGRESS = 'in_progress', 'Em Atendimento'
        CLOSED = 'closed', 'Resolvido'

    subject = models.CharField(max_length=200)
    message = models.TextField()
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    
    # Notificação automática ao criar
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            # Dispara Task do Celery para avisar você (admin)
            task_notify_admin_new_ticket.delay(self.id)
            # usar pass se não tiver nenhum argumento
            pass

    def __str__(self):
        return f"{self.subject} - {self.user.username}"


class HelpArticle(BaseModel):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=[
        ('FINANCE', 'Finanças'),
        ('ACADEMIC', 'Académico'),
        ('SETUP', 'Configuração Inicial')
    ])
    content = models.TextField() # Aceita HTML para os manuais
    icon = models.CharField(max_length=50, default='fa-question-circle')

    def __str__(self):
        return self.title


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='core_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    link = models.CharField(max_length=255, blank=True, null=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} - {self.user.username}"


class SchoolMessage(BaseModel):
    class Category(models.TextChoices):
        COMPLIMENT = 'COMPLIMENT', 'Elogio'
        INCIDENT = 'INCIDENT', 'Ocorrência Disciplinar'
        ACADEMIC = 'ACADEMIC', 'Alerta Académico'
        GENERAL = 'GENERAL', 'Informativo Geral'

    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='sent_messages')
    receiver = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='received_messages')
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, db_constraint=False, related_name='communication_history')
    
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.GENERAL)
    subject = models.CharField(max_length=200)
    content = models.TextField()

    
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_category_display()} - {self.student.full_name}"


class SchoolConfiguration(BaseModel):
    """
    Configurações de Branding, Identidade, Website e Regras de Negócio da Escola (Tenant).
    """
    # --- Identidade ---
    school_name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=20, verbose_name="NIF/Contribuinte")
    logo = CloudinaryField('logo', blank=True, null=True)
    favicon = CloudinaryField('favicon', blank=True, null=True)

    # --- Configurações de Avaliação (Pesos das Notas) ---
    weight_mac = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, help_text="Peso da Média de Avaliação Contínua")
    weight_npp = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, help_text="Peso da Nota de Prova Parcial")
    weight_npt = models.DecimalField(max_digits=3, decimal_places=2, default=1.0, help_text="Peso da Nota de Prova Trimestral/Final")
    

    class Quarter(models.IntegerChoices):
        FIRST = 1, "1º Trimestre"
        SECOND = 2, "2º Trimestre"
        THIRD = 3, "3º Trimestre"

    current_quarter = models.IntegerField(
        choices=Quarter.choices, 
        default=Quarter.FIRST,
        verbose_name="Trimestre Ativo"
    )

    # --- Cores Institucionais ---
    primary_color = models.CharField(max_length=7, default="#4f46e5", help_text="Cor principal")
    secondary_color = models.CharField(max_length=7, default="#1e293b", help_text="Cor secundária")
    
    # --- Personalização Avançada do Site ---
    site_header_bg = models.CharField(max_length=7, default="#FFFFFF", verbose_name="Fundo do Cabeçalho")
    site_header_text = models.CharField(max_length=7, default="#1e293b", verbose_name="Texto do Cabeçalho")
    site_footer_bg = models.CharField(max_length=7, default="#FFFFFF", verbose_name="Fundo do Rodapé")
    site_footer_text = models.CharField(max_length=7, default="#64748b", verbose_name="Texto do Rodapé")
    
    site_info_cards = models.JSONField(default=list, blank=True, verbose_name="Cards Informativos")

    # --- Finanças & Legal ---
    official_email = models.EmailField()
    phone_contact = models.CharField(max_length=20)
    address = models.TextField()

    # Configurações de Recrutamento
    is_recruitment_open = models.BooleanField(
        default=False, 
        verbose_name="Recrutamento Aberto"
    )
    
    available_job_areas = models.TextField(
        blank=True, 
        default="",
        help_text="Separe as áreas disponíveis por vírgula."
    )

    # --- 7. PERMISSÕES ESPECÍFICAS (DELEGAÇÃO DE PODER) ---
    # Quem pode editar dados do aluno (além de Admin/Diretor)?
    allow_secretary_edit_student = models.BooleanField(
        default=False, 
        verbose_name="Permitir Secretaria Editar Alunos"
    )
    
    # Quem pode ver a Ficha Técnica Completa?
    allow_teacher_view_full_file = models.BooleanField(
        default=False, 
        verbose_name="Permitir Professor ver Ficha Completa"
    )

    # Quem pode ver o Extrato Financeiro (além de Finanças/Admin)?
    allow_secretary_view_finance = models.BooleanField(
        default=False, 
        verbose_name="Permitir Secretaria ver Financeiro"
    )
    
    # Nota: Admin, Diretor e Dr. Financeiro têm acesso nativo hardcoded.

    # --- Redes Sociais ---
    website_link = models.URLField(blank=True, null=True)
    facebook_link = models.URLField(blank=True, null=True)
    instagram_link = models.URLField(blank=True, null=True)
    linkedin_link = models.URLField(blank=True, null=True)

    # --- Gestão de Conteúdo ---
    news_ticker = models.CharField(max_length=255, blank=True, verbose_name="Novidades (Ticker)")
    custom_html_content = models.TextField(blank=True, verbose_name="Conteúdo Estático/HTML")

    class HeroMode(models.TextChoices):
        CAROUSEL = 'CAROUSEL', 'Modo Carrossel (3 Slides)'
        SINGLE_IMAGE = 'SINGLE', 'Imagem Única (Hero)'
        MINIMAL = 'MINIMAL', 'Sem Imagem (Minimalista)'

    hero_mode = models.CharField(max_length=10, choices=HeroMode.choices, default=HeroMode.SINGLE_IMAGE)
    hero_title = models.CharField(max_length=100, default="Educação de Excelência")
    hero_subtitle = models.TextField(default="Preparando líderes para o futuro.")
    hero_image_1 = CloudinaryField('hero_image_1', blank=True, null=True)
    hero_image_2 = CloudinaryField('hero_image_2', blank=True, null=True)
    hero_image_3 = CloudinaryField('hero_image_3', blank=True, null=True)

    # --- CONTROLE DE CALENDÁRIO ACADÉMICO (Requisito 4) ---
    
    # 1. Matrículas (Novos Alunos)
    is_enrollment_open = models.BooleanField(
        default=True, 
        verbose_name="Matrículas Abertas (Manual)",
        help_text="Chave geral. Se desligado, ninguém se matricula."
    )
    enrollment_start_date = models.DateField(null=True, blank=True, verbose_name="Início das Matrículas")
    enrollment_end_date = models.DateField(null=True, blank=True, verbose_name="Fim das Matrículas")

    # 2. Reconfirmações (Alunos Antigos) - REQUISITO 1
    is_reconfirmation_open = models.BooleanField(
        default=False, 
        verbose_name="Reconfirmações Abertas (Manual)",
        help_text="Chave geral para alunos antigos."
    )
    reconfirmation_start_date = models.DateField(null=True, blank=True, verbose_name="Início das Reconfirmações")
    reconfirmation_end_date = models.DateField(null=True, blank=True, verbose_name="Fim das Reconfirmações")

    # --- Permissões de Operação ---
    allow_secretary_export = models.BooleanField(default=False)
    allow_secretary_import = models.BooleanField(default=False)
    allow_teacher_export = models.BooleanField(default=False)

    def __str__(self):
        return f"Configuração: {self.school_name}"
    
    def check_enrollment_window(self):
        """Verifica se hoje está dentro do prazo de NOVAS matrículas."""
        if not self.is_enrollment_open: return False
        today = timezone.now().date()
        if self.enrollment_start_date and today < self.enrollment_start_date: return False
        if self.enrollment_end_date and today > self.enrollment_end_date: return False
        return True

    def check_reconfirmation_window(self):
        """Verifica se hoje está dentro do prazo de RECONFIRMAÇÕES."""
        if not self.is_reconfirmation_open: return False
        today = timezone.now().date()
        if self.reconfirmation_start_date and today < self.reconfirmation_start_date: return False
        if self.reconfirmation_end_date and today > self.reconfirmation_end_date: return False
        return True



class JobApplication(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Pendente'
        INTERVIEW = 'INTERVIEW', 'Entrevista Agendada'
        HIRED = 'HIRED', 'Admitido / Contratado'
        REJECTED = 'REJECTED', 'Não Selecionado'

    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    
    # A área será validada no formulário com base na configuração
    applied_area = models.CharField(max_length=100)
    
    # Arquivos Obrigatórios
    cv_file = models.FileField(upload_to='recruitment/cvs/%Y/', verbose_name="Curriculum Vitae")
    
    # Arquivos Opcionais (Podem ser pedidos depois)
    bi_file = models.FileField(upload_to='recruitment/docs/%Y/', verbose_name="Bilhete de Identidade", null=True, blank=True)
    academic_cert = models.FileField(upload_to='recruitment/docs/%Y/', verbose_name="Certificado Literário", null=True, blank=True)
    
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    notes = models.TextField(blank=True, verbose_name="Notas Internas")

    def __str__(self):
        return f"{self.full_name} - {self.applied_area}"




