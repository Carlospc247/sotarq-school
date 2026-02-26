# apps/portal/context_processors.py
from django.db import connection
from .models import PortalNotification

def notification_count(request):
    # SEGURANÇA: Bloqueia a consulta se for o Dono do Sistema ou se não houver login
    if connection.schema_name == 'public' or not request.user.is_authenticated:
        return {'unread_notifications_count': 0}

    try:
        # Use o campo exato do seu model (seja 'is_read' ou 'read_at')
        count = PortalNotification.objects.filter(
            user=request.user, 
            read_at__isnull=True  # Mantive o padrão do seu código anterior
        ).count()
    except Exception:
        # Se a tabela ainda não foi criada no tenant, evita que o sistema quebre
        count = 0
        
    return {'unread_notifications_count': count}