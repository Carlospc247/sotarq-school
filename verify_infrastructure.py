import os
import django
import sys
import traceback

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from apps.customers.models import Client
from apps.audit.models import AuditLog
from apps.licenses.models import License
from apps.plans.models import Plan, Module, PlanModule
from django.contrib.contenttypes.models import ContentType

def verify():
    print("--- Verifying Core Infrastructure ---")
    
    # 1. Public Tenant
    public = Client.objects.filter(schema_name='public').first()
    if public:
        print("[OK] Public Tenant exists.")
    else:
        print("[FAIL] Public Tenant NOT found.")
        
    # 2. Audit Log (Public Schema)
    try:
        count_before = AuditLog.objects.count()
        # Find a valid content type
        ct = ContentType.objects.first()
        if not ct:
            print("[WARN] No ContentType found, skipping Audit Log creation.")
        else:
            AuditLog.objects.create(
                action='TEST',
                object_id='1',
                content_type=ct, 
                details={'test': 'true'}
            )
            count_after = AuditLog.objects.count()
            if count_after > count_before:
                print("[OK] AuditLog created in Public Schema (Shared App working).")
            else:
                print("[FAIL] AuditLog count did not increase.")
    except Exception as e:
        print(f"[FAIL] AuditLog creation failed:")
        traceback.print_exc()

    # 3. Licensing Logic
    print("\n--- Verifying Licensing ---")
    try:
         # Use a unique name to avoid conflicts if script runs multiple times
        plan_name = "Test Plan Verification"
        plan_code = "test_plan_verif"
        
        plan = Plan.objects.filter(code=plan_code).first()
        if not plan:
            plan = Plan.objects.create(name=plan_name, code=plan_code)
            
        module, _ = Module.objects.get_or_create(name="AcadTest", code="acad_test")
        # Ensure PlanModule doesn't exist to avoid integrity error on get_or_create if limits match but id differs?
        # Actually get_or_create checks params.
        # Let's use update_or_create
        pm, _ = PlanModule.objects.update_or_create(
            plan=plan, 
            module=module, 
            defaults={'limits': {'max_students': 10}}
        )
        
        lic = License(client=public, plan=plan) 
        
        # Test 1: Under limit
        allowed = lic.check_limit('acad_test.max_students', 5)
        if allowed:
             print(f"[OK] Check Limit (5 < 10): PASSED")
        else:
             print(f"[FAIL] Check Limit (5 < 10): FAILED - Expected True, got False")
        
        # Test 2: Over limit
        denied_result = lic.check_limit('acad_test.max_students', 15)
        # We expect check_limit to return FALSE for denied
        if not denied_result:
             print(f"[OK] Check Limit (15 > 10): PASSED")
        else:
             print(f"[FAIL] Check Limit (15 > 10): FAILED - Expected False, got True")
        
    except Exception as e:
         print(f"[FAIL] Licensing verification failed:")
         traceback.print_exc()

if __name__ == '__main__':
    verify()
