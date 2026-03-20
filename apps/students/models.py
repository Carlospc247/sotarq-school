# apps/students/models.py
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel
from django.db import connection
from apps.academic.models import Course, GradeLevel, Class
from django.utils import timezone
from django.db.models import Max
from django.db.models.signals import pre_save
from django.dispatch import receiver




class Student(BaseModel):
    class Gender(models.TextChoices):
        MALE = 'M', _('Masculino')
        FEMALE = 'F', _('Feminino')

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='student_profile')
    bi_number = models.CharField(max_length=20, unique=True, verbose_name="Número do BI", null=True, blank=True)
    registration_number = models.CharField(max_length=20, unique=True, editable=False)
    full_name = models.CharField(max_length=255, help_text="Official Full Name")
    birth_date = models.DateField()
    gender = models.CharField(max_length=1, choices=Gender.choices)
    is_suspended = models.BooleanField(default=False, help_text="Bloqueia acesso por falta de pagamento")
    
    # Denormalization or Current Status:
    current_class = models.ForeignKey('academic.Class', on_delete=models.SET_NULL, null=True, blank=True, related_name='current_students')
    is_active = models.BooleanField(default=True)

    merit_points = models.IntegerField(default=0, verbose_name="Pontos de Mérito Académico")
    
    is_suspended = models.BooleanField(default=False, help_text="Bloqueia acesso por falta de pagamento")
    
    # ADIÇÃO DE RIGOR PARA FRAUDE:
    is_blocked_for_fraud = models.BooleanField(default=False, verbose_name="Bloqueio de Segurança (Fraude)")
    fraud_lock_details = models.TextField(null=True, blank=True, verbose_name="Detalhes da Infração Técnica")

    # Audit & Security
    last_modified_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='modified_students')



    def save(self, *args, **kwargs):
        # 1. GERAÇÃO AUTOMÁTICA DE ID (Requisito 2)
        if not self.registration_number:
            current_year = timezone.now().year
            # Formato sugerido: ANO + SEQUÊNCIA (ex: 20260001)
            prefix = f"{current_year}"
            
            # Filtra alunos cujo ID começa com o ano atual para pegar o último
            last_student = Student.objects.filter(
                registration_number__startswith=prefix
            ).aggregate(largest=Max('registration_number'))['largest']

            if last_student:
                try:
                    # Extrai a sequência numérica (assumindo formato fixo)
                    sequence = int(last_student[4:]) + 1
                except ValueError:
                    # Fallback caso haja dados legados com formato diferente
                    sequence = 1
            else:
                sequence = 1

            self.registration_number = f"{prefix}{sequence:04d}"

        # 2. VERIFICAÇÃO DE LICENÇA (Código original mantido)
        if not self.pk:
            try:
                tenant = connection.tenant
                if tenant.schema_name != 'public':
                    if hasattr(tenant, 'license'):
                        current_count = Student.objects.count()
                        # Nota: Ajustei 'academic.max_students' baseando-se no padrão comum de tenants
                        is_allowed = tenant.license.check_limit('academic.max_students', current_count)
                        if not is_allowed:
                            from django.core.exceptions import ValidationError
                            raise ValidationError("License Limit Reached.")
            except AttributeError:
                pass

        super().save(*args, **kwargs)    

    def __str__(self):
        return f"{self.full_name} ({self.registration_number})"



class Guardian(BaseModel):
    full_name = models.CharField(max_length=255)
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    
    # Optional: Link to a User if guardians have login access
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='guardian_profile')

    def __str__(self):
        return self.full_name

class StudentGuardian(BaseModel):
    RELATIONSHIP_CHOICES = (
        ('father', _('Pai')),
        ('mother', _('Mãe')),
        ('uncle', _('Tio')),
        ('aunt', _('Tia')),
        ('grandparent', _('Avó/Avô')),
        ('other', _('Outros')),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='guardians')
    guardian = models.ForeignKey(Guardian, on_delete=models.CASCADE, related_name='students')
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    is_financial_responsible = models.BooleanField(default=False)

    class Meta:
        unique_together = ('student', 'guardian')

    def __str__(self):
        return f"{self.guardian} -> {self.student} ({self.relationship})"



class Enrollment(BaseModel):
    """
    Official Enrollment Record (Matrícula).
    """
    STATUS_CHOICES = (
        ('active', _('Ativo')),
        ('pending_placement', _('Aguardando Colocação')), # NOVO STATUS
        ('transferred', _('Transferido')),
        ('dropout', _('Desistente')),
        ('graduated', _('Graduado')),
        ('failed', _('Reprovado')),
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollments')
    academic_year = models.ForeignKey('academic.AcademicYear', on_delete=models.PROTECT)
    course = models.ForeignKey('academic.Course', on_delete=models.PROTECT)
    
    # ALTERAÇÃO TÉCNICA: null=True para permitir matrícula paga sem turma definida (aguardando Diretor)
    class_room = models.ForeignKey(
        'academic.Class', 
        on_delete=models.PROTECT, 
        related_name='enrollments_records', 
        help_text="Turma",
        null=True, 
        blank=True
    )
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    date_enrolled = models.DateField(auto_now_add=True)
    order_number = models.PositiveIntegerField(default=1, help_text="Número de ordem na pauta")

    def check_global_attendance_status(self):
        """
        Varre todas as notas do aluno no ano atual. 
        Se houver uma única retenção por faltas, o aluno perde o ano (Art. 25º).
        """
        has_failure = self.student.academic_grades.filter(
            klass=self.class_room, 
            is_failed_by_attendance=True
        ).exists()
        
        if has_failure:
            self.status = 'failed'
            self.save()
            return True
        return False
        
    def __str__(self):
        return f"{self.student} - {self.academic_year} ({self.status})"



class EnrollmentRequest(BaseModel):
    class RequestType(models.TextChoices):
        NEW = 'NEW', 'Nova Matrícula'
        RECONFIRMATION = 'RECONFIRMATION', 'Reconfirmação'

    request_type = models.CharField(
        max_length=20, 
        choices=RequestType.choices, 
        default=RequestType.NEW,
        verbose_name="Tipo de Solicitação"
    )

    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='enrollment_requests')
    
    course = models.ForeignKey('academic.Course', on_delete=models.SET_NULL, null=True)
    grade_level = models.ForeignKey('academic.GradeLevel', on_delete=models.SET_NULL, null=True)
    
    guardian_name = models.CharField(max_length=255, blank=True)
    guardian_phone = models.CharField(max_length=50, blank=True)
    guardian_email = models.EmailField(blank=True, null=True)
    
    doc_bi = models.FileField(upload_to='candidates/bi/', blank=True, null=True)
    doc_health = models.FileField(upload_to='candidates/health/', blank=True, null=True)
    
    # Campo específico para Reconfirmação (Upload direto do comprovativo)
    doc_payment_proof = models.FileField(
        upload_to='candidates/payments/%Y/', 
        verbose_name="Comprovativo de Pagamento",
        null=True, blank=True
    )
    
    doc_certificate = models.FileField(upload_to='candidates/certificates/%Y/', null=True, blank=True)
    photo_passport = models.ImageField(upload_to='candidates/photos/%Y/', null=True, blank=True)

    has_special_needs = models.BooleanField(default=False)
    observations = models.TextField(blank=True, null=True)
    
    invoice = models.OneToOneField('finance.Invoice', on_delete=models.SET_NULL, null=True, blank=True)
    
    status = models.CharField(max_length=20, default='pending', choices=[
        ('pending', 'Pendente Análise'),
        ('paid', 'Pago / Em Processamento'),
        ('approved', 'Confirmado'),
        ('rejected', 'Rejeitado')
    ])

    def __str__(self):
        return f"{self.get_request_type_display()}: {self.student.full_name} ({self.grade_level})"








@receiver(pre_save, sender=Student)
def audit_student_changes(sender, instance, **kwargs):
    if not instance.pk:
        return  # Aluno novo, não há o que auditar de "mudança"

    try:
        old_obj = Student.objects.get(pk=instance.pk)
    except Student.DoesNotExist:
        return

    # Mapeamento de campos críticos para auditar
    fields_to_audit = {
        'current_class': 'Turma/Curso',
        'is_suspended': 'Status de Suspensão',
        'full_name': 'Nome Completo'
    }

    for field, label in fields_to_audit.items():
        old_value = getattr(old_obj, field)
        new_value = getattr(instance, field)

        if old_value != new_value:
            # Criar o log de auditoria
            from apps.academic.models import StudentAuditLog # Import local para evitar circular
            StudentAuditLog.objects.create(
                student=instance,
                changed_by=instance.last_modified_by, # Preenchido na View de edição
                field_changed=label,
                old_value=str(old_value) if old_value else "Vazio",
                new_value=str(new_value) if new_value else "Vazio"
            )