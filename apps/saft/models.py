
from django.db import models

class SAFTSettings(models.Model):
    """Configurações de certificação da AGT"""
    software_certificate_number = models.CharField(max_length=50, default="000/AGT/2026")
    private_key = models.TextField(help_text="Chave privada RSA para assinatura das faturas")
    public_key = models.TextField()
    version = models.CharField(max_length=20, default="1.01_01")

class InvoiceControl(models.Model):
    """Rasto de auditoria para garantir a integridade da sequência de faturas"""
    invoice_number = models.CharField(max_length=100, unique=True)
    hash_value = models.CharField(max_length=255, help_text="Hash assinado (RSA Signature)")
    hash_control = models.CharField(max_length=1, default="1") # Versão do algoritmo
    created_at = models.DateTimeField(auto_now_add=True)

