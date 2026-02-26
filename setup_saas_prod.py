import os
import django
import sys

# EM PRODUÇÃO: Usamos o settings de produção
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.production")
django.setup()

from apps.customers.models import Client, Domain
from django.contrib.auth import get_user_model

def colored_print(text):
    print(f"--- {text} ---")

def setup_production():
    colored_print("🚀 A INAUGURAR O SOTARQ SCHOOL (PRODUÇÃO)...")

    # 1. Criar o Quartel General (Tenant Público)
    # AQUI ESTÁ A DIFERENÇA: Usamos o domínio REAL da sua empresa
    MEU_DOMINIO_REAL = "sotarqschool.com" # <--- Confirme se é este o seu domínio
    public_schema = 'public'

    if not Client.objects.filter(schema_name=public_schema).exists():
        colored_print("⚙️  A criar a Sede (Tenant Público)...")
        
        # AJUSTADO: Removidos 'paid_until' e 'on_trial' para evitar erros.
        # Adicionados campos de branding para ficar consistente com o seu model.
        public_tenant = Client.objects.create(
            schema_name=public_schema,
            name='Sotarq School Global',
            institution_type='corporate', # O Admin Global é uma empresa/corporação
            primary_color='#111827',      # Cor escura profissional para o Admin
            secondary_color='#F3F4F6'
        )
        
        # Cria o domínio principal
        Domain.objects.create(domain=MEU_DOMINIO_REAL, tenant=public_tenant, is_primary=True)
        colored_print(f"✅ Sede criada em: {MEU_DOMINIO_REAL}")
    else:
        colored_print("ℹ️  A Sede já existe.")

    # 2. Criar o Super Admin (Você)
    User = get_user_model()
    # Força conexão ao schema public
    from django.db import connection
    connection.set_schema_to_public()
    
    # Tenta ler a senha do ambiente, senão usa o fallback (mas tente usar a var de ambiente!)
    senha_admin = os.environ.get('DJANGO_SUPERUSER_PASSWORD', 'Sotarq#Prod_2026!')
    
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@sotarq.com', senha_admin)
        colored_print(f"👤 Super Admin criado.")

    colored_print("\n✨ SISTEMA ONLINE! ✨")
    colored_print(f"Aceda agora a: https://{MEU_DOMINIO_REAL}/admin/")
    colored_print("E comece a cadastrar as escolas reais manualmente.")

if __name__ == "__main__":
    setup_production()