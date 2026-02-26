#python manage.py setup_standard_plan
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from apps.plans.models import Plan, Module, PlanModule
from decimal import Decimal

class Command(BaseCommand):
    help = 'Provisiona a Escada de Valor SOTARQ: Padrão, Profissional, Premium e Enterprise'

    def handle(self, *args, **options):
        if connection.schema_name != 'public':
            self.stdout.write(self.style.ERROR("Execute este comando apenas no schema 'public'."))
            return

        self.stdout.write(self.style.MIGRATE_LABEL("--- Configurando Planos Estratégicos SOTARQ ---"))

        # Definição dos Módulos por Nível (Códigos definidos no setup_modules)
        base_modules = ['academic', 'students', 'finance', 'fiscal', 'saft']
        pro_modules = base_modules + ['library', 'cafeteria', 'audit']
        premium_modules = pro_modules + ['reports', 'documents', 'portal', 'transport', 'inventory']
        
        # Enterprise tem TUDO
        all_modules = [m.code for m in Module.objects.all()]

        plans_definition = [
            {
                'name': 'Padrão K12',
                'price': Decimal('65000.00'),
                'students': 200,
                'modules': base_modules,
                'desc': 'Essencial para escolas pequenas.',
                'features': {'whatsapp': False, 'ai': False, 'api': False}
            },
            {
                'name': 'Profissional',
                'price': Decimal('150000.00'),
                'students': 600,
                'modules': pro_modules,
                'desc': 'Controlo total de stocks e biblioteca.',
                'features': {'whatsapp': True, 'ai': False, 'api': False}
            },
            {
                'name': 'Premium BI',
                'price': Decimal('350000.00'),
                'students': 1500,
                'modules': premium_modules,
                'desc': 'Para instituições que decidem com base em dados.',
                'features': {'whatsapp': True, 'ai': True, 'api': True}
            },
            {
                'name': 'Enterprise',
                'price': Decimal('0.00'), # 0.00 indica Sob Consulta / Negociação
                'students': 99999,
                'modules': all_modules,
                'desc': 'Solução ilimitada para grandes grupos escolares.',
                'features': {'whatsapp': True, 'ai': True, 'api': True}
            }
        ]

        try:
            with transaction.atomic():
                for p_data in plans_definition:
                    plan, created = Plan.objects.update_or_create(
                        name=p_data['name'],
                        defaults={
                            'max_students': p_data['students'],
                            'monthly_price': p_data['price'],
                            'description': p_data['desc'],
                            'has_whatsapp_notifications': p_data['features']['whatsapp'],
                            'has_ai_risk_analysis': p_data['features']['ai'],
                            'has_api_access': p_data['features']['api'],
                        }
                    )
                    
                    # Limpa vínculos antigos para garantir integridade
                    PlanModule.objects.filter(plan=plan).delete()

                    # Vincula os módulos específicos do nível
                    for m_code in p_data['modules']:
                        try:
                            module_obj = Module.objects.get(code=m_code)
                            PlanModule.objects.create(plan=plan, module=module_obj)
                        except Module.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f" ! Módulo {m_code} não encontrado."))

                    status = "CRIADO" if created else "ATUALIZADO"
                    self.stdout.write(self.style.SUCCESS(f"✔ [{status}] {plan.name} - {p_data['students']} alunos - Kz {p_data['price']}"))

            self.stdout.write(self.style.SUCCESS("\nCatálogo comercial pronto para o mercado angolano!"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao configurar planos: {str(e)}"))

