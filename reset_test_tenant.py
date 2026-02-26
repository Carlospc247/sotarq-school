import os
import django
from django.db import connection

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.customers.models import Client

def reset():
    print("Resetting test tenant...")
    
    clients = Client.objects.filter(schema_name='school_excellence')
    print(f"Found {clients.count()} clients.")
    
    # Delete Client
    clients.delete()
    print("Client deleted.")
    
    # Drop Schema
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA IF EXISTS school_excellence CASCADE")
        print("Schema dropped.")

if __name__ == '__main__':
    reset()
