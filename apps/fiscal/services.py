# Para faturação eletrónica. Cinexão
# apps/fiscal/services.py
import requests
import xml.etree.ElementTree as ET
from django.conf import settings
from django.db import transaction
from apps.core.models import SchoolConfiguration
from .models import SerieFiscal, AssinaturaDigital, DocumentoFiscal, DocType
from .signing import AGTSigner
from django.utils import timezone
import json
import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization




def request_series_agt(tenant, year, doc_type):
    """
    Solicita uma nova série à AGT.
    """
    signer = AGTSigner(tenant.assinatura_digital.get_private_key())
    
    payload = {
        "schemaVersion": "1.2",
        "submissionUUID": signer.get_submission_uuid(),
        "taxRegistrationNumber": tenant.nif,
        "submissionTimeStamp": signer.get_timestamp(),
        "softwareInfo": signer.get_software_info(),
        "seriesYear": str(year),
        "documentType": doc_type,
        "establishmentNumber": "1",
        "seriesContingencyIndicator": "N"
    }

    sign_data = {
        "taxRegistrationNumber": tenant.nif,
        "establishmentNumber": "1",
        "seriesYear": str(year),
        "documentType": doc_type,
        # Nota: Validar se seriesContingencyIndicator entra na assinatura na documentação final
        "seriesContingencyIndicator": "N" 
    }
    payload["jwsSignature"] = signer.sign_payload(sign_data)

    # URL Dinâmica baseada no settings
    url = f"{settings.AGT_BASE_URL}/solicitarSerie"

    try:
        response = requests.post(url, json=payload, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            if "seriesFEResult" in data:
                res = data["seriesFEResult"]
                SerieFiscal.objects.create(
                    tenant=tenant,
                    codigo=res["seriesCode"],
                    ano=year,
                    tipo=doc_type,
                    ultimo_numero=0,
                    status='ATIVA'
                )
                return True, res["seriesCode"]
            # Tratar erros de negócio (200 mas com erro lógico)
            if "errorList" in data:
                 return False, f"Erro AGT: {data['errorList']}"
        
        return False, f"Erro HTTP {response.status_code}: {response.text}"
    
    except Exception as e:
        return False, f"Exceção: {str(e)}"


def register_invoice_agt(document_id):
    """
    Regista a fatura na AGT. Usa o AGTSigner e segue o esquema complexo.
    """
    doc = DocumentoFiscal.objects.get(id=document_id)
    tenant = doc.user.tenant
    signer = AGTSigner(tenant.assinatura_digital.get_private_key())
    
    # Construção do JSON da Fatura
    doc_json = {
        "documentNo": doc.numero_documento,
        "documentStatus": "N",
        "documentDate": doc.data_emissao.strftime("%Y-%m-%d"),
        "documentType": doc.tipo_documento,
        "systemEntryDate": doc.created_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "customerTaxID": doc.entidade_nif if doc.entidade_nif else "999999999",
        "customerCountry": "AO",
        "companyName": tenant.name[:200],
        "lines": [],
        "documentTotals": {
            "taxPayable": float(doc.valor_iva),
            "netTotal": float(doc.valor_base),
            "grossTotal": float(doc.valor_total)
        }
    }

    for linha in doc.linhas.all():
        line_item = {
            "lineNumber": linha.numero_linha,
            "productCode": f"SRV{linha.id}",
            "productDescription": linha.descricao[:200],
            "quantity": float(linha.quantidade),
            "unitOfMeasure": "UN",
            "unitPrice": float(linha.preco_unitario),
            "unitPriceBase": float(linha.preco_unitario),
            "taxes": [{
                "taxType": linha.taxa_iva.tax_type,
                "taxCountryRegion": "AO",
                "taxCode": linha.taxa_iva.tax_code,
                "taxPercentage": float(linha.taxa_iva.tax_percentage),
                "taxContribution": float(linha.valor_iva_linha)
            }],
            "settlementAmount": 0.0
        }
        
        if doc.tipo_documento == 'NC':
             line_item["debitAmount"] = float(linha.valor_total_linha)
        else:
             line_item["creditAmount"] = float(linha.valor_total_linha)

        if linha.taxa_iva.tax_code == 'ISE':
            line_item["taxes"][0]["taxExemptionCode"] = linha.taxa_iva.exemption_reason

        doc_json["lines"].append(line_item)

    # Assinatura individual da fatura
    doc_sign_data = doc_json.copy()
    doc_sign_data["taxRegistrationNumber"] = tenant.nif
    doc_json["jwsDocumentSignature"] = signer.sign_document_data(doc_sign_data)

    # Envelope de Envio
    request_payload = {
        "schemaVersion": "1.2",
        "submissionUUID": signer.get_submission_uuid(),
        "taxRegistrationNumber": tenant.nif,
        "submissionTimeStamp": signer.get_timestamp(),
        "softwareInfo": signer.get_software_info(),
        "numberOfEntries": 1,
        "documents": [doc_json]
    }
    
    # Assinatura da Requisição
    request_payload["jwsSignature"] = signer.sign_request_invoice(tenant.nif, 1)

    url = f"{settings.AGT_BASE_URL}/registarFactura"
    
    try:
        # Nota: Headers podem requerer token em produção dependendo da homologação
        response = requests.post(url, json=request_payload, timeout=60)
        
        if response.status_code == 200:
            res_json = response.json()
            # Verificar se há requestID (Sucesso)
            if "requestID" in res_json:
                doc.agt_request_id = res_json.get("requestID")
                doc.agt_status = 'PROCESSING'
                doc.save()
                return True, doc.agt_request_id
            
            # Se devolveu 200 mas tem errorList
            if "errorList" in res_json:
                errors = res_json.get("errorList", [])
                msg = str(errors)
                doc.agt_status = 'ERROR'
                doc.agt_log = msg
                doc.save()
                return False, msg
        else:
            doc.agt_status = 'ERROR'
            doc.agt_log = response.text
            doc.save()
            return False, response.text

    except Exception as e:
        return False, str(e)


#############################################
# WEBSERVICE
#############################################
import requests
import logging
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

class AGTWebService:
    """
    ENGINEER_SOTARQ: Middleware de comunicação com a AGT.
    Implementa segurança, timeout e cache para não travar o Tenant.
    """
    def __init__(self):
        # Em DEBUG, usamos um Mock para o sistema não parar
        self.is_debug = getattr(settings, 'DEBUG', True)
        self.base_url = "https://sandbox.agt.minfin.gov.ao/api/v1"
        self.timeout = 5 # Rigor: Nunca esperar mais de 5s pelo governo

    def check_status(self):
        """Verifica se o portal da AGT está operante."""
        cache_key = 'agt_status_online'
        status = cache.get(cache_key)
        
        if status is not None:
            return status

        if self.is_debug:
            # Simulação de Rigor para Desenvolvimento
            import random
            is_online = random.choice([True, True, True, False]) # 75% chance online
        else:
            try:
                response = requests.get(f"{self.base_url}/health", timeout=self.timeout)
                is_online = response.status_code == 200
            except Exception as e:
                logger.error(f"Erro de conexão AGT: {e}")
                is_online = False

        cache.set(cache_key, is_online, 60) # Cache de 1 minuto
        return is_online



class SerieManager:
    @staticmethod
    def get_or_create_active_serie(doc_type):
        """
        MOTOR DE SÉRIES SOTARQ (Unificado): 
        Busca a série ativa para o Schema atual via django-tenant. 
        Se não existir, executa o protocolo de solicitação automática à AGT.
        """
        year = datetime.date.today().year
        
        # 1. Busca local no Schema atual (Isolamento nativo django-tenant)
        serie = SerieFiscal.objects.filter(
            ano=year,
            tipo_documento=doc_type,
            status='ATIVA'
        ).first()

        if serie:
            return serie

        # 2. Resgate de Configurações do Tenant para comunicação AGT
        config = SchoolConfiguration.objects.first()
        if not config:
            raise ValueError("Erro Crítico SOTARQ: SchoolConfiguration não configurada para este Tenant.")

        # 3. Solicitação Formal à AGT e Persistência
        success, result = SerieManager.request_series_agt(config, year, doc_type)
        
        if success:
            return result
        else:
            # Rigor Máximo: Bloqueio imediato se a AGT não autorizar
            raise RuntimeError(f"BLOQUEIO DE FATURAÇÃO AGT: {result}")

    @staticmethod
    @transaction.atomic
    def request_series_agt(config, year, doc_type):
        """
        Protocolo de Comunicação JWS/AGT:
        Assina, envia e registra a nova série autorizada.
        """
        try:
            # O SchoolConfiguration (config) providencia o NIF e a chave privada
            # Assume-se que config.assinatura_digital.get_private_key() existe ou similar
            signer = AGTSigner(config.assinatura_digital.get_private_key())
            
            payload = {
                "schemaVersion": "1.2",
                "submissionUUID": signer.get_submission_uuid(),
                "taxRegistrationNumber": config.nif, # Rigor: Vem da config do Tenant
                "submissionTimeStamp": signer.get_timestamp(),
                "softwareInfo": signer.get_software_info(),
                "seriesYear": str(year),
                "documentType": doc_type,
                "establishmentNumber": "1",
                "seriesContingencyIndicator": "N"
            }

            sign_data = {
                "taxRegistrationNumber": config.nif,
                "establishmentNumber": "1",
                "seriesYear": str(year),
                "documentType": doc_type,
                "seriesContingencyIndicator": "N" 
            }
            payload["jwsSignature"] = signer.sign_payload(sign_data)

            url = f"{settings.AGT_BASE_URL}/solicitarSerie"
            
            response = requests.post(url, json=payload, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                if "seriesFEResult" in data:
                    res = data["seriesFEResult"]
                    
                    # Criação com os dados oficiais retornados
                    nova_serie = SerieFiscal.objects.create(
                        codigo=res["seriesCode"],
                        ano=year,
                        codigo_validacao_agt=res.get("seriesValidationCode", ""),
                        tipo_documento=doc_type,
                        ultimo_numero=0,
                        status='ATIVA'
                    )
                    return True, nova_serie
                
                if "errorList" in data:
                    return False, f"Rejeição AGT: {data['errorList']}"
            
            return False, f"Erro de Conexão AGT: HTTP {response.status_code}"

        except Exception as e:
            return False, f"Exceção no Protocolo SOTARQ-AGT: {str(e)}"
        

def gerar_chaves_rsa_tenant():
    """
    RIGOR SOTARQ: Gera par de chaves RSA 1024 bits para o SCHEMA ATUAL.
    O isolamento é garantido pelo Search Path do PostgreSQL via django-tenants.
    """
    from .models import AssinaturaDigital
    
    # 1. Gerar a chave privada RSA 1024 (Padrão AGT)
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=1024,
    )

    # 2. Serializar Privada (PEM)
    pem_privada = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')

    # 3. Serializar Pública (PEM)
    pem_publica = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')

    # 4. Transação de Estado no Schema
    # Como estamos dentro do Schema da Escola, objects.all() já é isolado.
    AssinaturaDigital.objects.filter(ativa=True).update(ativa=False)
    
    nova_assinatura = AssinaturaDigital.objects.create(
        chave_privada_pem=pem_privada,
        chave_publica_pem=pem_publica,
        ativa=True
    )
    
    return nova_assinatura
