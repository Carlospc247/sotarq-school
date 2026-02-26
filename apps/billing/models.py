# apps/billing/models.py
from django.db import models
from apps.core.models import BaseModel


class SaaSInvoice(BaseModel):
    STATUS_CHOICES = [('pending', 'Pendente'), ('paid', 'Pago'), ('failed', 'Falhou')]
    
    tenant = models.ForeignKey('customers.Client', on_delete=models.CASCADE)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    reference = models.CharField(max_length=100, unique=True) # Referência para o Gateway
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    payment_url = models.URLField(blank=True, null=True) # Link para o pagamento externo

    def __str__(self):
        return f"Sotarq Invoice {self.reference} - {self.tenant.name}"


