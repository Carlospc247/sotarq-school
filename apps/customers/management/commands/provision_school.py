import secrets
import string
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.customers.models import Client, Domain
from apps.core.models import User, Role, UserRole

def gerar_senha_singular(tamanho=15):
    caracteres = string.ascii_letters + string.digits + string.punctuation
    while True:
        senha = ''.join(secrets.choice(caracteres) for _ in range(tamanho))
        if (any(c.islower() for c in senha) and any(c.isupper() for c in senha)
                and any(c.isdigit() for c in senha) and any(c in string.punctuation for c in senha)):
            return senha

class Command(BaseCommand):
    help = 'Provisionamento de infraestrutura SaaS com geração de credenciais seguras.'

    def add_arguments(self, parser):
        parser.add_argument('--name', type=str, required=True, help='Nome da Instituição')
        parser.add_argument('--schema', type=str, required=True, help='Schema físico (ex: escolamila)')
        parser.add_argument('--domain', type=str, required=True, help='Domínio (ex: mila.sotarq.school)')
        parser.add_argument('--admin_user', type=str, required=True, help='Username do Diretor')
        parser.add_argument('--admin_email', type=str, required=True, help='Email institucional')

    def handle(self, *args, **options):
        name = options['name']
        schema = options['schema'].lower().replace(" ", "")
        domain_name = options['domain']
        
        # Geração automática da senha de 15 caracteres
        password_gerada = gerar_senha_singular()

        try:
            with transaction.atomic():
                # 1. Criação do Tenant (Dispara criação de Schema no Postgres)
                tenant = Client.objects.create(schema_name=schema, name=name)

                # 2. Mapeamento de DNS Interno
                Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)

                # 3. Configuração de Acesso Administrativo
                role, _ = Role.objects.get_or_create(code='ADMIN', defaults={'name': 'Administrador'})
                
                user = User.objects.create_user(
                    username=options['admin_user'],
                    email=options['admin_email'],
                    password=password_gerada, # Senha singular aplicada aqui
                    tenant=tenant,
                    current_role=role.code,
                    is_staff=True
                )
                UserRole.objects.create(user=user, role=role)

            self.stdout.write(self.style.SUCCESS(f"\n✔ INFRAESTRUTURA PROVISIONADA: {name}"))
            self.stdout.write(f"🔗 URL: http://{domain_name}:8080")
            self.stdout.write(f"👤 ADMIN: {user.username}")
            self.stdout.write(self.style.WARNING(f"🔑 PASSWORD GERADA: {password_gerada}"))
            self.stdout.write(self.style.NOTICE("⚠️  Guarde esta password! Ela não será exibida novamente.\n"))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ FALHA NO PROVISIONAMENTO: {str(e)}"))




# python manage.py provision_school --name "Colégio Delta" --schema "colegiodelta" --domain "delta.sotarq.local" --admin_user "admin_delta" --admin_email "geral@delta.ao"