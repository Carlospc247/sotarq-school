# apps/transport/models.py
from django.conf import settings
from django.db import models
from apps.core.models import BaseModel

class TransportZone(BaseModel):
    """Define preços baseados na distância ou bairros."""
    name = models.CharField(max_length=100, help_text="Ex: Zona A - Até 5km")
    monthly_fee = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.name} ({self.monthly_fee} Kz)"

class Bus(BaseModel):
    plate_number = models.CharField(max_length=20, unique=True)
    # Vinculamos a um User real para ele poder fazer login no scanner
    driver = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        limit_choices_to={'is_staff': True},
        related_name='assigned_buses'
    )
    capacity = models.PositiveIntegerField()
    is_active = models.BooleanField(default=True)

    current_lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    current_lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    last_location_update = models.DateTimeField(null=True, blank=True)
    
    # Status operacional para o Diretor
    is_in_route = models.BooleanField(default=False)

# Mantenha apenas esta versão em apps/transport/models.py
class BusEvent(BaseModel):
    EVENT_TYPES = (
        ('IN', 'Embarque'),
        ('OUT', 'Desembarque (Escola)'),
        ('HOME', 'Entregue em Casa'),
    )
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE)
    event_type = models.CharField(max_length=5, choices=EVENT_TYPES)
    # Rigor: Campos essenciais para o mapa de rastreio
    lat = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evento de Transporte"
        ordering = ['-timestamp']


class BusRoute(BaseModel):
    name = models.CharField(max_length=100) # Ex: Rota Talatona-Samba
    bus = models.ForeignKey(Bus, on_delete=models.SET_NULL, null=True)
    stops = models.JSONField(help_text="Lista ordenada de paragens e horários estimados")

class TransportEnrollment(BaseModel):
    """Vincula o aluno a uma rota e zona de faturação."""
    student = models.OneToOneField('students.Student', on_delete=models.CASCADE)
    route = models.ForeignKey(BusRoute, on_delete=models.PROTECT)
    zone = models.ForeignKey(TransportZone, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)




