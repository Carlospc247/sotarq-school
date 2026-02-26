# apps/portal/models.py
from django.db import models
from django.conf import settings
from apps.students.models import Student, Guardian
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.utils import timezone



class PortalProfile(models.Model):
    """
    Links a User to a specific Student or Guardian profile for Portal access.
    This allows a User to switch contexts if they are both (rare, but possible) 
    or just clearly defines 'Who am I in the portal?'.
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portal_profile')
    student = models.ForeignKey(Student, on_delete=models.SET_NULL, null=True, blank=True)
    guardian = models.ForeignKey(Guardian, on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        role = "Student" if self.student else "Guardian" if self.guardian else "Unknown"
        return f"{self.user} ({role})"

class PortalNotification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='portal_notifications')
    title = models.CharField(max_length=255)
    message = models.TextField()
    
    # NOVOS CAMPOS PARA NÍVEL ENTERPRISE:
    icon = models.CharField(max_length=50, default='info-circle', help_text="FontAwesome icon name")
    action_url = models.CharField(max_length=255, null=True, blank=True, help_text="URL para onde o pai será redirecionado")
    
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at'] # Notificações mais recentes primeiro sempre


@login_required
def notification_center(request):
    """Lista todas as notificações e marca as não lidas como visualizadas."""
    notifications = PortalNotification.objects.filter(user=request.user)
    
    # Marcar todas as notificações do utilizador como lidas ao abrir a página
    notifications.filter(read_at__isnull=True).update(read_at=timezone.now())
    
    return render(request, 'portal/notifications.html', {
        'notifications': notifications
    })

