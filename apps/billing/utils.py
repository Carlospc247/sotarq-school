# apps/billing/utils.py
import hmac
import hashlib
from django.conf import settings

def is_valid_webhook_signature(payload, signature):
    """
    Rigor SOTARQ: Validação Dinâmica via HMAC SHA256.
    Invalida qualquer tentativa que não venha do segredo definido no .env.
    """
    if not signature or not settings.GATEWAY_WEBHOOK_SECRET:
        return False
        
    secret = settings.GATEWAY_WEBHOOK_SECRET.encode('utf-8')
    
    # Gera o hash esperado a partir do payload bruto recebido
    expected_signature = hmac.new(
        key=secret,
        msg=payload,
        digestmod=hashlib.sha256
    ).hexdigest()
    
    # Comparação constante no tempo para evitar ataques de temporização
    return hmac.compare_digest(expected_signature, signature)