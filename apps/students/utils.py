import unicodedata
import re

def generate_sotarq_username(full_name):
    """Transforma 'Nome Completo' em 'nome.completo'"""
    # 1. Lowercase e remover espaços extras
    name = full_name.strip().lower()
    # 2. Remover acentos
    name = "".join(c for c in unicodedata.normalize('NFD', name) if unicodedata.category(c) != 'Mn')
    # 3. Substituir espaços por pontos
    username = re.sub(r'\s+', '.', name)
    # 4. Limpar caracteres não alfanuméricos (exceto o ponto)
    username = re.sub(r'[^a-z0-9.]', '', username)
    return username