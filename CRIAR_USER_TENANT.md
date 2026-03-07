from django.contrib.contenttypes.models import ContentType
from apps.customers.models import Client, Domain
from apps.core.models import User, Role, UserRole

# 1. Recuperar o Tenant (Ajuste o schema_name para o que você criou no Admin)
try:
    tenant = Client.objects.get(schema_name='public') # Ou o nome da sua primeira escola
    print(f"--- Iniciando criação no Tenant: {tenant.name} ---")
except Client.DoesNotExist:
    print("ERRO: O Tenant especificado não existe. Crie-o no Admin primeiro.")
    exit()

# 2. Garantir que o Role de ADMIN existe (Rigor do core.models)
role_admin, created = Role.objects.get_or_create(
    code='ADMIN',
    defaults={'name': 'Administrador do Sistema', 'is_system_role': True}
)

# 3. Criar o Usuário Superuser vinculado ao Tenant
# Substitua os dados abaixo pelos seus
username = 'carlos_admin'
email = 'carlos@sotarq.com'
password = 'SotarqPassword2026!'

if not User.objects.filter(username=username).exists():
    user = User.objects.create_superuser(
        username=username,
        email=email,
        password=password,
        tenant=tenant, # Vínculo direto
        current_role='ADMIN'
    )
    
    # 4. Criar a relação M2M via UserRole (conforme seu modelo)
    UserRole.objects.get_or_create(user=user, role=role_admin)
    
    print(f"SUCESSO: Usuário {username} criado e vinculado à {tenant.name}!")
else:
    print(f"AVISO: O usuário {username} já existe.")