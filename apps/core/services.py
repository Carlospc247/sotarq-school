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
import requests
from django.conf import settings

logger = logging.getLogger(__name__)




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








class WhatsAppService:
    """
    Serviço Enterprise SOTARQ para Mensageria.
    Unifica o envio de texto e documentos (PDF) com suporte a modo simulação.
    """

    @staticmethod
    def _get_api_credentials():
        """Helper interno para obter credenciais de forma limpa."""
        return (
            getattr(settings, 'WHATSAPP_API_URL', None),
            getattr(settings, 'WHATSAPP_API_TOKEN', None)
        )

    @staticmethod
    def _sanitize_number(phone):
        """Padroniza o número de telefone para o formato exigido pelas APIs."""
        return "".join(filter(str.isdigit, str(phone)))

    @staticmethod
    def send_message(phone_number, message_text):
        """Envia mensagens de texto simples."""
        if not phone_number:
            logger.warning("WhatsAppService: Tentativa de envio sem número.")
            return False

        clean_number = WhatsAppService._sanitize_number(phone_number)
        api_url, token = WhatsAppService._get_api_credentials()

        # --- MODO SIMULAÇÃO (DEBUG) ---
        if settings.DEBUG or not api_url or not token:
            print("\n" + "="*50)
            print("🚀 [WHATSAPP TEXT SIMULATION] 🚀")
            print(f"📞 Para: {clean_number}")
            print(f"💬 Conteúdo: {message_text[:100]}...")
            print("="*50 + "\n")
            return True

        # --- MODO PRODUÇÃO ---
        try:
            payload = {
                "phone": clean_number,
                "message": message_text,
                "token": token
            }
            # Endpoint padrão para texto (ajuste conforme seu provedor: /send-message)
            response = requests.post(f"{api_url}/send-text", json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"WhatsApp (Texto) enviado para {clean_number[-4:]}")
            return True
        except Exception as e:
            logger.error(f"Erro no Gateway WhatsApp (Texto): {str(e)}")
            return False

    @staticmethod
    def send_invoice_pdf(phone, pdf_data, filename, caption):
        """Envia PDFs (Faturas, Recibos) com legenda."""
        if not phone:
            return False

        clean_number = WhatsAppService._sanitize_number(phone)
        api_url, token = WhatsAppService._get_api_credentials()

        # --- MODO SIMULAÇÃO (DEBUG) ---
        if settings.DEBUG or not api_url or not token:
            debug_path = os.path.join(settings.MEDIA_ROOT, 'debug_whatsapp_pdfs')
            os.makedirs(debug_path, exist_ok=True)
            full_path = os.path.join(debug_path, filename)
            with open(full_path, 'wb') as f:
                f.write(pdf_data)
            
            print("\n" + "="*50)
            print("🚀 [WHATSAPP PDF SIMULATION] 🚀")
            print(f"📞 Para: {clean_number}")
            print(f"📄 Arquivo Salvo: {full_path}")
            print(f"📝 Legenda: {caption}")
            print("="*50 + "\n")
            return True

        # --- MODO PRODUÇÃO ---
        try:
            files = {'file': (filename, pdf_data, 'application/pdf')}
            payload = {
                'phone': clean_number, 
                'caption': caption, 
                'token': token
            }
            
            # Endpoint para documentos
            response = requests.post(f"{api_url}/send-document", data=payload, files=files, timeout=15)
            response.raise_for_status()
            logger.info(f"WhatsApp (PDF) enviado para {clean_number[-4:]}")
            return True
        except Exception as e:
            logger.error(f"Erro no Gateway WhatsApp (PDF): {str(e)}")
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

