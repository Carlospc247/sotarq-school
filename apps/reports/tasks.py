# apps/reports/tasks.py
import hashlib
from celery import shared_task, group
from django_tenants.utils import schema_context
from django.utils import timezone
from apps.customers.models import Client
from apps.reports.models import ReportExecution, ReportArtifact
from apps.academic.models import Class, StudentGrade
from apps.reports.services import generate_student_bulletin
from apps.students.models import Enrollment
import logging
import requests
from django.conf import settings
from apps.core.models import Notification
from apps.students.models import Student
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.db import transaction
from weasyprint import HTML, CSS


def generate_student_bulletin(execution_id, student_id, class_id):
    """
    Gera o Boletim de Notas (PDF) para um aluno específico.
    
    Args:
        execution_id (int): ID da execução do relatório (para auditoria).
        student_id (int): ID do aluno.
        class_id (int): ID da turma.
        
    Returns:
        ReportArtifact: O objeto do ficheiro gerado salvo no banco.
    """
    
    # 1. Recuperação de Dados (Data Fetching)
    student = Student.objects.select_related('user').get(id=student_id)
    klass = Class.objects.select_related('academic_year', 'grade_level').get(id=class_id)
    execution = ReportExecution.objects.get(id=execution_id)
    
    # Busca notas com otimização relacional
    grades = StudentGrade.objects.filter(
        student_id=student_id,
        klass_id=class_id
    ).select_related('subject').order_by('subject__name')

    # Dados da Instituição (Tenant atual via connection ou request context não disponível aqui, 
    # mas o execution tem o user que tem o tenant, ou pegamos da turma)
    tenant = klass.academic_year.tenant

    # 2. Preparação do Contexto para o Template
    context = {
        'student': student,
        'class': klass,
        'grades': grades,
        'academic_year': klass.academic_year,
        'school_name': tenant.name,
        'generated_at': timezone.now(),
        'logo_url': tenant.logo.url if tenant.logo else None,
        # Variáveis de Configuração de Cores (Branding)
        'primary_color': getattr(tenant, 'primary_color', '#000000'),
    }

    # 3. Renderização HTML
    html_string = render_to_string('reports/pdf/bulletin_template.html', context)

    # 4. Geração do PDF (Binary)
    # base_url='.' é necessário para carregar imagens estáticas corretamente
    html = HTML(string=html_string, base_url=str(settings.BASE_DIR))
    pdf_file = html.write_pdf()

    # 5. Persistência do Artefato
    # Nome do ficheiro padronizado: Boletim_ANO_TURMA_NUMERO_NOME.pdf
    filename = f"Boletim_{klass.academic_year.name}_{klass.name}_{student.process_number}.pdf"
    
    artifact = ReportArtifact(
        execution=execution,
        format='pdf',
        is_notified=False
    )
    
    # Salva o conteúdo binário no FileField
    artifact.file.save(filename, ContentFile(pdf_file), save=True)
    
    return artifact



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




@shared_task(name='reports.send_all_executive_reports')
def task_monthly_bi_reports():
    """Varre todos os Tenants (escolas) e envia o relatório para cada diretor."""
    for tenant in Client.objects.exclude(schema_name='public'):
        with schema_context(tenant.schema_name):
            from .services.executive import send_monthly_executive_report
            send_monthly_executive_report(tenant)


