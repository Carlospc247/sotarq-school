# config/celery.py
import os
from celery import Celery

# Ajuste aqui para o caminho correto do seu settings de desenvolvimento
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')

app = Celery('sotarq_school')

#namespace='CELERY' significa que todas as configs do Celery no settings.py 
#devem começar com o prefixo CELERY_
app.config_from_object('django.conf:settings', namespace='CELERY')

# Isso é vital: ele vai procurar arquivos tasks.py em todos os seus apps
app.autodiscover_tasks()