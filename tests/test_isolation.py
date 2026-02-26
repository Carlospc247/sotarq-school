import os
import django
from django.conf import settings

# Setup Django before imports that use models
if not os.environ.get('DJANGO_SETTINGS_MODULE'):
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    django.setup()

from django.test import TestCase
from django_tenants.utils import schema_context, get_tenant_model, get_tenant_domain_model
from apps.students.models import Student
from apps.core.models import User

class TenantIsolationTest(TestCase):
    """
    Verifies that data created in one tenant is not visible in another.
    """
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Ensure django setup if running standalone
        if not os.environ.get('DJANGO_SETTINGS_MODULE'):
            os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
            django.setup()
            
        Client = get_tenant_model()
        Domain = get_tenant_domain_model()
        
        # Create Tenant A
        cls.tenant_a = Client(schema_name='tenant_a', name='Tenant A')
        cls.tenant_a.save()
        domain_a = Domain(domain='a.localhost', tenant=cls.tenant_a, is_primary=True)
        domain_a.save()
        
        import time
        time.sleep(2) # Allow DB triggers to settle
        
        # Create Tenant B
        cls.tenant_b = Client(schema_name='tenant_b', name='Tenant B')
        cls.tenant_b.save()
        domain_b = Domain(domain='b.localhost', tenant=cls.tenant_b, is_primary=True)
        domain_b.save()
        
    @classmethod
    def tearDownClass(cls):
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(f"DROP SCHEMA IF EXISTS {cls.tenant_a.schema_name} CASCADE")
            cursor.execute(f"DROP SCHEMA IF EXISTS {cls.tenant_b.schema_name} CASCADE")
        cls.tenant_a.delete()
        cls.tenant_b.delete()
        super().tearDownClass()

    def test_student_isolation(self):
        print("\n--- Testing Tenant Isolation ---")
        
        # 1. Create Student in Tenant A
        with schema_context(self.tenant_a.schema_name):
            print(f"[Context: {self.tenant_a.schema_name}] Creating Student A...")
            user_a = User.objects.create(username='user_a')
            student_a = Student.objects.create(
                user=user_a,
                registration_number='ST-A',
                full_name='Student A',
                birth_date='2010-01-01',
                gender='M'
            )
            self.assertEqual(Student.objects.count(), 1)
            print("[OK] Student A created.")

        # 2. Verify Student A is NOT visible in Tenant B
        with schema_context(self.tenant_b.schema_name):
            print(f"[Context: {self.tenant_b.schema_name}] Checking visibility...")
            count = Student.objects.count()
            print(f"Student count in Tenant B: {count}")
            self.assertEqual(count, 0, "Tenant A data leaked into Tenant B!")
            
            # Create Student B
            print(f"[Context: {self.tenant_b.schema_name}] Creating Student B...")
            user_b = User.objects.create(username='user_b')
            student_b = Student.objects.create(
                user=user_b,
                registration_number='ST-B',
                full_name='Student B',
                birth_date='2010-01-01',
                gender='F'
            )
            self.assertEqual(Student.objects.count(), 1)
            print("[OK] Student B created.")
            
        # 3. Verify Student B is NOT visible in Tenant A
        with schema_context(self.tenant_a.schema_name):
            print(f"[Context: {self.tenant_a.schema_name}] Re-checking visibility...")
            count = Student.objects.count()
            print(f"Student count in Tenant A: {count}")
            self.assertEqual(count, 1)
            self.assertEqual(Student.objects.first().registration_number, 'ST-A')
            print("[OK] Only Student A is visible.")

if __name__ == '__main__':
    print("Running Standalone Isolation Check...")
    try:
        TenantIsolationTest.setUpClass()
        test = TenantIsolationTest()
        # Mock setUp
        test.setUp()
        test.test_student_isolation()
        test.tearDown()
        TenantIsolationTest.tearDownClass()
        print("\n[PASSED] Isolation Test Completed.")
    except Exception as e:
        print(f"\n[FAILED] Test Error: {e}")
        import traceback
        traceback.print_exc()
