# apps/customers/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import Client, Domain


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = (
        'name',
        'institution_type',
        'calculation_regime',
        'logo_preview',
        'primary_color_preview',
        'secondary_color_preview',
        'is_active',
        'created_on',
    )

    list_filter = (
        'institution_type',
        'is_active',
        'created_on',
    )

    search_fields = (
        'name',
    )

    readonly_fields = (
        'created_on',
        'logo_preview',
        'primary_color_preview',
        'secondary_color_preview',
    )

    fieldsets = (
        ('Informações Básicas', {
            'fields': (
                'name',
                'logo',
                'logo_preview',
                'is_active',
            )
        }),
        ('Identidade Visual', {
            'fields': (
                'primary_color',
                'primary_color_preview',
                'secondary_color',
                'secondary_color_preview',
            )
        }),
        ('Configuração Institucional', {
            'fields': (
                'institution_type',
            )
        }),
        ('Controle do Sistema', {
            'fields': (
                'created_on',
            )
        }),
    )

    # =====================
    # PREVIEWS
    # =====================

    def logo_preview(self, obj):
        if obj.logo:
            return format_html(
                '<img src="{}" style="max-height: 80px; max-width: 200px; object-fit: contain;" />',
                obj.logo.url
            )
        return "—"

    logo_preview.short_description = "Preview do Logo"

    def primary_color_preview(self, obj):
        return format_html(
            '<div style="width: 40px; height: 20px; '
            'background-color: {}; border: 1px solid #000;"></div> {}',
            obj.primary_color,
            obj.primary_color
        )

    primary_color_preview.short_description = "Cor Primária"

    def secondary_color_preview(self, obj):
        return format_html(
            '<div style="width: 40px; height: 20px; '
            'background-color: {}; border: 1px solid #000;"></div> {}',
            obj.secondary_color,
            obj.secondary_color
        )

    secondary_color_preview.short_description = "Cor Secundária"


@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = (
        'domain',
        'tenant',
        'is_primary',
    )
    list_filter = (
        'is_primary',
    )
    search_fields = (
        'domain',
        'tenant__name',
    )
