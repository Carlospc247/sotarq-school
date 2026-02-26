# apps/core/services.py
from django.core.mail import EmailMessage
from django.conf import settings
from django.template.loader import render_to_string
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import timedelta
import requests
import os
import logging




# Nota: O import de 'Invoice' e outros modelos financeiros deve vir de apps.finance
from apps.finance.models import Invoice, InvoiceItem, DebtAgreement, FinanceConfig

# Se o modelo SchoolMessage estiver no core.models, mantenha o import local
# Caso contrário, ajuste para 'from apps.portal.models import SchoolMessage'
from .models import SchoolMessage

def send_payment_confirmation_notification(invoice, payment):
    student = invoice.student
    # Assumindo que a relação no seu modelo Student é 'guardians' e não 'parent'
    guardian_link = student.guardians.filter(is_financial_responsible=True).first()
    if not guardian_link:
        return None
    
    parent = guardian_link.guardian
    
    context = {
        'student_name': student.full_name,
        'invoice_number': invoice.number,
        'amount': payment.amount,
        'school_name': getattr(settings, 'SCHOOL_NAME', 'Sotarq School')
    }

    # 1. ENVIO DE E-MAIL
    subject = f"Pagamento Confirmado - {invoice.number}"
    message_html = render_to_string('emails/payment_confirmed.html', context)
    
    email = EmailMessage(
        subject,
        message_html,
        settings.DEFAULT_FROM_EMAIL,
        [parent.email],
    )
    email.content_subtype = "html"
    
    if invoice.receipt_pdf:
        email.attach_file(invoice.receipt_pdf.path)
    
    email.send(fail_silently=True)

class DebtRefinancingService:
    @staticmethod
    @transaction.atomic
    def create_agreement(student, installments_count=3):
        overdue_invoices = Invoice.objects.filter(
            student=student, 
            status__in=['pending', 'overdue'],
            due_date__lt=timezone.now().date()
        )
        
        total_debt = sum(inv.calculate_current_total() for inv in overdue_invoices)
        
        if total_debt <= 0:
            raise ValueError("O aluno não possui dívidas vencidas para refinanciamento.")

        agreement = DebtAgreement.objects.create(
            student=student,
            total_debt_original=total_debt,
            installments_count=installments_count,
            is_active=True
        )

        overdue_invoices.update(status='cancelled')
        installment_value = (total_debt / installments_count).quantize(Decimal('0.01'))
        
        for i in range(1, installments_count + 1):
            new_invoice = Invoice.objects.create(
                student=student,
                doc_type='FT',
                total=installment_value,
                due_date=timezone.now().date() + timedelta(days=30 * (i - 1)),
                status='pending'
            )
            
            InvoiceItem.objects.create(
                invoice=new_invoice,
                description=f"Acordo de Dívida {agreement.id} - Prestação {i}/{installments_count}",
                amount=installment_value
            )

        return agreement






import logging
import requests
from django.conf import settings

logger = logging.getLogger(__name__)

class WhatsAppService:
    """
    Serviço Enterprise para encapsular a comunicação com APIs de Mensagens.
    Inclui modo de DEBUG para testes locais sem API.
    """
    
    @staticmethod
    def send_message(phone_number, message_text):
        if not phone_number:
            logger.warning("WhatsAppService: Tentativa de envio sem número de telefone.")
            return False

        # Sanitização do número (Remove espaços, traços, parênteses)
        clean_number = "".join(filter(str.isdigit, str(phone_number)))
        
        # Obter credenciais do settings.py
        api_url = getattr(settings, 'WHATSAPP_API_URL', None)
        token = getattr(settings, 'WHATSAPP_API_TOKEN', None)

        # --- MODO SIMULAÇÃO (CS50W DEBUGGING) ---
        # Se não houver URL ou Token configurado, ou se estivermos em DEBUG,
        # apenas imprimimos no terminal para confirmar que a lógica funcionou.
        if not api_url or not token or settings.DEBUG:
            print("\n" + "="*50)
            print("🚀 [WHATSAPP SIMULATION MODE] 🚀")
            print(f"📞 Para: {clean_number}")
            print(f"💬 Mensagem:\n{message_text}")
            print("="*50 + "\n")
            
            # Retorna True para o controller achar que funcionou
            logger.info(f"Simulação: Mensagem enviada para {clean_number}")
            return True

        # --- MODO PRODUÇÃO (ENVIO REAL) ---
        try:
            # Exemplo de payload genérico (pode variar conforme o provedor: Meta, Twilio, Z-API)
            payload = {
                "phone": clean_number,
                "message": message_text,
                "token": token
            }
            
            # O timeout é crucial para não travar o servidor se a API cair
            response = requests.post(api_url, json=payload, timeout=10)
            response.raise_for_status()
            
            logger.info(f"WhatsApp enviado com sucesso para {clean_number[-4:]} (mascarado).")
            return True

        except requests.exceptions.RequestException as e:
            logger.error(f"Erro de conexão com Gateway WhatsApp: {str(e)}")
            return False



# --- A FUNÇÃO QUE VOCÊ PEDIU ---
def send_school_message(teacher, student, category, subject, content):
    # 1. Identificar o Encarregado Responsável
    guardian_link = student.guardians.filter(is_financial_responsible=True).first()
    if not guardian_link: 
        return None

    # 2. Criar a mensagem no Banco de Dados
    message = SchoolMessage.objects.create(
        sender=teacher.user,
        receiver=guardian_link.guardian.user,
        student=student,
        category=category,
        subject=subject,
        content=content
    )

    # 3. Disparar Alerta via WhatsApp (API UltraMsg)
    if guardian_link.guardian.phone:
        alert_text = (
            f"Olá {guardian_link.guardian.full_name},\n\n"
            f"Há uma nova comunicação escolar ({message.get_category_display()}) sobre o aluno {student.full_name}.\n"
            f"Aceda ao portal para ler o conteúdo completo: https://sotarq.school/portal/inbox/"
        )
        
        # IMPORT LOCAL: Isto mata o erro de 'Circular Import' definitivamente
        from apps.core.tasks import task_send_whatsapp_notification
        task_send_whatsapp_notification.delay(guardian_link.guardian.phone, alert_text)

    return message

