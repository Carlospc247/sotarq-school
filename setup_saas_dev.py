import os
import django
import sys

# Configurar ambiente
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.customers.models import Client, Domain
from django.contrib.auth import get_user_model
from django.db import connection

# Senha Forte para o Admin Global
PASS_ADMIN = "C#$tlk@Global_2026!"

def colored_print(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m")

def create_hq():
    colored_print("🚀 A INAUGURAR O HQ (ADMIN GLOBAL)...", "94")

    # 1. Tenant Público (A Sede)
    if not Client.objects.filter(schema_name='public').exists():
        colored_print("⚙️  A criar Tenant Público...", "93")
        
        public = Client.objects.create(
            schema_name='public',
            name='Sotarq Admin Global',
            institution_type='corporate',
            primary_color='#111827',
            secondary_color='#F3F4F6'
        )
        
        # Cria o domínio localhost para você acessar o painel
        Domain.objects.create(domain='localhost', tenant=public, is_primary=True)
        colored_print("✅ Tenant Público criado.", "92")
    else:
        colored_print("ℹ️  Tenant Público já existe.", "90")

    # 2. Superuser Global (Você)
    User = get_user_model()
    # Garante que estamos no schema public
    connection.set_schema_to_public()
    
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser('admin', 'admin@sotarq.com', PASS_ADMIN)
        colored_print(f"👤 Admin criado (Senha: {PASS_ADMIN})", "92")
    else:
        colored_print("ℹ️  Admin já existe.", "90")

    colored_print("\n✨ SISTEMA PRONTO PARA CONFIGURAÇÃO MANUAL! ✨", "92")
    print("------------------------------------------------")
    print(f"👉 Aceda ao Painel: http://localhost:8080/admin/")
    print(f"   Login: admin")
    print(f"   Pass:  {PASS_ADMIN}")
    print("------------------------------------------------")
    print("⚠️  PRÓXIMO PASSO: Crie a sua primeira escola clicando em")
    print("    'Customers' > 'Clients' dentro do painel admin.")

if __name__ == "__main__":
    create_hq()