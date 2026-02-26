import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.customers.models import Client, Domain

def init_public_tenant():
    if Client.objects.filter(schema_name='public').exists():
        print("Public tenant already exists.")
        return

    print("Creating Public Tenant...")
    public_client = Client(
        schema_name='public',
        name='Sotarq School Public',
        institution_type='corporate',
        primary_color='#1a73e8',
        secondary_color='#ffffff'
    )
    public_client.save()
    
    domain = Domain()
    domain.domain = 'localhost' # or your dev domain
    domain.tenant = public_client
    domain.is_primary = True
    domain.save()
    
    print("Public Tenant created successfully.")

if __name__ == '__main__':
    init_public_tenant()
