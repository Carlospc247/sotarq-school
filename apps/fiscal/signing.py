# apps/fiscal/signing.py
import base64
import logging
import jwt
import uuid
from datetime import datetime
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization
from django.conf import settings

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
    Responsável por gerar as assinaturas JWS (RS256) para a API da AGT.
    (Regra da Faturação Eletrónica)
    """
    def __init__(self, private_key_pem):
        self.private_key = private_key_pem
        self.headers = {"typ": "JWT", "alg": "RS256"}

    def get_submission_uuid(self):
        return str(uuid.uuid4())

    def get_timestamp(self):
        return datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    def get_software_info(self):
        """
        Gera o objeto softwareInfo e ASSINA dinamicamente com a chave MESTRE da SOTARQ.
        """
        # 1. Dados do Software (Payload)
        software_info_detail = {
            "productId": settings.AGT_SOFTWARE_PRODUCER_NAME,
            "productVersion": settings.AGT_SOFTWARE_VERSION,
            "softwareValidationNumber": settings.AGT_CERTIFICATE_NUMBER,
            "signatureVersion": 1
        }

        # 2. Carregar a Chave Mestre da SOTARQ (Do settings/env)
        # ATENÇÃO: Aqui usamos a chave do PRODUTOR, não a da escola!
        try:
            producer_private_key = settings.SOTARQ_PRIVATE_KEY_BYTES
        except AttributeError:
            raise ValueError("Chave Mestre SOTARQ não configurada no settings.")

        # 3. Gerar a Assinatura (O tal Token JWS)
        # Isto cria o jwsSoftwareSignature usando a chave privada mestre
        signature = jwt.encode(
            software_info_detail,
            producer_private_key,
            algorithm="RS256",
            headers={"typ": "JWT", "alg": "RS256"}
        )

        # 4. Retornar a estrutura completa exigida pela AGT
        return {
            "softwareInfoDetail": software_info_detail,
            "jwsSoftwareSignature": signature # O Token gerado agora
        }

    def sign_payload(self, payload):
        return jwt.encode(payload, self.private_key, algorithm="RS256", headers=self.headers)

    def sign_document_data(self, doc_data):
        """Assina os campos críticos da fatura para o JWS."""
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

    def sign_request_invoice(self, tax_reg_number, number_of_entries):
        payload = {
            "taxRegistrationNumber": tax_reg_number,
            "numberOfEntries": number_of_entries
        }
        return self.sign_payload(payload)

