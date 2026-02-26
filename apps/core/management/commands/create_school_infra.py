from django.core.management.base import BaseCommand
from apps.customers.models import Client, Domain

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, required=True)
        parser.add_argument('--schema', type=str, required=True)
        parser.add_argument('--domain', type=str, required=True)

    def handle(self, *args, **options):
        tenant = Client.objects.create(
            name=options['name'], schema_name=options['schema'], 
            institution_type='complexo', is_active=True
        )
        Domain.objects.create(domain=options['domain'], tenant=tenant, is_primary=True)
        self.stdout.write(self.style.SUCCESS(f"✔ Infraestrutura pronta: {options['domain']}"))

# Objetivo: Provisionar uma nova escola (Tenant + Domínio) via terminal.