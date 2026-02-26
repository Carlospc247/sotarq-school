# apps/teachers/models.py
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel



class Teacher(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='teacher_profile')
    employee_number = models.CharField(max_length=20, unique=True)
    academic_degree = models.CharField(max_length=100, help_text="e.g. PhD, MSc, Licentiate")
    is_active = models.BooleanField(default=True)
    
    # --- NOVOS CAMPOS PARA RH / HISTÓRICO DE SAÍDA ---
    exit_date = models.DateField(null=True, blank=True, help_text="Data de desligamento")
    
    class ExitReason(models.TextChoices):
        RESIGNATION = 'RESIGNATION', 'Demissão Voluntária'
        TERMINATION = 'TERMINATION', 'Rescisão Contratual'
        DISMISSAL = 'DISMISSAL', 'Justa Causa (Expulsão)'
        REDUNDANCY = 'REDUNDANCY', 'Redução de Pessoal'
        RETIREMENT = 'RETIREMENT', 'Reforma'
        OTHER = 'OTHER', 'Outros'

    exit_reason = models.CharField(
        max_length=20, 
        choices=ExitReason.choices, 
        null=True, 
        blank=True,
        verbose_name="Motivo de Saída"
    )
    
    final_evaluation = models.TextField(
        null=True, 
        blank=True, 
        help_text="Avaliação final de desempenho ou notas do RH.",
        verbose_name="Avaliação / Obs."
    )

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_number})"



class TeacherSubject(models.Model):
    """
    Allocates a Teacher to a Subject in a specific Class (Turma).
    This defines 'Who teaches what to whom'.
    """
    teacher = models.ForeignKey(Teacher, on_delete=models.CASCADE, related_name='allocations')
    subject = models.ForeignKey('academic.Subject', on_delete=models.CASCADE, related_name='teacher_allocations')
    class_room = models.ForeignKey('academic.Class', on_delete=models.CASCADE, related_name='teacher_allocations', help_text="Turma")
    
    class Meta:
        unique_together = ('teacher', 'subject', 'class_room')
        verbose_name = "Teacher Allocation"

    def __str__(self):
        return f"{self.teacher} - {self.subject} ({self.class_room})"
