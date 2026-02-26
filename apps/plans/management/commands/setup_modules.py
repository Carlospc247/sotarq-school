from django.core.management.base import BaseCommand
from apps.plans.models import Module

class Command(BaseCommand):
    help = 'Provisiona o catálogo de módulos do ecossistema SOTARQ'

    def handle(self, *args, **options):
        # Mapeamento técnico para comercial
        modules_list = [
            {'code': 'core', 'name': 'Core Engine', 'description': 'Núcleo de identidade e configurações base.'},
            {'code': 'academic', 'name': 'Gestão Académica', 'description': 'Controlo de turmas, disciplinas e horários.'},
            {'code': 'students', 'name': 'Gestão de Alunos', 'description': 'Matrículas, prontuários e histórico escolar.'},
            {'code': 'teachers', 'name': 'Portal do Professor', 'description': 'Lançamento de notas, sumários e faltas.'},
            {'code': 'finance', 'name': 'Gestão Financeira', 'description': 'Faturação, pagamentos e cobranças.'},
            {'code': 'documents', 'name': 'Gestão Documental', 'description': 'Emissão de certificados e declarações com QR Code.'},
            {'code': 'portal', 'name': 'Portal do Encarregado', 'description': 'Acesso exclusivo para pais e tutores.'},
            {'code': 'reports', 'name': 'Business Intelligence', 'description': 'Relatórios avançados e KPIs analíticos.'},
            {'code': 'audit', 'name': 'Auditoria e Logs', 'description': 'Rastreabilidade total de operações críticas.'},
            {'code': 'accounts', 'name': 'Contabilidade Escolar', 'description': 'Plano de contas e integração bancária.'},
            {'code': 'saft', 'name': 'Exportação SAFT-AO', 'description': 'Conformidade fiscal para Angola.'},
            {'code': 'fiscal', 'name': 'Módulo Fiscal AGT', 'description': 'Assinatura de documentos e comunicação com a AGT.'},
            {'code': 'compras', 'name': 'Aprovisionamento', 'description': 'Gestão de compras e stock da instituição.'},
            {'code': 'library', 'name': 'Gestão de Biblioteca', 'description': 'Catálogo, empréstimos e multas.'},
            {'code': 'cafeteria', 'name': 'Cantina e Refeitório', 'description': 'Vendas POS e controlo de dietas.'},
            {'code': 'transport', 'name': 'Transporte Escolar', 'description': 'Gestão de rotas, frotas e paragens.'},
            {'code': 'inventory', 'name': 'Gestão de Ativos', 'description': 'Inventário de património e depreciação.'},
            {'code': 'management', 'name': 'Global Management', 'description': 'Torre de controlo multi-tenant.'},
            
            # --- NOVO MÓDULO (Requisito: Site Institucional) ---
            {'code': 'site_institucional', 'name': 'Site Institucional & Portal', 'description': 'Habilita website público, personalização de cores e gestão de conteúdo (White-label).'},

            # 2. O Motor de Matrículas (Funcionalidade)
            {'code': 'matriculas_online', 'name': 'Motor de Matrículas Online', 'description': 'Permite candidaturas e upload de documentos via web.'},
        ]

        self.stdout.write(self.style.SUCCESS('--- Iniciando Provisionamento de Módulos SOTARQ ---'))
        
        count = 0
        for item in modules_list:
            module, created = Module.objects.get_or_create(
                code=item['code'],
                defaults={'name': item['name'], 'description': item['description']}
            )
            if created:
                self.stdout.write(f"Módulo [{item['code']}] criado com sucesso.")
                count += 1
            else:
                # Atualiza descrição caso tenha mudado
                if module.description != item['description'] or module.name != item['name']:
                    module.description = item['description']
                    module.name = item['name']
                    module.save()
                    self.stdout.write(self.style.WARNING(f"Módulo [{item['code']}] atualizado."))
                else:
                    self.stdout.write(self.style.WARNING(f"Módulo [{item['code']}] já existe. Ignorado."))

        self.stdout.write(self.style.SUCCESS(f'--- Processo Finalizado. Configuração atualizada. ---'))

