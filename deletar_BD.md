#####
-- 1. Termina todas as conexões ativas ao banco (evita erro de "database is being accessed")
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'sotarq_school'
  AND pid <> pg_backend_pid();

-- 2. Apaga o banco de dados
DROP DATABASE sotarq_school;

-- 3. Cria o banco de dados limpo
CREATE DATABASE sotarq_school;

-- 4. Sai do psql
\q
#####










######
-- 1. Expulsar toda a gente da base correta
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE datname = 'sotarq_db' AND pid <> pg_backend_pid();

-- 2. Apagar a base de dados real
DROP DATABASE sotarq_db WITH (FORCE);

-- 3. Criar a base de dados do zero
CREATE DATABASE sotarq_db;

-- 4. Sair
\q

#####

#####
###
###
# Apagar ficheiros de migração antigos (mantendo os __init__.py)
Get-ChildItem -Path "apps" -Filter "00*.py" -Recurse | Remove-Item

# Gerar o novo plano de migração limpo
python manage.py makemigrations

# Aplicar a infraestrutura base (Schema Public)
python manage.py migrate_schemas --schema=public


#####

criar escola

from apps.customers.models import Client, Domain
from apps.core.models import Role

# 1. CRIAR AS ROLES DE SISTEMA (Fundamentais para o SOTARQ)
print("A criar Roles de sistema...")
roles = [
    ('ADMIN', 'Administrador de Unidade', True),
    ('DIRECTOR', 'Diretor Pedagógico', True),
    ('TEACHER', 'Professor', True),
    ('STUDENT', 'Aluno', True),
    ('GUARDIAN', 'Encarregado de Educação', True),
    ('SECRETARY', 'Secretaria', True),
]

for code, name, is_system in roles:
    Role.objects.get_or_create(code=code, defaults={'name': name, 'is_system_role': is_system})

# 2. CRIAR A PRIMEIRA ESCOLA (TENANT)
print("A provisionar a primeira escola...")
tenant, created = Client.objects.get_or_create(
    schema_name='escolateste',
    defaults={
        'name': 'Escola Teste SOTARQ',
        'institution_type': 'complexo',
        'is_active': True
    }
)

# 3. CRIAR O DOMÍNIO DE ACESSO
if created:
    Domain.objects.create(
        domain='escolateste.localhost', # Use este para aceder localmente
        tenant=tenant,
        is_primary=True
    )
    print("Sucesso: Escola e Domínio criados.")
else:
    print("A escola já existia.")
  

criar dominio do schema public:
from apps.customers.models import Client, Domain

# 1. Criar o Tenant Público (Se ainda não existir)
public_tenant, created = Client.objects.get_or_create(
    schema_name='public',
    defaults={
        'name': 'SOTARQ Administração Global',
        'institution_type': 'complexo',
        'is_active': True
    }
)

# 2. Vincular o domínio 'localhost' ao schema public
# Isto diz ao Django: "Se o domínio for localhost, usa o schema public"
Domain.objects.get_or_create(
    domain='localhost',
    tenant=public_tenant,
    is_primary=True
)

# 3. Vincular também o IP (Evita o mesmo erro ao usar 127.0.0.1)
Domain.objects.get_or_create(
    domain='127.0.0.1',
    tenant=public_tenant,
    is_primary=False
)

print("Domínios públicos configurados com sucesso!")