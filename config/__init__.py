# config/__init__.py

from .celery import app as celery_app

# Isso garante que o app seja sempre importado quando o Django iniciar
__all__ = ('celery_app',)