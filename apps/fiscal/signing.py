# apps/fiscal/signing.py
import base64
import logging
import jwt
import uuid
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

class FiscalSigner:
    """
    Responsável por gerar o Hash SHA1 para o PDF e para o campo 'Hash' do SAF-T.
    (Regra do Decreto Presidencial 292/18)
    """
    def load_private_key_from_db(self):
        from .models import AssinaturaDigital
        config = AssinaturaDigital.objects.filter(ativa=True).last()
        
        if not config or not config.chave_privada_pem:
            logger.error("CRÍTICO: Nenhuma chave privada ativa encontrada!")
            return None
            
        return serialization.load_pem_private_key(
            config.chave_privada_pem.encode('utf-8'),
            password=None,
        )

    def sign(self, invoice_date, system_entry_date, doc_number, gross_total, previous_hash):
        private_key = self.load_private_key_from_db()
        if not private_key:
            raise ValueError("Chaves RSA não configuradas.")

        str_date = invoice_date.strftime('%Y-%m-%d')
        str_entry = system_entry_date.strftime('%Y-%m-%dT%H:%M:%S')
        str_total = "{:.2f}".format(gross_total)
        str_prev_hash = previous_hash if previous_hash else ""

        data_to_sign = f"{str_date};{str_entry};{doc_number};{str_total};{str_prev_hash}"
        
        signature = private_key.sign(
            data_to_sign.encode('utf-8'),
            padding.PKCS1v15(),
            hashes.SHA1()
        )
        return base64.b64encode(signature).decode('utf-8')



class AGTSigner:
    """
    Responsável pelas assinaturas JWS (RS256) para a API da AGT.
    Diferencia a assinatura da Software House (SOTARQ) da assinatura do Emissor (Escola).
    """
    def __init__(self, tenant_private_key_pem):
        """
        Inicia com a chave privada da ESCOLA (Tenant).
        """
        self.private_key = tenant_private_key_pem
        self.headers = {"typ": "JWT", "alg": "RS256"}

    def get_submission_uuid(self):
        return str(uuid.uuid4())

    def get_timestamp(self):
        # Rigor: Usar timezone-aware para evitar rejeição por drift de tempo
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_software_info(self):
        """
        IDENTIFICAÇÃO DO SOFTWARE: Assinado com a Chave Mestre SOTARQ do .env.
        Isto prova à AGT que o sistema é o SOTARQ SCHOOL Certificado.
        """
        software_info_detail = {
            "productId": settings.AGT_SOFTWARE_PRODUCER_NAME,
            "productVersion": settings.AGT_SOFTWARE_VERSION,
            "softwareValidationNumber": settings.AGT_CERTIFICATE_NUMBER,
            "signatureVersion": 1
        }

        try:
            # Rigor: A chave mestre vem do settings (bytes formatados)
            producer_private_key = settings.SOTARQ_PRIVATE_KEY_BYTES
            
            # Geramos o Token JWS do software
            signature = jwt.encode(
                software_info_detail,
                producer_private_key,
                algorithm="RS256",
                headers=self.headers
            )
        except Exception as e:
            logger.error(f"Erro ao assinar softwareInfo com Chave Mestre: {e}")
            raise ValueError("Falha na integridade da Chave Mestre SOTARQ.")

        return {
            "softwareInfoDetail": software_info_detail,
            "jwsSoftwareSignature": signature 
        }

    def sign_payload(self, payload):
        """Assina dados usando a chave da ESCOLA (Tenant)."""
        return jwt.encode(payload, self.private_key, algorithm="RS256", headers=self.headers)

    def sign_document_data(self, doc_data):
        """Assina os campos críticos da fatura (Regra de Ouro da AGT)."""
        payload_to_sign = {
            "documentNo": doc_data["documentNo"],
            "taxRegistrationNumber": doc_data["taxRegistrationNumber"],
            "documentType": doc_data["documentType"],
            "documentDate": doc_data["documentDate"],
            "customerTaxID": doc_data["customerTaxID"],
            "customerCountry": doc_data["customerCountry"],
            "companyName": doc_data["companyName"],
            "documentTotals": doc_data["documentTotals"]
        }
        return self.sign_payload(payload_to_sign)
