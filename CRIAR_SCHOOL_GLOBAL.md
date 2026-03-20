from apps.customers.models import Client, Domain

# 1. Criar o Tenant Público (O Schema compartilhado)
# Este é o "cérebro" que gerencia todas as outras escolas
tenant = Client(
    schema_name='public',
    name='SOTARQ SOFTWARE - Administração Global',
    institution_type='complexo',
    is_active=True
)
tenant.save()

# 2. Criar o Domínio para o Schema Público
# É este domínio que o senhor usará para aceder ao painel de controle global
domain = Domain()
domain.domain = 'localhost' # Ou 'sotarq.local' se configurou o hosts
domain.tenant = tenant
domain.is_primary = True
domain.save()

print("\n[RIGOR_SUCCESS] Schema 'public' e Domínio 'localhost' criados com sucesso!")





##### producao




from apps.customers.models import Client, Domain

# 1. Criar o Tenant Público (Schema compartilhado)
tenant = Client(
    schema_name='public',
    name='SOTARQ SOFTWARE - Administração Global',
    institution_type='complexo',
    is_active=True
)
tenant.save()

# 2. Criar o Domínio para o Schema Público
domain = Domain()
domain.domain = 'sotarqschool.pro'  # Domínio real do Droplet
domain.tenant = tenant
domain.is_primary = True
domain.save()

print("\n[RIGOR_SUCCESS] Schema 'public' e Domínio 'sotarqschool.pro' criados com sucesso!")
