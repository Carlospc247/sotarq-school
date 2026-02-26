# apps/core/status_check.py
import os
import django
import json
from datetime import datetime

# Setup do ambiente Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.db import connections
from django.core.cache import cache

def check_status():
    status_data = {
        "last_update": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "services": []
    }

    # 1. Verificar Banco de Dados
    try:
        connections['default'].cursor()
        status_data["services"].append({"name": "Base de Dados", "status": "online", "icon": "fa-database"})
    except Exception:
        status_data["services"].append({"name": "Base de Dados", "status": "offline", "icon": "fa-database"})

    # 2. Verificar Redis (Celery)
    try:
        cache.set('status_check', 'ok', 5)
        status_data["services"].append({"name": "Motor de Notificações (Celery/Redis)", "status": "online", "icon": "fa-bolt"})
    except Exception:
        status_data["services"].append({"name": "Motor de Notificações (Celery/Redis)", "status": "offline", "icon": "fa-bolt"})

    # 3. Status Geral do Sistema
    all_online = all(s["status"] == "online" for s in status_data["services"])
    status_data["system_status"] = "Operacional" if all_online else "Instabilidade Detetada"
    status_data["color"] = "green" if all_online else "red"

    # Salva o resultado para ser lido pela página estática
    with open('/var/www/sotarq/static/status.json', 'w') as f:
        json.dump(status_data, f)

if __name__ == "__main__":
    check_status()

