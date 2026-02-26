# apps/cafeteria/tasks.py
from celery import shared_task
from apps.cafeteria.services import NutritionalService
from apps.core.services import WhatsAppService
from apps.library.models import LibraryConfig, Loan
from apps.students.models import Student




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



@shared_task
def task_send_weekly_nutritional_reports():
    """
    Varre todos os alunos activos e envia o resumo semanal aos encarregados.
    """
    students = Student.objects.filter(is_active=True)
    ws = WhatsAppService()
    
    for student in students:
        summary = NutritionalService.get_weekly_summary(student)
        
        if summary['count'] > 0:
            guardian = student.guardians.filter(is_financial_responsible=True).first()
            if guardian and guardian.guardian.phone:
                # Montagem dinâmica da mensagem (Business Style)
                items_text = "\n".join([f"- {item['description']} ({item['total']}x)" for item in summary['items'][:5]])
                
                message = (
                    f"🥗 *Relatório Nutricional SOTARQ - {student.full_name}*\n\n"
                    f"Resumo da última semana:\n"
                    f"{items_text}\n\n"
                    f"💰 *Total Gasto:* {summary['total_spent']} Kz\n"
                    f"📊 *Índice de Diversidade:* {summary['count']} itens consumidos.\n\n"
                    f"Pode gerir os limites de consumo e bloquear categorias de alimentos no seu Portal do Encarregado."
                )
                
                ws.send_message(guardian.guardian.phone, message)
