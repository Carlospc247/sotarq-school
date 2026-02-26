import os
import django
from datetime import timedelta
from django.utils import timezone

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from apps.customers.models import Client, Domain
from apps.plans.models import Plan, Module, PlanModule
from apps.licenses.models import License

def bootstrap_system():
    print("[*] Configurando Módulos e Planos Globais...")

    # 1. Módulos conforme TYPE_CHOICES
    modules_data = [
        ('creche', 'Creche / Pre-School'),
        ('k12', 'K-12 School'),
        ('vocational', 'Vocational / Technical'),
        ('university', 'University / Higher Ed'),
        ('corporate', 'Corporate Training'),
    ]
    
    modules = {}
    for code, name in modules_data:
        mod, _ = Module.objects.get_or_create(code=code, defaults={'name': name})
        modules[code] = mod

    # 2. Definição Rígida de Planos
    plans_config = [
        {
            'name': 'Basic (Starter)',
            'price': 25000,
            'units': 1,
            'students': 150,
            'modules': ['creche'], # Ou corporate conforme o foco
            'features': {'saft': True}
        },
        {
            'name': 'Professional',
            'price': 60000,
            'units': 2,
            'students': 500,
            'modules': ['k12', 'vocational'],
            'features': {'saft': True, 'app': True}
        },
        {
            'name': 'Premium (Redes)',
            'price': 150000,
            'units': 5,
            'students': 2000,
            'modules': ['k12', 'university', 'creche'],
            'features': {'saft': True, 'selector': True}
        },
        {
            'name': 'Enterprise (Global)',
            'price': 400000,
            'units': 9999, # Ilimitado
            'students': 99999,
            'modules': [m[0] for m in modules_data],
            'features': {'saft': True, 'panic_button': True, 'api': True, 'audit': True}
        }
    ]

    for p_data in plans_config:
        plan, _ = Plan.objects.update_or_create(
            name=p_data['name'],
            defaults={
                'monthly_price': p_data['price'],
                'max_students': p_data['students'],
                'max_units': p_data['units'],
                'has_api_access': p_data['features'].get('api', False),
            }
        )
        
        # Vincular Módulos ao Plano
        for m_code in p_data['modules']:
            PlanModule.objects.get_or_create(plan=plan, module=modules[m_code])

    print("[+] Planos e Módulos configurados com sucesso.")

def create_tenant(schema, domain, name, plan_name, inst_type):
    try:
        # 1. Criar Cliente
        client, created = Client.objects.get_or_create(
            schema_name=schema,
            defaults={
                'name': name,
                'institution_type': inst_type,
                'is_active': True
            }
        )
        
        # 2. Criar Domínio
        Domain.objects.get_or_create(
            domain=domain,
            defaults={'tenant': client, 'is_primary': True}
        )

        # 3. Atribuir Licença
        plan = Plan.objects.get(name=plan_name)
        License.objects.update_or_create(
            tenant=client,
            defaults={
                'plan': plan,
                'is_active': True,
                'expiry_date': timezone.now().date() + timedelta(days=365)
            }
        )
        
        print(f"[OK] Cliente {name} criado no plano {plan_name}.")
    except Exception as e:
        print(f"[ERRO] {e}")

if __name__ == "__main__":
    bootstrap_system() # Corre uma vez para configurar o sistema
    
    # Exemplo de criação de uma rede de creches
    create_tenant(
        schema='rede_magno', 
        domain='magno.local', 
        name='Grupo Magno Internacional', 
        plan_name='Premium (Redes)', 
        inst_type='creche'
    )