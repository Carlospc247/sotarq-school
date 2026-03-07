from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from apps.customers.models import Client, Domain


class Command(BaseCommand):
    help = "Recupera o tenant public, domínio e superusuário"

    def handle(self, *args, **kwargs):

        # 1️⃣ Criar tenant public se não existir
        tenant = Client.objects.filter(schema_name="public").first()

        if not tenant:
            tenant = Client.objects.create(
                schema_name="public",
                name="Administração Global"
            )
            self.stdout.write(self.style.SUCCESS("Tenant public criado"))
        else:
            self.stdout.write("Tenant public já existe")

        # 2️⃣ Criar domínio
        domain = Domain.objects.filter(domain="localhost:8080").first()

        if not domain:
            Domain.objects.create(
                domain="localhost:8080",
                tenant=tenant,
                is_primary=True
            )
            self.stdout.write(self.style.SUCCESS("Domínio criado"))
        else:
            self.stdout.write("Domínio já existe")

        # 3️⃣ Criar superusuário
        User = get_user_model()

        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@sotarq.com",
                password="admin123",
                tenant=tenant
            )
            self.stdout.write(self.style.SUCCESS("Superusuário criado"))
        else:
            self.stdout.write("Superusuário já existe")

        self.stdout.write(self.style.SUCCESS("Sistema recuperado com sucesso"))