from django.contrib import admin
from .models import PortalNotification  # Confirme se o nome do modelo é este
from apps.core.admin_mixins import TenantOnlyAdminMixin

@admin.register(PortalNotification)
class PortalNotificationAdmin(TenantOnlyAdminMixin, admin.ModelAdmin):
    """
    Este Admin usa o Mixin para dizer ao Django:
    'Se o schema for public, eu não existo'.
    Isso impede o SELECT COUNT(*) que está causando o erro.
    """
    pass