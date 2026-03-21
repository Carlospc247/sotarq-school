import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class AlertService:
    @staticmethod
    def send_attendance_alert(phone_number, student_name, subject_name):
        """
        Envia alerta via WhatsApp Cloud API e SMS.
        """
        message_text = f"ALERTA SOTARQ: O educando {student_name} faltou hoje à disciplina de {subject_name} e corre risco de perder o ano por faltas."
        
        # 1. WHATSAPP CLOUD API INTEGRATION
        url = settings.WHATSAPP_API_URL
        headers = {
            "Authorization": f"Bearer {settings.WHATSAPP_API_TOKEN}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "messaging_product": "whatsapp",
            "to": f"244{phone_number}", # Prefixo de Angola
            "type": "text",
            "text": {"body": message_text}
        }

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            if response.status_code not in [200, 201]:
                logger.error(f"Erro WhatsApp: {response.text}")
        except Exception as e:
            logger.error(f"Falha crítica no Gateway WhatsApp: {e}")

        # 2. LOGICA DE SMS (Pode ser estendida para seu provedor local como Unitel/Movicel)
        logger.info(f"SMS ENVIADO PARA {phone_number}: {message_text}")