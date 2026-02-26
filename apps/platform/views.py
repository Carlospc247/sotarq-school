# apps/platform/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.utils import timezone # ESSENCIAL
from datetime import timedelta     # ESSENCIAL

from apps.audit.models import AuditLog
from apps.customers.models import Client, SubAgent
from apps.licenses.models import License
from .metrics import get_saas_metrics, get_subagent_performance

@user_passes_test(lambda u: u.is_superuser)
def global_admin_dashboard(request):
    metrics = get_saas_metrics()
    
    next_week = timezone.now().date() + timedelta(days=7)
    alerts = License.objects.filter(
        expiry_date__range=[timezone.now().date(), next_week],
        is_active=True
    ).select_related('tenant')

    return render(request, 'platform/dashboard.html', {
        'metrics': metrics,
        'alerts': alerts
    })

@user_passes_test(lambda u: u.is_superuser)
def agent_commission_manager(request):
    """Gestão de pagamentos para subagentes."""
    # Aqui você implementará a lógica de pagamento de comissões
    return render(request, 'platform/agent_commissions.html', {
        'subagents': SubAgent.objects.all()
    })

@user_passes_test(lambda u: u.is_superuser)
def agent_performance_report(request):
    """Relatório detalhado de performance da rede de parceiros."""
    performance = get_subagent_performance()
    return render(request, 'platform/agent_performance.html', {
        'performance': performance
    })

@user_passes_test(lambda u: u.is_superuser)
def license_management_hub(request):
    manual_activations = AuditLog.objects.filter(action='LICENSE_MANUAL_ACTIVATE')[:50]
    
    at_risk_tenants = Client.objects.filter(
        license__expiry_date__lte=timezone.now().date() + timedelta(days=5),
        license__is_active=True
    ).distinct()

    return render(request, 'platform/license_hub.html', {
        'at_risk': at_risk_tenants,
        'audit_logs': manual_activations,
        'subagents': SubAgent.objects.all()
    })

@user_passes_test(lambda u: u.is_superuser)
def force_block_tenant(request):
    """View dedicada para o POST de bloqueio forçado."""
    if request.method == 'POST':
        tenant_id = request.POST.get('tenant_id')
        reason = request.POST.get('reason')
        tenant = get_object_or_404(Client, id=tenant_id)
        
        License.objects.filter(tenant=tenant).update(is_active=False)
        tenant.is_active = False
        tenant.save()
        
        AuditLog.objects.create(
            user=request.user,
            action='FORCE_TENANT_BLOCK',
            details=f"Escola {tenant.name} bloqueada manualmente. Motivo: {reason}"
        )
        messages.warning(request, f"Escola {tenant.name} bloqueada com rigor.")
    return redirect('platform:license_hub')

