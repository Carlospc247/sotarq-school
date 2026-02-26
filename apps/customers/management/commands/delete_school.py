from django.core.management.base import BaseCommand
from django.db import connection, transaction
from apps.customers.models import Client

class Command(BaseCommand):
    help = 'NUKE 6.0: Desativação total de restrições para eliminação forçada.'

    def add_arguments(self, parser):
        parser.add_argument('--id', type=int, required=True)

    def handle(self, *args, **options):
        tenant_id = options['id']

        if tenant_id == 1:
            self.stdout.write(self.style.ERROR("❌ Operação Negada: O sistema principal (public) é intocável."))
            return

        try:
            tenant = Client.objects.get(id=tenant_id)
            schema_name = tenant.schema_name
            self.stdout.write(self.style.WARNING(f"☢️  NUCLEAR: Erradicando ID {tenant_id} do mapa..."))

            with transaction.atomic():
                with connection.cursor() as cursor:
                    # 1. ENTRAR EM MODO DE RÉPLICA (Desativa todos os gatilhos e FKs)
                    # Nota: Requer que o utilizador da BD seja superuser (no seu PC deve ser)
                    cursor.execute("SET session_replication_role = 'replica';")
                    cursor.execute("SET search_path TO public;")

                    # 2. LIMPEZA TOTAL DE DEPENDÊNCIAS DO UTILIZADOR
                    self.stdout.write("--- Limpando vínculos periféricos (Admin, Roles, etc)...")
                    cursor.execute("""
                        DELETE FROM django_admin_log 
                        WHERE user_id IN (SELECT id FROM core_user WHERE tenant_id = %s)
                    """, [tenant_id])
                    
                    cursor.execute("""
                        DELETE FROM core_userrole 
                        WHERE user_id IN (SELECT id FROM core_user WHERE tenant_id = %s)
                    """, [tenant_id])

                    # 3. ELIMINAÇÃO DOS UTILIZADORES (Agora sem restrições)
                    self.stdout.write("--- Eliminando utilizadores vinculados...")
                    cursor.execute("DELETE FROM core_user WHERE tenant_id = %s", [tenant_id])

                    # 4. LIMPEZA DE INFRAESTRUTURA
                    self.stdout.write("--- Removendo licenças e domínios...")
                    cursor.execute("DELETE FROM licenses_license WHERE tenant_id = %s", [tenant_id])
                    cursor.execute("DELETE FROM customers_domain WHERE tenant_id = %s", [tenant_id])

                    # 5. DESTRUIÇÃO DO SCHEMA FÍSICO
                    self.stdout.write(f"--- Destruindo schema físico '{schema_name}'...")
                    cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE;")

                    # 6. O GOLPE FINAL NA ESCOLA
                    self.stdout.write("--- Removendo registo na customers_client...")
                    cursor.execute("DELETE FROM customers_client WHERE id = %s", [tenant_id])

                    # 7. VOLTAR AO MODO NORMAL
                    cursor.execute("SET session_replication_role = 'origin';")

            self.stdout.write(self.style.SUCCESS(f"🚀 MISSÃO CUMPRIDA! O ID {tenant_id} deixou de existir no SOTARQ."))

        except Client.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"❌ Erro: O ID {tenant_id} já não consta na tabela Client."))
        except Exception as e:
            # Em caso de erro, garantimos que o modo de réplica seja desativado
            with connection.cursor() as cursor:
                cursor.execute("SET session_replication_role = 'origin';")
            self.stdout.write(self.style.ERROR(f"❌ Falha Crítica de SQL: {str(e)}"))

















# Objetivo: Eliminar permanentemente o Tenant, o Schema e os Domínios associados.
# Uso: python manage.py delete_school --id 5