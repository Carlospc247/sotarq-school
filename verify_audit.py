import os
import django
import sys
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django_tenants.utils import schema_context

from apps.students.models import Student
from apps.audit.models import AuditLog
from apps.core.models import User

def verify_audit():
    print("--- Verifying Audit Logging ---")
    schema_name = 'school_excellence'
    
    with schema_context(schema_name):
        print(f"[Context: {schema_name}]")
        
        # Get Student created in previous step
        # Note: We soft deleted it. So get from all_objects.
        student = Student.all_objects.filter(registration_number="RES-001").first()
        if not student:
            print("[WARN] Student RES-001 not found. Creating new one.")
            user, _ = User.objects.get_or_create(username='audit_tester')
            student = Student.objects.create(
                user=user,
                registration_number="AUDIT-001",
                full_name="Audit Tester",
                birth_date="2010-01-01",
                gender='M'
            )
            
        print(f"Target Student ID: {student.pk}")
        
        # Modify to trigger Update Audit
        student.full_name = "Audit Tester Modified"
        student.save()
        print("Student modified.")
        
        # Check Logs
        logs = AuditLog.objects.filter(object_id=str(student.pk))
        print(f"Audit Logs found: {logs.count()}")
        
        if logs.count() > 0:
            for log in logs:
                print(f" - [{log.timestamp}] {log.action} on {log.content_type} (IP: {log.ip_address})")
            print("[OK] Audit Logging Verified.")
        else:
            print("[FAIL] No Audit Logs found!")

if __name__ == '__main__':
    verify_audit()
