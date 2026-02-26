from django.core.management.base import BaseCommand
from apps.customers.models import Client
from apps.core.models import User

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_LABEL("--- INVENTÁRIO DE TENANTS ---"))
        for c in Client.objects.all():
            self.stdout.write(f"ID: {c.id:<3} | Schema: {c.schema_name:<15} | Nome: {c.name}")
        
        self.stdout.write(self.style.MIGRATE_LABEL("\n--- INVENTÁRIO DE UTILIZADORES ---"))
        for u in User.objects.select_related('tenant').all():
            tenant = u.tenant.schema_name if u.tenant else "GLOBAL"
            self.stdout.write(f"User: {u.username:<15} | Tenant: {tenant:<15} | Role: {u.current_role}")


# Objetivo: Listar Escolas, Schemas e Utilizadores ativos.