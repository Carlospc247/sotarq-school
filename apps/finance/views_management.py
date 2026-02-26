# apps/finance/views_management.py
from datetime import timezone
from django.http import HttpResponseForbidden
from django.shortcuts import render
from django.utils.decorators import login_required
from apps.finance.models import Invoice
from apps.reports.services.finance_bi import EfficiencyEngine

@login_required
def staff_performance_dashboard(request):
    """
    Dashboard de Rigor: Avaliação da Secretaria.
    """
    if request.user.current_role not in ['ADMIN', 'DIRECTOR']:
        return HttpResponseForbidden("Acesso restrito à Direção Geral.")

    today = timezone.now()
    perf = EfficiencyEngine.get_staff_efficiency_score(today.month, today.year)
    
    return render(request, 'finance/management/performance.html', {
        'perf': perf,
        'critical_debtors': Invoice.objects.filter(status='overdue').order_by('-total')[:10]
    })