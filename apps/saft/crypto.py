import base64
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives import serialization


def get_hash_display(signature_base64):
    """
    Extrai os caracteres nas posições 1, 11, 21, 31 conforme regra AGT 
    para exibição na fatura impressa.
    """
    try:
        return (signature_base64[0] + signature_base64[10] + 
                signature_base64[20] + signature_base64[30])
    except IndexError:
        return ""

# O teu código de generate_invoice_hash está excelente e segue o padrão RSA-SHA1.

def generate_invoice_hash(invoice_data, previous_hash, private_key_pem):
    """
    invoice_data string: 'Data;DataHora;Numero;Total'
    Ex: '2026-01-13;2026-01-13T17:23:00;FT SCH/1;15000.00'
    """
    # 1. Carregar a Chave Privada
    private_key = serialization.load_pem_private_key(
        private_key_pem.encode(),
        password=None
    )

    # 2. Concatenar com o hash anterior conforme exigência do XSD
    string_to_sign = f"{invoice_data};{previous_hash}" if previous_hash else invoice_data

    # 3. Assinar com RSA-SHA1 (padrão 1.01_01)
    signature = private_key.sign(
        string_to_sign.encode(),
        padding.PKCS1v15(),
        hashes.SHA1()
    )

    # 4. Retornar em Base64 (posições 1, 11, 21, 31 conforme regra AGT)
    return base64.b64encode(signature).decode()