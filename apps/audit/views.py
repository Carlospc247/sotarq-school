from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import connection
from .models import AuditLog
from django.contrib import messages
from .models import SecurityAlert



@login_required
def audit_logs(request):
    """
    Sistema de Auditoria Dual: 
    1. Global (SaaS Owner) no schema 'public'.
    2. Local (Diretor) no schema do Tenant.
    """
    is_public_schema = connection.schema_name == 'public'

    # SEGURANÇA: Se alguém tentar entrar no schema 'public' e não for Superuser Global
    if is_public_schema and not request.user.is_superuser:
        raise PermissionDenied("Acesso exclusivo ao Administrador Central.")

    # SEGURANÇA: No Tenant, apenas quem tem cargo de Diretor/Admin pode ver
    if not is_public_schema and not (request.user.is_staff or request.user.is_superuser):
        raise PermissionDenied("Você não tem permissão para auditar esta instituição.")

    # Filtros
    action_query = request.GET.get('action', '')
    user_query = request.GET.get('user', '')

    # Graças ao django-tenants, o .all() aqui já filtra automaticamente 
    # os logs apenas da escola atual se não estivermos no public.
    logs_list = AuditLog.objects.select_related('user', 'content_type').all()

    if action_query:
        logs_list = logs_list.filter(action=action_query)
    if user_query:
        logs_list = logs_list.filter(user__username__icontains=user_query)

    paginator = Paginator(logs_list, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'actions': ['CREATE', 'UPDATE', 'DELETE', 'LOGIN'],
        'current_filters': {'action': action_query, 'user': user_query},
        'is_global_view': is_public_schema
    }
    
    return render(request, 'audit/logs.html', context)



@login_required
def security_alerts_list(request):
    """
    Rigor SOTARQ: Lista alertas de segurança (logins suspeitos).
    Apenas superusuários ou diretores podem ver.
    """
    if not request.user.is_staff and not request.user.is_superuser:
        raise PermissionDenied

    alerts = SecurityAlert.objects.all().select_related('user').order_by('-created_at')
    
    return render(request, 'audit/security_alerts.html', {
        'alerts': alerts
    })

@login_required
def resolve_alert(request, alert_id):
    """Marca um incidente de segurança como resolvido após análise."""
    if not request.user.is_staff and not request.user.is_superuser:
        raise PermissionDenied

    alert = get_object_or_404(SecurityAlert, id=alert_id)
    alert.is_resolved = True
    alert.save()
    
    messages.success(request, f"Alerta de {alert.user.username} marcado como resolvido.")
    return redirect('audit:security_alerts')


