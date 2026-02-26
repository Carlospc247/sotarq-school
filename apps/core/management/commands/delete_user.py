from django.core.management.base import BaseCommand
from django.db import connection
from apps.core.models import User

class Command(BaseCommand):
    help = 'Elimina um utilizador via SQL puro para ignorar erros de relação multi-tenant.'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, required=True)

    def handle(self, *args, **options):
        user_id = options['id']

        # 1. Verificar se existe (para dar feedback)
        user = User.objects.filter(id=user_id).first()
        if not user:
            self.stdout.write(self.style.ERROR(f"❌ Erro: ID {user_id} não encontrado."))
            return

        username = user.username
        self.stdout.write(f"⚠️  Executando eliminação forçada de: {username} (ID: {user_id})...")

        # 2. SQL Puro para bypassar o ORM do Django
        # Precisamos garantir que estamos no schema public
        with connection.cursor() as cursor:
            try:
                # Forçamos o search path para o public onde os Users vivem
                cursor.execute("SET search_path TO public")
                
                # Deletamos primeiro da tabela de roles para evitar erro de FK
                cursor.execute("DELETE FROM core_userrole WHERE user_id = %s", [user_id])
                
                # Deletamos o usuário
                cursor.execute("DELETE FROM core_user WHERE id = %s", [user_id])
                
                self.stdout.write(self.style.SUCCESS(f"✔ Utilizador '{username}' foi removido do banco de dados."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ Falha no SQL: {str(e)}"))

# Objetivo: Eliminar permanentemente um utilizador do sistema através do seu ID único.
# Uso: python manage.py delete_user --id 15