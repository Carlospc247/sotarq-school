import os

apps = [
    'plans', 'billing', 'platform',
    'students', 'teachers', 'documents', 'reports', 'audit'
]

base_dir = r'c:\Users\CARLOS SEBASTIÃO-PC\sotarq-school\apps'

for app in apps:
    app_dir = os.path.join(base_dir, app)
    os.makedirs(app_dir, exist_ok=True)
    
    # Create __init__.py
    with open(os.path.join(app_dir, '__init__.py'), 'w') as f:
        pass
        
    # Create apps.py
    with open(os.path.join(app_dir, 'apps.py'), 'w') as f:
        f.write(f"from django.apps import AppConfig\n\nclass {app.capitalize()}Config(AppConfig):\n    default_auto_field = 'django.db.models.BigAutoField'\n    name = 'apps.{app}'\n")
    
    # Create models.py (empty for now)
    with open(os.path.join(app_dir, 'models.py'), 'w') as f:
        f.write("from django.db import models\n\n# Create your models here.\n")

print("Apps initialized.")
