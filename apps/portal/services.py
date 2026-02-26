# apps/portal/services.py
from .models import PortalNotification
from django.utils import timezone

class NotificationService:
    @staticmethod
    def notify(user, title, message):
        """Cria uma notificação persistente para o utilizador."""
        return PortalNotification.objects.create(
            user=user,
            title=title,
            message=message
        )

    @staticmethod
    def get_unread(user):
        """Retorna as notificações não lidas."""
        # Removido o caractere inválido no final desta linha
        return PortalNotification.objects.filter(user=user, read_at__isnull=True).order_by('-created_at')

