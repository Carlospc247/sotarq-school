from django.core.management.base import BaseCommand
from apps.core.models import User, Role, UserRole
from apps.customers.models import Client

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True)
        parser.add_argument('--email', type=str, required=True)
        parser.add_argument('--password', type=str, required=True)
        parser.add_argument('--tenant_id', type=int, required=True)

    def handle(self, *args, **options):
        tenant = Client.objects.get(id=options['tenant_id'])
        role = Role.objects.get(code='ADMIN')
        
        user = User.objects.create_user(
            username=options['username'], email=options['email'],
            password=options['password'], tenant=tenant,
            current_role=role.code, is_staff=True
        )
        UserRole.objects.create(user=user, role=role)
        self.stdout.write(self.style.SUCCESS(f"✔ Utilizador {user.username} criado no tenant {tenant.schema_name}"))
    

# Objetivo: Criar um utilizador do zero já dentro de uma escola específica.