from django.core.management.base import BaseCommand
from apps.core.models import User, Role, UserRole

class Command(BaseCommand):
    help = 'Cria um utilizador destinado a uma escola, mas sem vínculo inicial (Pendente).'

    def add_arguments(self, parser):
        parser.add_argument('--username', type=str, required=True)
        parser.add_argument('--email', type=str, required=True)
        parser.add_argument('--password', type=str, required=True)
        parser.add_argument('--role', type=str, default='ADMIN', help='DIRECTOR, ADMIN, TEACHER, etc.')

    def handle(self, *args, **options):
        try:
            # 1. Criar o utilizador no schema public
            # is_staff=True é necessário para que ele possa entrar no admin quando for vinculado
            user = User.objects.create_user(
                username=options['username'],
                email=options['email'],
                password=options['password'],
                tenant=None,               # Sem escola vinculada no momento
                current_role=options['role'],
                is_staff=True,             # Staff para acesso futuro ao painel
                is_superuser=False         # Não é o dono do SaaS
            )

            # 2. Atribuir o Papel (Role) no sistema
            role, _ = Role.objects.get_or_create(
                code=options['role'], 
                defaults={'name': options['role'].capitalize()}
            )
            UserRole.objects.get_or_create(user=user, role=role)

            self.stdout.write(
                self.style.SUCCESS(
                    f"✔ Utilizador '{user.username}' criado com sucesso!\n"
                    f"ℹ️  Estado: PENDENTE (Sem Escola)\n"
                    f"ℹ️  Papel Reservado: {user.current_role}"
                )
            )

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro operacional: {str(e)}"))




# Objetivo: Criar uma conta ativa, com papel escolar definido (Ex: ADMIN ou TEACHER), mas com tenant = None.
# Uso: python manage.py create_pending_user --username carlos_diretor --email carlos@escola.ao --password @guimil@#$%666 --role DIRECTOR
