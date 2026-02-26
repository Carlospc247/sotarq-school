# apps/audit/models.py
from django.db import models
from django.conf import settings
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey

from apps.core.models import BaseModel

class AuditLog(models.Model):
    """
    Mandatory Audit Trail for Institutional Clients.
    Tracks 'Who did What to Whom/Which Object, When and from Where'.
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='audit_logs'  # Adicionado para evitar conflitos de nomes
    )
    action = models.CharField(max_length=50, help_text="CREATE, UPDATE, DELETE, LOGIN")
    
    # Generic Link to any object
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE, verbose_name="object_type")
    object_id = models.CharField(max_length=50) # Char to support UUIDs if needed
    content_object = GenericForeignKey('content_type', 'object_id')
    
    timestamp = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    details = models.JSONField(blank=True, null=True, help_text="Extra context like changed fields")

    class Meta:
        ordering = ['-timestamp']

    def __str__(self):
        return f"[{self.timestamp}] {self.user} - {self.action} on {self.content_type} {self.object_id}"



class SecurityAlert(BaseModel):
    """
    Rigor SOTARQ: Alertas de Acesso Suspeito.
    Identifica logins impossíveis fisicamente (Time-Distance Violation).
    """
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    alert_type = models.CharField(max_length=50, default='IMPOSSIBLE_TRAVEL')
    
    # Detalhes do Incidente
    last_ip = models.GenericIPAddressField()
    current_ip = models.GenericIPAddressField()
    last_location = models.CharField(max_length=255)
    current_location = models.CharField(max_length=255)
    
    is_resolved = models.BooleanField(default=False)
    risk_level = models.CharField(max_length=10, choices=(('HIGH', 'Crítico'), ('MED', 'Médio')))

    def __str__(self):
        return f"ALERTA: {self.user.username} - {self.alert_type}"


