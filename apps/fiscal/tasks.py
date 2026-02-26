# apps/fiscal/tasks.py
from decimal import Decimal
from email.message import EmailMessage
import json
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from django_tenants.utils import get_tenant_model, tenant_context
from django.db.models import Sum
from apps.core.models import User
from apps.fiscal.generators import SAFTGenerator
from .models import FiscalConfig, SAFTExport
from celery import shared_task
from django_tenants.utils import schema_context
from apps.customers.models import Client
from apps.fiscal.models import DocumentoFiscal
from apps.fiscal.signing import FiscalSigner
import logging
from celery import shared_task
from .models import DocumentoFiscal, LogIntegracaoAGT
from .signing import AGTSigner
import requests

from django.template.loader import render_to_string






@shared_task
def check_and_generate_monthly_saft():
    """
    Roda diariamente. Verifica se é o dia agendado pela escola para gerar o SAFT do mês anterior.
    """
    today = timezone.now().date()
    TenantModel = get_tenant_model()

    # Itera sobre todas as escolas (Tenants)
    for tenant in TenantModel.objects.exclude(schema_name='public'):
        with tenant_context(tenant):
            # 1. Verifica Configuração da Escola
            config = FiscalConfig.objects.first()
            if not config:
                continue # Escola sem config fiscal, pula
            
            # 2. Verifica se hoje é o dia escolhido
            if today.day == config.saft_generation_day:
                # Define o mês anterior
                last_month = today.replace(day=1) - timezone.timedelta(days=1)
                periodo = last_month.strftime("%Y-%m")

                # 3. Evita duplicidade
                if not SAFTExport.objects.filter(periodo_tributacao=periodo, status='generated').exists():
                    # Cria registo de pendência
                    saft_record = SAFTExport.objects.create(
                        periodo_tributacao=periodo,
                        status='pending',
                        nome_arquivo=f"SAFT_{tenant.schema_name}_{periodo}.xml"
                    )
                    
                    # Dispara a geração pesada (Assíncrona dentro do Tenant)
                    task_generate_xml.delay(saft_record.id, tenant.schema_name)



@shared_task
def task_generate_xml(saft_id, schema_name):
    from django_tenants.utils import schema_context
    from .validators import SAFTValidator
    
    with schema_context(schema_name):
        saft_record = SAFTExport.objects.get(id=saft_id)
        try:
            # 1. Gera o XML (usando o SAFTGenerator que unificamos)
            generator = SAFTGenerator(saft_record.start_date, saft_record.end_date, saft_record.tenant)
            xml_content = generator.generate_xml()
            
            # 2. Perícia Técnica (XSD Validation)
            validator = SAFTValidator()
            is_valid, errors = validator.validate(xml_content)
            
            if not is_valid:
                saft_record.status = 'failed'
                saft_record.log_erros = "Falha no Schema AGT: " + " | ".join(errors)
                saft_record.save()
                # Notifica o Chefe via log crítico
                logger.error(f"SAFT INVÁLIDO gerado para o tenant {schema_name}. Erros: {errors}")
                return

            # 3. Se válido, guarda o ficheiro para download
            from django.core.files.base import ContentFile
            saft_record.arquivo.save(saft_record.nome_arquivo, ContentFile(xml_content))
            saft_record.status = 'generated'
            saft_record.save()
            
        except Exception as e:
            saft_record.status = 'failed'
            saft_record.log_erros = f"Erro de Exceção: {str(e)}"
            saft_record.save()

logger = logging.getLogger('fiscal_audit')

@shared_task(name="apps.fiscal.tasks.daily_integrity_audit")
def daily_integrity_audit():
    """
    ROBÔ DE AUDITORIA: Re-valida todas as assinaturas do dia para detectar fraudes.
    """
    tenants = Client.objects.exclude(schema_name='public')
    signer = FiscalSigner()
    fraud_detected = []

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            # Analisamos documentos confirmados nas últimas 24 horas
            docs = DocumentoFiscal.objects.filter(
                status='confirmed',
                updated_at__gte=timezone.now() - timezone.timedelta(days=1)
            )

            for doc in docs:
                # Geramos o hash temporário para comparação
                recalculated_hash = signer.sign(
                    invoice_date=doc.data_emissao,
                    system_entry_date=doc.created_at,
                    doc_number=doc.numero_documento,
                    gross_total=doc.valor_total,
                    previous_hash=doc.hash_anterior
                )

                if recalculated_hash != doc.hash_documento:
                    msg = f"ALERTA DE FRAUDE: Documento {doc.numero_documento} no Tenant {tenant.schema_name} foi violado!"
                    logger.critical(msg)
                    fraud_detected.append(msg)
                    # Opcional: Bloquear o documento ou marcar para investigação
                    doc.status = 'flagged' 
                    doc.save(update_fields=['status'])

    if fraud_detected:
        # Aqui dispararias um e-mail urgente para o Administrador do Sistema (Sotarq)
        send_fraud_alert_email(fraud_detected)
        
    return f"Auditoria concluída. {len(fraud_detected)} violações encontradas."


@shared_task(name="submit_invoice_agt")
def submit_invoice_agt(document_id):
    """
    Passo 1: Envia a fatura para a AGT e guarda o requestID.
    """
    doc = DocumentoFiscal.objects.get(id=document_id)
    tenant = doc.user.tenant
    
    # Recupera chaves
    config_assinatura = tenant.assinatura_digital # Assumindo relação
    signer = AGTSigner(config_assinatura.get_private_key())

    # Estrutura do Documento (JSON Canónico AGT)
    doc_data = {
        "documentNo": doc.numero_documento, # "FT FT2026A/1"
        "documentStatus": "N",
        "documentDate": doc.data_emissao.strftime("%Y-%m-%d"),
        "documentType": doc.tipo_documento,
        "systemEntryDate": doc.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "customerTaxID": doc.entidade_nif if doc.entidade_nif else "999999999",
        "customerCountry": "AO",
        "companyName": tenant.name,
        "lines": [], # Preencher com loop das linhas
        "documentTotals": {
            "taxPayable": float(doc.valor_iva),
            "netTotal": float(doc.valor_base),
            "grossTotal": float(doc.valor_total)
        }
    }
    
    # Preencher Linhas
    for linha in doc.linhas.all():
        doc_data["lines"].append({
            "lineNumber": linha.numero_linha,
            "productCode": f"SRV-{linha.id}",
            "productDescription": linha.descricao,
            "quantity": float(linha.quantidade),
            "unitOfMeasure": "UN",
            "unitPrice": float(linha.preco_unitario),
            "unitPriceBase": float(linha.preco_unitario),
            "creditAmount": float(linha.valor_total_linha), # Venda normal = Crédito
            "settlementAmount": 0,
            "taxes": [{
                "taxType": "IVA",
                "taxCountryRegion": "AO",
                "taxCode": linha.taxa_iva.tax_code, # NOR, ISE, etc
                "taxPercentage": float(linha.taxa_iva.tax_percentage),
                "taxContribution": float(linha.valor_iva_linha)
            }]
        })

    # Assinar Documento
    doc_data["jwsDocumentSignature"] = signer.sign_document(doc_data)

    # Payload Final de Envio
    payload = {
        "schemaVersion": "1.0",
        "submissionUUID": signer.get_submission_id(),
        "taxRegistrationNumber": tenant.nif,
        "submissionTimeStamp": signer.get_timestamp(),
        "softwareInfo": signer.get_software_info(),
        "numberOfEntries": 1,
        "documents": [doc_data]
    }
    
    # Assinatura da Requisição
    payload_req_sign = {
        "taxRegistrationNumber": tenant.nif,
        "numberOfEntries": 1
        # Nota: A doc diz "taxRegistrationNumber" e "documentNo" para consultar, 
        # mas para registar pode variar. Validar se numberOfEntries entra na assinatura.
        # Geralmente é taxRegistrationNumber + algo unico. 
        # SE A DOC FOR OMISSA, TENTAR APENAS taxRegistrationNumber.
    }
    # Ajuste conforme erro E40 se necessário.
    
    # Envio
    url = f"{settings.AGT_BASE_URL}/registarFactura"
    response = requests.post(url, json=payload, timeout=60)
    
    if response.status_code == 200:
        res_json = response.json()
        request_id = res_json.get('requestID')
        
        # Guarda o RequestID para consultar depois
        doc.agt_request_id = request_id
        doc.agt_status = 'PROCESSING'
        doc.save()
        
        # Agenda verificação
        check_invoice_status.apply_async((doc.id,), countdown=60) # Espera 1 min
    else:
        doc.agt_status = 'ERROR'
        doc.agt_log = response.text
        doc.save()

@shared_task(name="check_invoice_status")
def check_invoice_status(document_id):
    """
    Passo 2: Consulta o estado usando o requestID (Polling).
    """
    doc = DocumentoFiscal.objects.get(id=document_id)
    if not doc.agt_request_id: return

    tenant = doc.user.tenant
    signer = AGTSigner(tenant.assinatura_digital.get_private_key())
    
    payload_assinatura = {
        "taxRegistrationNumber": tenant.nif,
        "requestID": doc.agt_request_id
    }
    
    payload = {
        "schemaVersion": "1.0",
        "submissionUUID": signer.get_submission_id(),
        "taxRegistrationNumber": tenant.nif,
        "submissionTimeStamp": signer.get_timestamp(),
        "softwareInfo": signer.get_software_info(),
        "requestID": doc.agt_request_id,
        "jwsSignature": signer.sign_request(payload_assinatura)
    }
    
    url = f"{settings.AGT_BASE_URL}/obterEstado"
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        # 0=Sucesso, 1=Parcial, 2=Erro, 8=Em curso
        if data['resultCode'] == 0:
            doc_status = data['documentStatusList'][0]
            if doc_status['documentStatus'] == 'V':
                doc.agt_status = 'VALID'
                doc.save()
            elif doc_status['documentStatus'] == 'I':
                doc.agt_status = 'INVALID'
                doc.agt_log = json.dumps(doc_status.get('errorList', []))
                doc.save()
        elif data['resultCode'] == 8:
            # Ainda processando, tenta de novo em 2 min
            check_invoice_status.apply_async((doc.id,), countdown=120)
    



@shared_task(name="task_dispatch_saft_to_accountant")
def task_dispatch_saft_to_accountant(saft_id, schema_name):
    """
    Localiza o Contabilista do Tenant e envia o SAF-T validado.
    Rigor SOTARQ: Prova de entrega e log de auditoria técnica.
    """
    from django_tenants.utils import schema_context
    with schema_context(schema_name):
        saft_record = SAFTExport.objects.get(id=saft_id)
        
        # 1. Busca Contabilistas Ativos (Role: ACCOUNTANT)
        accountants = User.objects.filter(
            current_role='ACCOUNTANT',
            is_active=True
        ).values_list('email', flat=True)

        if not accountants:
            # CORREÇÃO: Adicionado 'f' para interpolação da string
            saft_record.dispatch_log = f"FALHA: Nenhum contabilista (ACCOUNTANT) cadastrado no tenant {schema_name}."
            saft_record.save()
            return

        emails_list = list(accountants)

        # 2. Preparar Resumo de Faturação do Período
        docs_periodo = DocumentoFiscal.objects.filter(
            periodo_tributacao=saft_record.periodo_tributacao,
            status='confirmed'
        )
        total_faturado = docs_periodo.aggregate(Sum('valor_total'))['valor_total__sum'] or Decimal('0.00')
        total_iva = docs_periodo.aggregate(Sum('valor_iva'))['valor_iva__sum'] or Decimal('0.00')

        # 3. Construção do E-mail Enterprise
        subject = f"🏛️ SAF-T Mensal - {saft_record.periodo_tributacao} | {schema_name.upper()}"
        body = render_to_string('fiscal/emails/saft_notification.html', {
            'periodo': saft_record.periodo_tributacao,
            'total_faturado': total_faturado,
            'total_iva': total_iva,
            'qtd_docs': docs_periodo.count(),
            'schema_name': schema_name
        })

        email = EmailMessage(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            emails_list,
        )
        email.content_subtype = "html"

        # 4. Anexar o Ficheiro XML Validado
        if saft_record.arquivo:
            email.attach(
                saft_record.nome_arquivo,
                saft_record.arquivo.read(),
                'application/xml'
            )

        # --- BLOCO ÚNICO DE ENVIO E LOG (RIGOR CONTRA DUPLICIDADE) ---
        try:
            # CORREÇÃO: Removido o email.send() que estava solto acima
            email.send(fail_silently=False)
            
            # Gravação da Prova de Entrega
            saft_record.sent_to_email = ", ".join(emails_list)
            saft_record.sent_at = timezone.now()
            saft_record.dispatch_log = f"SUCESSO: Enviado para {len(emails_list)} destinatário(s)."
            saft_record.save()
            
            logger.info(f"SAF-T enviado com sucesso para o tenant {schema_name}.")
            
        except Exception as e:
            saft_record.dispatch_log = f"ERRO SMTP: {str(e)}"
            saft_record.save()
            logger.error(f"Falha ao despachar SAF-T para o tenant {schema_name}: {e}")
