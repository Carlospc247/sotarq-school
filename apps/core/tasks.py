# apps/core/tasks.py
import requests
from celery import shared_task
from django.core.mail import EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django_tenants.utils import schema_context
from apps.finance.models import Payment, Invoice
from apps.customers.models import Client
from celery import shared_task
from django_tenants.utils import schema_context
from django.utils import timezone
from django.core.exceptions import ObjectDoesNotExist
import logging
from apps.students.models import Student
from apps.core.models import Notification, User
from apps.core.services import WhatsAppService
from datetime import timedelta




# Configuração de Logger para Auditoria de Envios
logger = logging.getLogger('celery.tasks.notifications')

@shared_task(bind=True, max_retries=3, default_retry_delay=60, name='core.tasks.send_whatsapp')
def task_send_whatsapp_notification(self, student_id, message_text):
    """
    Processa o envio de notificações multicanal (Sistema Interno + WhatsApp).
    
    Decisões Técnicas:
    1. Persistência Primeiro: Cria sempre a Notification no banco antes de tentar o envio externo.
       Isso garante que o aluno vê o aviso no Portal mesmo que a API do WhatsApp falhe.
    2. Retry Policy: Configurado para 3 tentativas com delay de 60s em caso de erro de conexão (HTTP).
    3. Idempotência: A criação da notificação deve ser verificada para evitar duplicados em retries (opcional, aqui focado na entrega).
    """
    try:
        # 1. Recuperação Eficiente do Aluno e Usuário Associado
        student = Student.objects.select_related('user').get(id=student_id)
        user = student.user

        if not user:
            logger.warning(f"Abortado: Aluno {student_id} sem utilizador associado para notificação.")
            return "No User Linked"

        # 2. Geração da Notificação Interna (Registro Oficial)
        # Baseado no model Notification em apps/core/models.py
        Notification.objects.create(
            user=user,
            title="Novo Boletim Disponível",
            message=message_text,
            link="/portal/dashboard/", # Link direto para o documento
            is_read=False,
            created_at=timezone.now()
        )

        # 3. Envio Externo (WhatsApp)
        # Verifica se existem credenciais configuradas no settings para evitar erros em dev
        whatsapp_api_url = getattr(settings, 'WHATSAPP_API_URL', None)
        whatsapp_token = getattr(settings, 'WHATSAPP_API_TOKEN', None)
        
        # Recupera telefone (Tenta do User, fallback para Student se o model tiver)
        phone_number = getattr(user, 'phone_number', getattr(student, 'phone_number', None))

        if whatsapp_api_url and phone_number:
            payload = {
                "phone": phone_number,
                "message": message_text,
                "provider": "SOTARQ_SCHOOL"
            }
            headers = {
                "Authorization": f"Bearer {whatsapp_token}",
                "Content-Type": "application/json"
            }

            # Timeout explícito para não bloquear o Worker do Celery
            response = requests.post(whatsapp_api_url, json=payload, headers=headers, timeout=10)
            
            # Levanta exceção para códigos 4xx/5xx, acionando o retry do Celery
            response.raise_for_status()
            
            return f"Sent to {phone_number}"
        
        return "Internal Notification Created (No WhatsApp Config/Phone)"

    except Student.DoesNotExist:
        logger.error(f"Erro Crítico: Aluno ID {student_id} não encontrado durante a tarefa de notificação.")
        # Não fazemos retry se o aluno não existe (erro permanente)
        return "Student Not Found"

    except requests.exceptions.RequestException as e:
        logger.error(f"Falha na API WhatsApp para Aluno {student_id}: {str(e)}")
        # Retry automático (Exponential Backoff seria ideal, aqui usamos fixo)
        raise self.retry(exc=e)

    except Exception as e:
        logger.exception(f"Erro não tratado na task de notificação: {str(e)}")
        raise e



logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def task_send_whatsapp_notification(self, student_id, message_text):
    """
    Envia notificação multicanal (Sistema Interno + WhatsApp).
    
    Args:
        student_id (int): ID do aluno alvo.
        message_text (str): Texto da mensagem.
    
    Decisões Técnicas:
    1. bind=True: Permite acesso ao contexto da task para executar self.retry.
    2. Retry: Essencial para falhas de rede em APIs externas.
    3. Notificação Híbrida: Cria registo no banco (persistência) e envia push (imediato).
    """
    
    # O contexto do schema é passado implicitamente se a task for chamada
    # dentro de um bloco with schema_context, mas para segurança em calls
    # assíncronas puras, recomenda-se passar o schema_name como argumento.
    # Assumindo que o worker já está no contexto correto ou que esta task 
    # é disparada dentro de uma cadeia que gerencia isso.
    
    try:
        student = Student.objects.select_related('user').get(id=student_id)
        
        # 1. Determinar o destinatário principal (Prioridade: Encarregado Financeiro -> Aluno)
        # Lógica: O sistema notifica quem paga/gere, mas o aluno também recebe no portal.
        
        # Tenta buscar o primeiro encarregado associado (supondo relação ManyToMany ou ForeignKey)
        guardian_relation = student.guardians.first() 
        target_phone = None
        target_user = student.user # O user padrão para notificação interna é o do aluno
        
        if guardian_relation:
            # Se tiver encarregado, o WhatsApp vai para ele
            # Ajuste conforme o nome do campo no seu modelo Guardian (ex: phone, mobile, contact)
            if hasattr(guardian_relation.guardian, 'phone_number'):
                target_phone = guardian_relation.guardian.phone_number
            elif hasattr(guardian_relation.guardian, 'phone'):
                target_phone = guardian_relation.guardian.phone
            
            # Se o encarregado tiver User no sistema, notifica ele também internamente
            if hasattr(guardian_relation.guardian, 'user') and guardian_relation.guardian.user:
                # Opcional: Criar notificação também para o pai
                Notification.objects.create(
                    user=guardian_relation.guardian.user,
                    title="Novo Documento Disponível",
                    message=message_text,
                    icon="file-text"
                )
        
        # Fallback: Se não achar telefone do pai, tenta o do aluno
        if not target_phone:
            if hasattr(student, 'phone_number'):
                target_phone = student.phone_number
            elif hasattr(student, 'phone'):
                target_phone = student.phone

        # 2. Criar Notificação Interna (Persistência no Portal do Aluno)
        # Isso garante que mesmo que o WhatsApp falhe, o aviso está no sistema.
        if target_user:
            Notification.objects.create(
                user=target_user,
                title="Novo Boletim Disponível",
                message=message_text,
                icon="file-text", # Icone do Feather Icons
                link="/portal/dashboard/" # Link direto para ação
            )

        # 3. Envio Externo (WhatsApp)
        if target_phone:
            service = WhatsAppService()
            service.send_message(target_phone, message_text)
        else:
            logger.warning(f"Aluno {student_id} sem telefone registado para envio de WhatsApp.")

    except Student.DoesNotExist:
        logger.error(f"Aluno ID {student_id} não encontrado para notificação.")
    
    except Exception as exc:
        logger.error(f"Erro ao processar notificação para Aluno {student_id}: {exc}")
        # Retry automático em caso de falha na API do WhatsApp
        raise self.retry(exc=exc)





@shared_task(name="core.tasks.cleanup_read_notifications")
def cleanup_read_notifications():
    """
    Rigor SOTARQ: Mantém o banco leve removendo notificações lidas há mais de 30 dias.
    """
    threshold = timezone.now() - timedelta(days=30)
    deleted_count, _ = Notification.objects.filter(
        is_read=True, 
        created_at__lt=threshold
    ).delete()
    return f"Limpeza concluída: {deleted_count} notificações removidas."


