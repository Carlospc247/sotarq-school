import os
import django
import sys
from django.db import connection
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.customers.models import Client, Domain
from apps.students.models import Student
from apps.core.models import User
from apps.audit.models import AuditLog
from django_tenants.utils import schema_context

def verify():
    print("--- Verifying Enterprise Resilience (V2) ---")
    sys.stdout.flush()
    
    tenant_name = 'School of Excellence'
    schema_name = 'school_excellence'
    
    # 1. Force Cleanup
    print(f"Checking for existing tenant {tenant_name}...")
    existing = Client.objects.filter(schema_name=schema_name)
    if existing.exists():
        print(f"Found {existing.count()} existing tenants. Deleting...")
        existing.delete() # Triggers schema drop usually
        print("Deleted call finished.")
        if Client.objects.filter(schema_name=schema_name).exists():
             print("[FATAL] Client still exists after delete!")
             # Force SQL delete
             with connection.cursor() as cursor:
                 cursor.execute("DELETE FROM customers_client WHERE schema_name = %s", [schema_name])
                 print("Forced SQL Delete executed.")
        else:
             print("Verified: Client gone.")
    
    # Just to be sure, drop schema raw
    with connection.cursor() as cursor:
        cursor.execute(f"DROP SCHEMA IF EXISTS {schema_name} CASCADE")
        
    # 2. Create Tenant
    print("Creating Tenant...")
    client = Client(
        schema_name=schema_name,
        name=tenant_name,
        institution_type='k12'
    )
    client.save() # This triggers migrate_schemas
    
    domain = Domain()
    domain.domain = 'school.localhost'
    domain.tenant = client
    domain.is_primary = True
    domain.save()
    print("Tenant created.")
    
    # 3. Verify Migrations Applicability
    # We can try to explicitly migrate if we suspect issues, but client.save should have done it.
    # Let's switch context and rely on it.
    
    with schema_context(schema_name):
        print(f"\n[Context: {schema_name}]")
        
        # Create User
        username = 'resilience_test_user'
        if User.objects.filter(username=username).exists():
             User.objects.filter(username=username).delete()
             
        user = User.objects.create(username=username)
        print("[OK] User created.")

        # Create Student
        print("Creating Student...")
        student = Student(
            user=user,
            registration_number="RES-001",
            full_name="Resilience Tester",
            birth_date="2010-01-01",
            gender='M'
        )
        student.save()
        print(f"[OK] Student created. Created_at: {student.created_at}")
        
        # Soft Delete
        print("Testing Soft Delete...")
        student.delete()
        
        if Student.objects.filter(pk=student.pk).exists():
            print("[FAIL] Student still in objects manager.")
        else:
            print("[OK] Student hidden from default manager.")
            
        if Student.all_objects.filter(pk=student.pk).exists():
            print("[OK] Student found in all_objects.")
        else:
             print("[FAIL] Student lost from all_objects.")

if __name__ == '__main__':
    verify()
