from datetime import timedelta

from celery import shared_task
from apps.core.services import WhatsAppService
from apps.library.models import LibraryConfig

@shared_task
def task_notify_return_reminder():
    """Roda 24h antes do vencimento."""
    tomorrow = timezone.now().date() + timedelta(days=1)
    expiring_loans = Loan.objects.filter(expected_return_date=tomorrow, status='active')
    
    ws = WhatsAppService()
    for loan in expiring_loans:
        phone = loan.student.guardians.filter(is_financial_responsible=True).first().guardian.phone
        if phone:
            message = (
                f"Lembrete SOTARQ: O livro '{loan.book.title}' deve ser entregue amanhã na biblioteca.\n"
                f"Evite multas de {LibraryConfig.objects.first().daily_fine_amount} Kz/dia."
            )
            ws.send_message(phone, message)


# apps/library/tasks.py
from celery import shared_task
from django.utils import timezone
from apps.core.services import WhatsAppService
from .models import Loan

@shared_task
def task_critical_overdue_alert():
    """
    Rigor SOTARQ: Alerta de cobrança para atrasos superiores a 15 dias.
    """
    today = timezone.now().date()
    limit_date = today - timedelta(days=15)
    
    # Filtra quem venceu há mais de 15 dias e ainda não foi notificado nesta fase
    critical_loans = Loan.objects.filter(
        status='overdue',
        expected_return_date__lte=limit_date,
        notified_15_days=False
    )
    
    ws = WhatsAppService()
    
    for loan in critical_loans:
        borrower = loan.borrower
        # Localiza o telefone (do aluno/staff ou do encarregado financeiro se for aluno)
        phone = borrower.phone 
        
        message = (
            f"⚠️ *AVISO CRÍTICO - BIBLIOTECA SOTARQ*\n\n"
            f"Prezado(a) {borrower.full_name},\n"
            f"O livro *'{loan.book.title}'* encontra-se com atraso superior a 15 dias.\n"
            f"O valor acumulado da multa é de: *{loan.current_fine_preview} Kz*.\n\n"
            f"Por favor, regularize a situação na secretaria para evitar suspensão de serviços."
        )
        
        if ws.send_message(phone, message):
            loan.notified_15_days = True
            loan.save()



@shared_task
def task_notify_return_reminder():
    """Roda 24h antes do vencimento."""
    tomorrow = timezone.now().date() + timedelta(days=1)
    expiring_loans = Loan.objects.filter(expected_return_date=tomorrow, status='active')
    
    ws = WhatsAppService()
    for loan in expiring_loans:
        phone = loan.student.guardians.filter(is_financial_responsible=True).first().guardian.phone
        if phone:
            message = (
                f"Lembrete SOTARQ: O livro '{loan.book.title}' deve ser entregue amanhã na biblioteca.\n"
                f"Evite multas de {LibraryConfig.objects.first().daily_fine_amount} Kz/dia."
            )
            ws.send_message(phone, message)



