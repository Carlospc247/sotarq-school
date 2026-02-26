from django.core.management.base import BaseCommand
from apps.core.models import Role

class Command(BaseCommand):
    help = 'Lista todas as Roles (privilégios) do sistema.'

    def handle(self, *args, **options):
        roles = Role.objects.all()
        self.stdout.write(f"{'ID':<5} | {'NOME':<20} | {'CÓDIGO':<15}")
        self.stdout.write("-" * 45)
        for r in roles:
            self.stdout.write(f"{r.id:<5} | {r.name:<20} | {r.code:<15}")

# Uso: python manage.py list_roles