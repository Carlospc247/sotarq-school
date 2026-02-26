from django.db import models
from apps.customers.models import Client
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

class CentralKeyVault(models.Model):
    """Cofre Centralizado: Apenas acessível pelo Admin do SaaS"""
    tenant = models.OneToOneField(Client, on_delete=models.CASCADE, related_name='vault')
    chave_privada_pem = models.TextField()
    chave_publica_pem = models.TextField()
    data_geracao = models.DateTimeField(auto_now_add=True)
    ativa = models.BooleanField(default=True)

    def gerar_par_rsa(self):
        key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
        self.chave_privada_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        ).decode('utf-8')
        
        self.chave_publica_pem = key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        self.save()