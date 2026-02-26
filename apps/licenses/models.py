# apps/licenses/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
from apps.core.models import BaseModel


class License(BaseModel):
    tenant = models.ForeignKey('customers.Client', on_delete=models.CASCADE)
    plan = models.ForeignKey('plans.Plan', on_delete=models.PROTECT)
    # NOVO: Módulos específicos para esta escola
    additional_modules = models.ManyToManyField('plans.Module', blank=True)
    is_active = models.BooleanField(default=True)
    expiry_date = models.DateField()
    
    def is_valid(self):
        return self.is_active and self.expiry_date >= timezone.now().date()
    
    def __str__(self):
        return f"{self.tenant} - {self.plan} - {self.expiry_date}"

