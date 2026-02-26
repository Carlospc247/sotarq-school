# apps/core/views_admin.py

import logging
from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone
from django.urls import reverse

# Imports Internos (SOTARQ Architecture)
from apps.academic.models import VacancyRequest
from apps.compras.models import Purchase, SchoolStoreSale
from apps.finance.models import Invoice
from .models import Notification, Role

# Configuração de Logging para Auditoria
logger = logging.getLogger(__name__)

# --- CONTROLE DE PERMISSÕES ---
def is_manager_check(user):
    """
    Verifica permissão de gestão (Admin ou Diretor) no contexto do Tenant.
    Ref: Django Authentication System
    """
    if not user.is_authenticated:
        return False
    MANAGEMENT_ROLES = [Role.Type.ADMIN, Role.Type.DIRECTOR]
    return user.is_superuser or user.current_role in MANAGEMENT_ROLES



@login_required
@user_passes_test(is_manager_check, login_url='/', redirect_field_name=None)
def final_audit_report(request):
    """
    Relatório de Auditoria Final (DRE Simplificado).
    Escopo: Apenas dados do Tenant atual.
    """
    today = timezone.now().date()
    tenant = request.user.tenant

    # 1. Inadimplência Real (Filtro por Tenant)
    inadimplencia_qs = Invoice.objects.filter(
        student__user__tenant=tenant, # Tenant Constraint
        status__in=['pending', 'overdue'],
        due_date__lt=today
    )
    
    total_inadimplente = inadimplencia_qs.aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    qtd_devedores = inadimplencia_qs.values('student').distinct().count()

    # 2. Operação de Loja (Filtro por Tenant)
    # Assumindo que SchoolStoreSale tem vínculo com tenant ou via student/user
    total_receita_loja = SchoolStoreSale.objects.filter(
        student__user__tenant=tenant,
        is_paid=True
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')

    # 3. Compras/Stock (Filtro por Tenant)
    # Assumindo Purchase vinculado ao Tenant
    total_compras_stock = Purchase.objects.filter(
        tenant=tenant, 
        status='confirmed'
    ).aggregate(total=Sum('total_amount'))['total'] or Decimal('0.00')
    
    ebitda = total_receita_loja - total_compras_stock
    
    # Placeholder para lógica futura de desperdício
    desperdicio = Decimal('0.00')

    context = {
        'year': today.year,
        'audit': {
            'dre': {
                'receita': total_receita_loja,
                'despesas': total_compras_stock,
                'ebitda': ebitda,
            },
            'risco': {
                'total_inadimplente': total_inadimplente,
                'qtd_devedores': qtd_devedores,
            },
            'desperdicio': desperdicio,
        },
        'page_title': 'Auditoria Financeira'
    }
    
    return render(request, 'core/admin/final_audit.html', context)


@login_required
@user_passes_test(is_manager_check, login_url='/', redirect_field_name=None)
def notify_debtors_bulk(request):
    """
    Ação de Cobrança em Massa.
    Escopo: Apenas devedores do Tenant atual.
    Usa bulk_create para performance em alta escala.
    """
    if request.method == "POST":
        today = timezone.now().date()
        tenant = request.user.tenant
        
        # 1. Filtra faturas vencidas DO TENANT ATUAL
        invoices_to_notify = Invoice.objects.filter(
            student__user__tenant=tenant, # Tenant Constraint
            status__in=['pending', 'overdue'],
            due_date__lt=today,
            is_notified=False
        ).select_related('student__user')

        if not invoices_to_notify.exists():
            messages.info(request, "Não existem novos devedores para notificar neste momento.")
            return redirect('core:final_audit')

        notifications_to_create = []
        invoice_ids_to_update = []

        msg_template = (
            "AVISO DE AUDITORIA: Detetamos faturas pendentes na sua conta. "
            "Regularize via Multicaixa ou Secretaria para evitar suspensão."
        )

        # 2. Prepara objetos em memória
        for inv in invoices_to_notify:
            notifications_to_create.append(
                Notification(
                    user=inv.student.user,
                    title="⚠️ PENDÊNCIA FINANCEIRA DETETADA",
                    message=f"{msg_template} Ref Fatura: {inv.number}",
                    link=reverse('portal:financial_dashboard') if hasattr(inv, 'get_absolute_url') else '#'
                )
            )
            invoice_ids_to_update.append(inv.id)

        try:
            with transaction.atomic():
                # Bulk Create: Executa 1 query INSERT para N notificações
                Notification.objects.bulk_create(notifications_to_create)
                
                # Bulk Update: Executa 1 query UPDATE para N faturas
                Invoice.objects.filter(id__in=invoice_ids_to_update).update(is_notified=True)
                
                count = len(notifications_to_create)
                logger.info(f"Cobrança em massa executada por {request.user.username}: {count} notificações enviadas.")
                messages.success(request, f"Execução Concluída: {count} notificações de cobrança enviadas.")
        
        except Exception as e:
            logger.error(f"Erro Crítico Auditoria Bulk: {str(e)}")
            messages.error(request, "Falha na execução em massa. Operação revertida.")

        return redirect('core:final_audit')
    
    return redirect('core:final_audit')


