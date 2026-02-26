from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
import os

print("⏳ A gerar par de chaves RSA (1024 bits)...")

# 1. Gerar a chave privada
key = rsa.generate_private_key(
    public_exponent=65537,
    key_size=1024, # 1024 é o mínimo aceite pela AGT (2048 é recomendado, mas 1024 é mais rápido para teste)
)

# 2. Gravar a Chave Privada (private_key.pem)
with open("private_key.pem", "wb") as f:
    f.write(key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption()
    ))

# 3. Extrair e Gravar a Chave Pública (public_key.pem)
public_key = key.public_key()
with open("public_key.pem", "wb") as f:
    f.write(public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    ))

print(f"✅ SUCESSO!")
print(f"📁 Chaves criadas na raiz: {os.getcwd()}")
print("   - private_key.pem (Guarde em segredo!)")
print("   - public_key.pem (Para enviar à AGT)")