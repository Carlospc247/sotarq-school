from django_tenants.utils import schema_context
from apps.customers.models import Client 
from apps.academic.models import GradeLevel

tenants = Client.objects.exclude(schema_name='public')

print(f"{'TENANT':<20} | {'ID SUGERIDO':<12} | {'NOME DA CLASSE'}")
print("-" * 50)

for tenant in tenants:
    with schema_context(tenant.schema_name):
        # Buscamos a primeira classe disponível em cada escola
        first_grade = GradeLevel.objects.order_by('level_index').first()
        
        if first_grade:
            print(f"{tenant.schema_name:<20} | {first_grade.id:<12} | {first_grade.name}")
        else:
            print(f"{tenant.schema_name:<20} | {'SEM DADOS':<12} | [ALERTA: Criar GradeLevel aqui]")

print("-" * 50)