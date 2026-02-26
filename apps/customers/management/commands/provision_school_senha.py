from django.core.management.base import BaseCommand
from django.db import transaction
from apps.customers.models import Client, Domain
from apps.core.models import User, Role, UserRole

class Command(BaseCommand):
    help = 'Cria uma nova escola, domínio e administrador num único passo.'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, required=True, help='Nome da Escola')
        parser.add_argument('--schema', type=str, required=True, help='Schema (sem espaços)')
        parser.add_argument('--domain', type=str, required=True, help='Domínio (ex: escola.sotarq.local)')
        parser.add_argument('--admin_user', type=str, required=True, help='Username do Admin')
        parser.add_argument('--admin_email', type=str, required=True, help='Email do Admin')

    def handle(self, *args, **options):
        name = options['name']
        schema = options['schema'].lower().replace(" ", "")
        domain_name = options['domain']

        try:
            with transaction.atomic():
                # 1. Criar a Instituição (Tenant)
                tenant = Client.objects.create(
                    schema_name=schema,
                    name=name
                )

                # 2. Criar o Domínio
                Domain.objects.create(
                    domain=domain_name,
                    tenant=tenant,
                    is_primary=True
                )

                # 3. Criar o Administrador da Escola
                role, _ = Role.objects.get_or_create(code='ADMIN', defaults={'name': 'Administrador'})
                
                user = User.objects.create_user(
                    username=options['admin_user'],
                    email=options['admin_email'],
                    password='SenhaPadrao123@', # Trocar para password=options['password'], se quiser inserir a password pelo terminal
                    tenant=tenant,
                    current_role=role.code,
                    is_staff=True
                )
                UserRole.objects.create(user=user, role=role)

            self.stdout.write(self.style.SUCCESS(f"✔ Sucesso! Infraestrutura pronta para: {name}"))
            self.stdout.write(f"🔗 URL: http://{domain_name}:8080")
            self.stdout.write(f"👤 Admin: {user.username}")

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Falha no provisionamento: {str(e)}"))
    


# Uso: python manage.py provision_school --name "Colégio Delta" --schema "colegiodelta" --domain "delta.sotarq.local" --admin_user "admin_delta" --admin_email "geral@delta.ao"

# python manage.py provision_school --name "Complexo Mila" --schema "complexomila" --domain "mila.sotarq.local" --admin_user "mila_admin" --admin_email "mila@escola.ao" --password "Mila@2026_Forte"