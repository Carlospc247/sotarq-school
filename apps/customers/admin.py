# apps/customers/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Client, Domain

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'schema_name', 
        'name',
        'institution_type',
        'calculation_regime', # Funciona aqui porque o list_display aceita métodos/properties
        'logo_preview',
        'is_active',
        'created_on',
    )

    list_filter = ('institution_type', 'is_active', 'created_on')
    search_fields = ('name', 'schema_name')

    fieldsets = (
        ('Identificação do Sistema (Crítico)', {
            'fields': (
                'schema_name', 
                'name',
                'sub_agent', # Adicionado para você vincular ao Subagente
            ),
        }),
        ('Identidade Visual', {
            'fields': (
                'logo',
                'logo_preview',
                'primary_color',
                'primary_color_preview',
                'secondary_color',
                'secondary_color_preview',
            )
        }),
        ('Configuração Institucional', {
            'fields': (
                'institution_type',
                'calculation_regime', # OK, desde que esteja em readonly_fields
            )
        }),
        ('Controle do Sistema', {
            'fields': (
                'is_active',
                'created_on',
            )
        }),
    )

    # RIGOR: calculation_regime PRECISA estar aqui por ser @property
    readonly_fields = (
        'calculation_regime',
        'created_on',
        'logo_preview',
        'primary_color_preview',
        'secondary_color_preview',
    )

    def get_readonly_fields(self, request, obj=None):
        # Mantém a trava de segurança no schema_name após criar
        readonly = list(self.readonly_fields)
        if obj: 
            readonly.append('schema_name')
        return readonly

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if hasattr(request, 'tenant') and request.tenant.schema_name == 'public':
            return qs.prefetch_related(None).select_related(None)
        return qs

    # --- Previews ---
    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 50px;"/>', obj.logo.url)
        return "—"
    logo_preview.short_description = "Preview Logo"

    def primary_color_preview(self, obj):
        return format_html('<div style="width:20px;height:20px;background:{};border:1px solid #000;"></div>', obj.primary_color)
    
    def secondary_color_preview(self, obj):
        return format_html('<div style="width:20px;height:20px;background:{};border:1px solid #000;"></div>', obj.secondary_color)

@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain', 'tenant', 'is_primary')
    list_filter = ('is_primary',)
    search_fields = ('domain', 'tenant__name')