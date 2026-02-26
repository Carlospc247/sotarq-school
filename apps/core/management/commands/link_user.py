from django.core.management.base import BaseCommand
from apps.core.models import User, Role, UserRole
from apps.customers.models import Client

class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('--user', type=str, required=True)
        parser.add_argument('--tenant', type=int, required=True)
        parser.add_argument('--role', type=str, required=True)

    def handle(self, *args, **options):
        try:
            user = User.objects.get(username=options['user'])
            tenant = Client.objects.get(id=options['tenant'])
            role = Role.objects.get(code=options['role'])
            
            user.tenant, user.current_role, user.is_staff = tenant, role.code, True
            user.save()
            UserRole.objects.get_or_create(user=user, role=role)
            
            self.stdout.write(self.style.SUCCESS(f"✔ {user.username} vinculado à {tenant.name} como {role.code}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Erro: {str(e)}"))
            

# Uso: python manage.py link_user --user carlos --tenant 5 --role ADMIN