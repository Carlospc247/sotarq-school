from django.core.management.base import BaseCommand
from apps.customers.models import Domain

class Command(BaseCommand):
    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_LABEL("--- MAPEAMENTO DE DOMÍNIOS ATIVOS ---"))
        for d in Domain.objects.select_related('tenant').all():
            status = "✅ ATIVO" if d.is_primary else "⚪ SECUNDÁRIO"
            self.stdout.write(f"Domínio: {d.domain:<30} | Escola: {d.tenant.name:<20} | {status}")


# python manage.py check_domains