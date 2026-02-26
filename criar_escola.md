from apps.customers.models import Client, Domain

# 1. Criar o Tenant (A Escola)
tenant = Client(
    schema_name='escolateste',
    name='Escola de Teste SOTARQ',
    institution_type='complexo'
)
tenant.save()

# 2. Criar o Domínio (A URL de acesso)
domain = Domain()
domain.domain = 'escolateste.localhost' # Ou o seu domínio local
domain.tenant = tenant
domain.is_primary = True
domain.save()