# apps/academic/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import StudentGrade
from apps.portal.services import NotificationService






@receiver(post_save, sender=StudentGrade)
def notify_grade_release(sender, instance, created, **kwargs):
    """Notifica o aluno quando uma nota é lançada ou alterada."""
    try:
        user = instance.student.user
        subject_name = instance.subject.name
        
        NotificationService.notify(
            user=user,
            title="Nova Nota Lançada 📝",
            message=f"A tua nota de {subject_name} já está disponível no boletim."
        )
    except Exception:
        pass # Evita que um erro na notificação trave o salvamento da nota

