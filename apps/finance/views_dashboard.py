from django.http import HttpResponseForbidden
import matplotlib.pyplot as plt
import io
import base64
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Q, F
from django.utils import timezone
from decimal import Decimal

# Imports da Aplicação
from apps.fiscal.models import DocumentoFiscal
from .models import Payment, Invoice
from apps.students.models import Enrollment
from .services import get_revenue_projection, get_revenue_risk_ranking
from apps.core.models import Role




@login_required
def daily_cash_flow(request):
    """
    PAINEL DE CONTROLE FINANCEIRO SOTARQ.
    Isolamento nativo via django-tenants (Schema-level).
    """
    if request.user.current_role not in ['ADMIN', 'DIRECTOR', 'DIRECT_FINANC']:
        return HttpResponseForbidden("Acesso restrito.")

    today = timezone.now().date()

    # --- 1. SINCRONIZAÇÃO DE STATUS ---
    # O Schema atual garante que só alteramos faturas desta escola
    Invoice.objects.filter(
        status='pending',
        due_date__lt=today
    ).update(status='overdue')

    # --- 2. MÉTRICAS FINANCEIRAS ---
    # Removidos todos os filtros '__tenant' e '__user__tenant'
    projected_revenue = Decimal(get_revenue_projection(request.tenant))

    cash_in_today = Payment.objects.filter(
        validation_status='validated',
        confirmed_at__date=today
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')

    total_overdue = Invoice.objects.filter(
        status='overdue'
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
    
    total_pending = Invoice.objects.filter(
        status='pending',
        due_date__gte=today
    ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

    # --- 3. OPERAÇÃO E CONFORMIDADE ---
    receipts_signed_24h = Payment.objects.filter(
        validation_status='validated',
        confirmed_at__gte=timezone.now() - timezone.timedelta(hours=24),
        hash_control__isnull=False 
    ).count()

    notifications_sent_today = Invoice.objects.filter(
        is_notified=True,
        due_date__lt=today
    ).count()

    # --- 4. BI E RISCO ---
    risk_students = get_revenue_risk_ranking(request.tenant)
    total_risk_value = risk_students.aggregate(total=Sum('total_overdue'))['total'] or Decimal('0.00')
    safe_revenue = max(0, projected_revenue - total_risk_value)

    # --- 5. GRÁFICOS ---
    # Gráfico 1: Tendência
    plt.figure(figsize=(5, 3))
    plt.bar(['Hoje', 'Projetado'], [float(cash_in_today), float(projected_revenue)], color=['#10b981', '#6366f1'])
    plt.title("Fluxo Real vs Projetado", fontsize=9, fontweight='bold')
    buf_tend = io.BytesIO()
    plt.savefig(buf_tend, format='png', bbox_inches='tight')
    graph_tendencia = base64.b64encode(buf_tend.getvalue()).decode('utf-8')
    plt.close()

    # Gráfico 2: Risco
    plt.figure(figsize=(5, 3))
    risk_values = [float(safe_revenue), float(total_risk_value)]
    if sum(risk_values) > 0:
        plt.pie(risk_values, labels=['Segura', 'Risco'], colors=['#10b981', '#ef4444'], 
                autopct='%1.1f%%', startangle=90)
        plt.gca().add_artist(plt.Circle((0,0), 0.70, fc='white'))
    plt.title("Qualidade da Receita", fontsize=9, fontweight='bold')
    buf_risk = io.BytesIO()
    plt.savefig(buf_risk, format='png', bbox_inches='tight')
    graph_risk = base64.b64encode(buf_risk.getvalue()).decode('utf-8')
    plt.close()

    # --- 6. AGT ---
    docs_pending_agt = DocumentoFiscal.objects.filter(
        atcud__isnull=True, 
        status='confirmed'
    ).count() 

    context = {
        'projected_revenue': projected_revenue,
        'cash_in_today': cash_in_today,
        'total_overdue': total_overdue,
        'total_pending': total_pending,
        'receipts_signed_24h': receipts_signed_24h,
        'notifications_sent_today': notifications_sent_today,
        'currency': "Kz",
        'projection_graph': graph_tendencia,
        'risk_graph': graph_risk,
        'risk_students': risk_students,
        'total_risk_value': total_risk_value,
        'safe_revenue': safe_revenue,
        'active_enrollments_count': Enrollment.objects.filter(status='active').count(),
        'docs_pending_agt': docs_pending_agt,
    }
    
    return render(request, 'finance/daily_dashboard.html', context)

