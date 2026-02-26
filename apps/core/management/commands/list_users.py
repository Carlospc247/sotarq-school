from django.core.management.base import BaseCommand
from apps.core.models import User

class Command(BaseCommand):
    help = 'Lista todos os utilizadores do sistema com ID, Nome e Instituição.'

    def add_arguments(self, parser):
        # Permite escolher a ordenação (padrão por ID)
        parser.add_argument(
            '--sort', 
            type=str, 
            default='id', 
            help='Ordenar por: id, username ou first_name'
        )

    def handle(self, *args, **options):
        sort_by = options['sort']
        
        # Otimização: select_related evita múltiplas consultas ao banco para o tenant
        users = User.objects.select_related('tenant').all().order_by(sort_by)

        self.stdout.write(self.style.MIGRATE_LABEL(f"--- LISTA GERAL DE UTILIZADORES (Ordenado por: {sort_by}) ---"))
        
        # Cabeçalho da tabela
        header = f"{'ID':<5} | {'USERNAME':<15} | {'NOME COMPLETO':<25} | {'EMAIL':<25} | {'TENANT (SCHEMA)':<15}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))

        for u in users:
            # Lógica para tratar o nome e o tenant nulo (Global)
            full_name = u.get_full_name() or "---"
            tenant_name = u.tenant.schema_name if u.tenant else "GLOBAL (Public)"
            
            line = f"{u.id:<5} | {u.username:<15} | {full_name:<25} | {u.email:<25} | {tenant_name:<15}"
            
            # Destaca em verde se for superuser global
            if u.is_superuser and not u.tenant:
                self.stdout.write(self.style.SUCCESS(line))
            else:
                self.stdout.write(line)

        self.stdout.write("-" * len(header))
        self.stdout.write(f"Total de utilizadores: {users.count()}")



# Uso: python manage.py list_users
# ou 
# python manage.py list_users --sort name (Atenção: Ainda não funciona)