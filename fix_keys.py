# 
import os
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from apps.fiscal.models import AssinaturaDigital
from core.models import Tenant # Ajuste conforme seu modelo de Tenant

def generate_rsa_keys():
    """Gera um par de chaves RSA de 2048 bits no formato PEM."""
    private_key = rsa.generate_private_key(
        public_exponent=65537,
        key_size=2048,
    )
    
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode('utf-8')
    
    public_pem = private_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ).decode('utf-8')
    
    return private_pem, public_pem

def fix_and_generate_tenant_keys():
    """Percorre todos os tenants e garante que tenham chaves válidas."""
    tenants = Tenant.objects.all()
    print(f"Iniciando Rigor SOTARQ: Verificando {tenants.count()} escolas...")

    for t in tenants:
        assinatura, created = AssinaturaDigital.objects.get_or_create(tenant=t)
        
        # Se a chave estiver vazia ou mal formatada (ex: \n literal), geramos nova
        if created or "\\n" in assinatura.chave_privada_pem or not assinatura.chave_privada_pem:
            priv, pub = generate_rsa_keys()
            assinatura.chave_privada_pem = priv
            assinatura.chave_publica_pem = pub
            assinatura.descricao = f"Chaves AGT 2026 - {t.schema_name}"
            assinatura.ativa = True
            assinatura.save()
            print(f"[OK] Chaves geradas para: {t.schema_name}")
        else:
            print(f"[SKIP] {t.schema_name} já possui chaves válidas.")

if __name__ == "__main__":
    fix_and_generate_tenant_keys()