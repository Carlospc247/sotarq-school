from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import License

@admin.register(License)
class LicenseAdmin(admin.ModelAdmin):
    # 1. Adicionamos 'tempo_restante' à lista de exibição
    list_display = ('tenant', 'plan', 'expiry_date', 'status_validade', 'tempo_restante', 'is_active')
    list_filter = ('is_active', 'plan', 'expiry_date', 'tenant')
    search_fields = ('tenant__name', 'plan__name')
    filter_horizontal = ('additional_modules',)
    readonly_fields = ('created_at', 'updated_at', 'deleted_at')
    
    def status_validade(self, obj):
        hoje = timezone.now().date()
        if obj.is_active and obj.expiry_date >= hoje:
            color = "green"
            texto = "VÁLIDA"
        else:
            color = "red"
            texto = "EXPIRADA/INATIVA"
        return format_html('<b style="color: {};">{}</b>', color, texto)
    
    status_validade.short_description = 'Estado'

    # --- NOVO MÉTODO: CÁLCULO DE DIAS ---
    def tempo_restante(self, obj):
        """
        Calcula a diferença entre a data atual e a expiração.
        """
        hoje = timezone.now().date()
        delta = obj.expiry_date - hoje
        dias = delta.days

        if dias > 0:
            # Licença futura
            color = "#2563eb" # Azul profissional
            if dias <= 7: color = "#06A10E" # Laranja se faltar menos de uma semana
            return format_html('<span style="color: {};">Expira em {} dias</span>', color, dias)
        
        elif dias == 0:
            # Expira hoje
            return format_html('<b style="color: #dc2626;">EXPIRA HOJE!</b>')
        
        else:
            # Já expirou
            dias_passados = abs(dias)
            return format_html('<span style="color: #B90A30;">Expirou há {} dias</span>', dias_passados)

    tempo_restante.short_description = 'Contagem Decrescente'

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('tenant', 'plan')


