# apps/plans/admin.py

from django.contrib import admin
from .models import Module, Plan, PlanModule

class PlanModuleInline(admin.TabularInline):
    model = PlanModule
    extra = 1
    autocomplete_fields = ['module'] # Melhora a usabilidade se tiveres muitos módulos

@admin.register(Plan)
class PlanAdmin(admin.ModelAdmin):
    inlines = [PlanModuleInline]
    # Adicionamos 'get_modules_display' para veres na lista o que cada plano tem
    list_display = ('name', 'monthly_price', 'max_students', 'get_modules_display', 'has_whatsapp_notifications')
    list_filter = ('has_whatsapp_notifications', 'has_ai_risk_analysis')
    search_fields = ('name',)

    @admin.display(description='Módulos Incluídos')
    def get_modules_display(self, obj):
        # Retorna uma string com os códigos dos módulos (ex: "financeiro, site_institucional")
        return ", ".join([pm.module.code for pm in obj.planmodule_set.all()])

@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'created_at')
    search_fields = ('name', 'code')
    # Mantém o prepopulated, mas atenção ao criar:
    prepopulated_fields = {'code': ('name',)}
