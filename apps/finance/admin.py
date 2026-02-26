from django.contrib import admin
from django.db import connection # Importação necessária para detetar o schema
from .models import FinanceConfig, FeeType, Invoice, InvoiceItem, PaymentMethod, BankAccount, Payment

@admin.register(FinanceConfig)
class FinanceConfigAdmin(admin.ModelAdmin):
    list_display = ('late_fee_percentage', 'daily_interest_rate', 'grace_period_days')
    
    def has_module_permission(self, request):
        # Se for o Dono do Sistema (public), esconde este módulo
        if connection.schema_name == 'public':
            return False
        return super().has_module_permission(request)

    def has_add_permission(self, request):
        # Proteção contra schema public
        if connection.schema_name == 'public':
            return False
        # No tenant, só permite adicionar se não existir nenhum
        try:
            return not FinanceConfig.objects.exists()
        except:
            return False

# Aplicar a mesma lógica de esconder no public para os outros modelos
@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ('number', 'student', 'total', 'status', 'due_date')
    list_filter = ('status', 'doc_type')
    search_fields = ('number', 'student__full_name')
    readonly_fields = ('number', 'issue_date')

    def has_module_permission(self, request):
        return connection.schema_name != 'public'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ('invoice', 'amount', 'method', 'validation_status', 'created_at')
    list_filter = ('validation_status', 'method')
    actions = ['validate_selected_payments']

    def has_module_permission(self, request):
        return connection.schema_name != 'public'

    @admin.action(description="Validar pagamentos selecionados (Liquidar Faturas)")
    def validate_selected_payments(self, request, queryset):
        for payment in queryset:
            payment.validate_payment(request.user)
        self.message_user(request, "Pagamentos validados e faturas liquidadas.")

# Registar os restantes modelos com proteção manual
if connection.schema_name != 'public':
    admin.site.register(FeeType)
    admin.site.register(BankAccount)
    admin.site.register(PaymentMethod)