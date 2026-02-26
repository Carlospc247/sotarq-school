# apps/plans/models.py
from django.db import models
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel


class Module(BaseModel):
    """
    Represents a functional module of the SaaS (e.g., 'Financial', 'Academic', 'Portal').
    """
    name = models.CharField(max_length=50)
    code = models.SlugField(max_length=50, unique=True)
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

class Plan(BaseModel):
    name = models.CharField(max_length=100) # Ex: Basic, Premium, Gold
    max_students = models.PositiveIntegerField()
    monthly_price = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    
    # Módulos ativos (Flags)
    has_whatsapp_notifications = models.BooleanField(default=False)
    has_ai_risk_analysis = models.BooleanField(default=False)
    has_api_access = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.name} - {self.monthly_price} Kz"

        
class PlanModule(models.Model):
    """
    Intermediate table linking a Plan to a Module, allowing for plan-specific limits.
    Enterprise Logic: Different plans can have different limits for the same module.
    """
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE)
    module = models.ForeignKey(Module, on_delete=models.CASCADE)
    
    # Limits encoded in JSON or specific fields. 
    # For robust SQL querying, specific fields are often better, 
    # but JSON is flexible for varying module requirements.
    # Let's use a flexible JSON field for limits.
    limits = models.JSONField(default=dict, blank=True, help_text="limitations e.g. {'max_students': 100, 'max_users': 5}")
    
    class Meta:
        unique_together = ('plan', 'module')

    def __str__(self):
        return f"{self.plan.name} - {self.module.name}"
