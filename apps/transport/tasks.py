from celery import shared_task
from apps.core.services import WhatsAppService
from apps.library.models import LibraryConfig, Loan
from apps.students.models import Student




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
