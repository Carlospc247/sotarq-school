# Use este para consertar a escola que o senhor já criou.
# python manage.py seed_existing_school seu_schema_aqui
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from apps.customers.models import Client
from apps.academic.utils import run_school_factory

class Command(BaseCommand):
    help = 'Executa o seed de estrutura acadêmica para uma escola já existente.'

    def add_arguments(self, parser):
        parser.add_argument('schema_name', type=str, help='O nome do schema da escola')

    def handle(self, *args, **options):
        schema_name = options['schema_name']
        try:
            instance = Client.objects.get(schema_name=schema_name)
            with schema_context(schema_name):
                self.stdout.write(self.style.SUCCESS(f'Iniciando Seed em: {instance.name}'))
                run_school_factory(instance, stdout=self.stdout)
                self.stdout.write(self.style.SUCCESS('Seed finalizado com sucesso!'))
        except Client.DoesNotExist:
            self.stdout.write(self.style.ERROR(f'Schema "{schema_name}" não encontrado.'))