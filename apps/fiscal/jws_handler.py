# apps/fiscal/jws_handler.py
import jwt  # PyJWT
import uuid
from django.utils import timezone
from django.conf import settings
from .models import AssinaturaDigital

class AGTJoseHandler:
    """
    Implementa a norma JWS (RS256) (algoritmo RS256) exigida pela AGT para Faturação Eletrónica.
    """
    @staticmethod
    def generate_jws_signature(payload_data):
        """
        Gera a jwsSignature em Base64URL usando a chave privada da Sotarq.
        """
        # A chave privada deve estar carregada no schema public
        from apps.fiscal.models import AssinaturaDigital
        config = AssinaturaDigital.objects.filter(ativa=True).last()
        
        private_key = config.get_private_key() # Método que retorna a chave decifrada

        headers = {
            "typ": "JOSE",
            "alg": "RS256"
        }
        
        # O payload para consulta exige taxRegistrationNumber e documentNo
        return jwt.encode(
            payload_data,
            private_key,
            algorithm='RS256',
            headers=headers
        )

    @staticmethod
    def build_agt_request(doc_number, tenant_nif):
        """
        Monta o JSON completo para o endpoint /consultarFactura
        """
        payload_assinatura = {
            "taxRegistrationNumber": tenant_nif,
            "documentNo": doc_number
        }
        
        jws_signature = AGTJoseHandler.generate_jws_signature(payload_assinatura)
        
        return {
            "schemaVersion": "1.2",
            "submissionUUID": str(uuid.uuid4()),
            "taxRegistrationNumber": tenant_nif,
            "submissionTimeStamp": timezone.now().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "softwareInfo": {
                "softwareInfoDetail": {
                    "productId": settings.AGT_SOFTWARE_PRODUCER_NAME,
                    "productVersion": settings.AGT_SOFTWARE_VERSION,
                    "softwareValidationNumber": settings.AGT_CERTIFICATE_NUMBER
                },
                "jwsSoftwareSignature": settings.AGT_JWS_SOFTWARE_SIGNATURE # Fornecido pela AGT na certificação
            },
            "jwsSignature": jws_signature,
            "invoiceNo": doc_number
        }