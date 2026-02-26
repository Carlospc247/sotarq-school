from django.core.management.base import BaseCommand
from apps.core.models import User

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, required=True)
        parser.add_argument('--pass', type=str, required=True)

    def handle(self, *args, **options):
        User.objects.create_superuser(
            username=options['user'], password=options['pass'],
            tenant=None, is_staff=True, is_superuser=True
        )
        self.stdout.write(self.style.SUCCESS(f"✔ Master Admin {options['user']} criado com sucesso."))


# Objetivo: Criar o Superuser Global (Dono do SaaS) que não pertence a nenhuma escola.
