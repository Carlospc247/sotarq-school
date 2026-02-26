from django.contrib import admin
from .models import AuditLog
from apps.core.admin_mixins import SaaSOnlyAdminMixin

@admin.register(AuditLog)
class AuditLogAdmin(SaaSOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action', 'content_type', 'ip_address')
    list_filter = ('action', 'timestamp')
    readonly_fields = [f.name for f in AuditLog._meta.get_fields()] # Tudo apenas leitura
    
    def has_add_permission(self, request): return False
    def has_delete_permission(self, request, obj=None): return False