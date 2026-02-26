from django.core.management.base import BaseCommand
from django.db import transaction, connection
from apps.plans.models import Plan, Module, PlanModule
from decimal import Decimal

class Command(BaseCommand):
    help = 'Provisiona a Escada de Valor SOTARQ: Padrão, Profissional, Premium e Enterprise'

    def handle(self, *args, **options):
        # Validação de Segurança Multi-tenant
        if connection.schema_name != 'public':
            self.stdout.write(self.style.ERROR("ERRO CRÍTICO: Execute este comando apenas no schema 'public'."))
            return

        self.stdout.write(self.style.MIGRATE_LABEL("--- Configurando Planos Estratégicos SOTARQ ---"))

        # Definição dos Módulos por Nível (Escada de Valor)
        base_modules = ['core', 'academic', 'teachers', 'students','documents', 'finance', 'fiscal', 'saft']
        pro_modules = base_modules + ['library', 'cafeteria', 'audit', 'site_institucional']
        
        # DECISÃO ESTRATÉGICA: O Site Institucional entra apenas no Premium para justificar o preço maior
        premium_modules = pro_modules + ['reports', 'portal', 'transport', 'inventory', 'matriculas_online']
        
        # Enterprise tem TUDO o que existe na tabela de módulos
        # Nota: Certifique-se de rodar setup_modules antes deste comando
        all_modules_qs = Module.objects.all()
        all_modules = [m.code for m in all_modules_qs]

        plans_definition = [
            {
                'name': 'Padrão K12',
                'price': Decimal('7000.00'),
                'students': 200,
                'modules': base_modules,
                'desc': 'Essencial para escolas pequenas. Sem site personalizado.',
                'features': {'whatsapp': False, 'ai': False, 'api': False}
            },
            {
                'name': 'Profissional',
                'price': Decimal('15000.00'),
                'students': 600,
                'modules': pro_modules,
                'desc': 'Controlo total de stocks e biblioteca.',
                'features': {'whatsapp': True, 'ai': False, 'api': False}
            },
            {
                'name': 'Premium BI',
                'price': Decimal('25000.00'),
                'students': 1500,
                'modules': premium_modules,
                'desc': 'Para instituições que decidem com base em dados. Inclui Site Institucional.',
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
                    
                    # Limpa vínculos antigos para garantir integridade (Full Refresh)
                    PlanModule.objects.filter(plan=plan).delete()

                    # Vincula os módulos específicos do nível
                    modules_to_add = []
                    for m_code in p_data['modules']:
                        try:
                            # Busca o objeto na memória para evitar query dentro do loop de create
                            module_obj = Module.objects.get(code=m_code)
                            modules_to_add.append(PlanModule(plan=plan, module=module_obj))
                        except Module.DoesNotExist:
                            self.stdout.write(self.style.WARNING(f" ! Aviso: Módulo '{m_code}' definido no plano mas não existe no banco."))

                    # Bulk Create é mais performante para Enterprise
                    if modules_to_add:
                        PlanModule.objects.bulk_create(modules_to_add)

                    status = "CRIADO" if created else "ATUALIZADO"
                    self.stdout.write(self.style.SUCCESS(f"✔ [{status}] {plan.name} - {p_data['students']} alunos - Site incluído: {'site_institucional' in p_data['modules']}"))

            self.stdout.write(self.style.SUCCESS("\nCatálogo comercial pronto. Execute 'python manage.py runserver'."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Erro ao configurar planos: {str(e)}"))
