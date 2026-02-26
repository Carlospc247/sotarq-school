from django.core.management.base import BaseCommand
from apps.customers.models import Client

class Command(BaseCommand):
    help = 'Lista todas as escolas registadas no SOTARQ com ID, Nome e Schema.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_LABEL("\n--- MAPEAMENTO DE INSTITUIÇÕES (TENANTS) ---"))
        
        # Cabeçalho da tabela
        header = f"{'ID':<5} | {'NOME DA INSTITUIÇÃO':<35} | {'SCHEMA':<20}"
        self.stdout.write(header)
        self.stdout.write("-" * len(header))

        # Busca todas as escolas
        tenants = Client.objects.all().order_by('id')

        for t in tenants:
            # Estilização: Destaca o schema public (Global) em verde
            line = f"{t.id:<5} | {t.name:<35} | {t.schema_name:<20}"
            
            if t.schema_name == 'public':
                self.stdout.write(self.style.SUCCESS(line))
            else:
                self.stdout.write(line)

        self.stdout.write("-" * len(header))
        self.stdout.write(f"Total de instituições: {tenants.count()}\n")



# python manage.py list_schools