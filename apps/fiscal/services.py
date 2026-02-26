# Para faturação eletrónica. Cinexão
# apps/fiscal/services.py
import requests
import xml.etree.ElementTree as ET
from django.conf import settings
from .models import DocumentoFiscal
from .models import SerieFiscal, AssinaturaDigital, DocumentoFiscal
from .signing import AGTSigner



import requests
import json
from django.conf import settings
from .models import DocumentoFiscal, SerieFiscal
from .signing import AGTSigner

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


