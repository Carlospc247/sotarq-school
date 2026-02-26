from django.contrib import admin, messages
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from .models import SaaSInvoice
from apps.licenses.models import License
from apps.core.admin_mixins import SaaSOnlyAdminMixin

@admin.register(SaaSInvoice)
class SaaSInvoiceAdmin(SaaSOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('reference', 'tenant', 'amount', 'status', 'created_at', 'expiry_preview')
    list_filter = ('status', 'created_at', 'tenant')
    search_fields = ('reference', 'tenant__name')
    # Proteção: Faturas de faturamento não devem ser editadas manualmente após criadas
    readonly_fields = ('reference', 'tenant', 'amount', 'created_at', 'updated_at')
    
    actions = ['force_activate_license']

    def expiry_preview(self, obj):
        """Mostra até quando a licença irá se for paga hoje."""
        return timezone.now().date() + relativedelta(months=1)
    expiry_preview.short_description = "Projeção de Renovação"

    @admin.action(description='🔥 ATIVAÇÃO FORÇADA: Confirmar Pagamento e Renovar Licença')
    def force_activate_license(self, request, queryset):
        """
        Esta ação faz o que o Webhook faria: 
        1. Marca como Pago
        2. Localiza/Cria a Licença
        3. Estende o prazo por 30 dias
        """
        updated_count = 0
        for invoice in queryset.filter(status='pending'):
            # 1. Atualizar Fatura
            invoice.status = 'paid'
            invoice.payment_date = timezone.now()
            invoice.save()

            # 2. Atualizar Licença
            lic, created = License.objects.get_or_create(
                tenant=invoice.tenant,
                is_active=True,
                defaults={'expiry_date': timezone.now().date()}
            )
            
            # Lógica de Extensão
            base_date = max(lic.expiry_date, timezone.now().date())
            lic.expiry_date = base_date + relativedelta(months=1)
            lic.save()
            
            updated_count += 1

        self.message_user(
            request, 
            f"Sucesso: {updated_count} faturas confirmadas e licenças renovadas.",
            messages.SUCCESS
        )

    def has_delete_permission(self, request, obj=None):
        # Faturas financeiras nunca devem ser apagadas (Audit Trail)
        return False