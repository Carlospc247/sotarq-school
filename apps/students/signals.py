from datetime import timedelta

from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.students.models import Enrollment

@receiver(post_save, sender=Enrollment)
def sync_student_class(sender, instance, created, **kwargs):
    """
    Rigor SOTARQ: Garante que o Student.current_class 
    esteja SEMPRE sincronizado com a matrícula ativa.
    """
    student = instance.student
    
    if instance.status == 'active':
        # Se a matrícula está ativa, o aluno herda a turma
        if student.current_class != instance.class_room:
            student.current_class = instance.class_room
            student.save(update_fields=['current_class'])
    
    elif instance.status in ['cancelled', 'graduated', 'suspended']:
        # Se não há mais matrícula ativa, limpamos a turma
        # (Opcional: verificar se existe outra matrícula ativa antes de limpar)
        if not student.enrollments.filter(status='active').exists():
            student.current_class = None
            student.save(update_fields=['current_class'])


import logging
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from .models import Enrollment
from apps.finance.models import Invoice, FeeType, InvoiceItem

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Enrollment)
def handle_new_enrollment_finance(sender, instance, created, **kwargs):
    if created:
        student = instance.student
        course = instance.grade_level.course
        
        # Rigor SOTARQ: Buscamos o FeeType que o Chefe configurou no Curso
        fee_type = course.default_enrollment_fee_type
        
        if not fee_type:
            logger.error(f"❌ Falha Financeira: O curso {course.name} não tem um FeeType de matrícula definido!")
            return

        try:
            with transaction.atomic():
                # Sincroniza Turma
                student.current_class = instance.class_room
                student.save(update_fields=['current_class'])

                # Cria a Fatura usando o FeeType oficial
                if not Invoice.objects.filter(student=student, fee_type=fee_type).exists():
                    invoice = Invoice.objects.create(
                        student=student,
                        status='pending',
                        tax_type=course.taxa_iva, # IVA vem do Curso
                        due_date=timezone.now().date() + timedelta(days=5)
                    )
                    
                    # Cria o item da fatura com o valor do catálogo
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        fee_type=fee_type,
                        description=fee_type.name,
                        amount=fee_type.amount
                    )
                    
                    # Motor de cálculo AGT
                    invoice.update_totals() 
                    
        except Exception as e:
            logger.error(f"❌ Erro ao processar financeiro de matrícula: {e}")
            