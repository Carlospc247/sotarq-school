# apps/finance/views_dashboard.py
import matplotlib.pyplot as plt
import io
import base64
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Sum, Q, F
from django.utils import timezone
from decimal import Decimal

from apps.fiscal.models import DocumentoFiscal
from apps.inventory.tasks import get_monthly_depreciation_cost
from .models import Payment, Invoice
from apps.students.models import Enrollment
from .services import get_revenue_projection, get_revenue_risk_ranking

@staff_member_required
def daily_cash_flow(request):
    """
    PAINEL DE CONTROLE FINANCEIRO: Visão de 360º para o Diretor (Produção).
    """
    today = timezone.now().date()
    
    # 1. MÉTRICAS FINANCEIRAS REAIS
    cash_in_today = Payment.objects.filter(
        validation_status='validated',
        confirmed_at__date=today
    ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    total_overdue = Invoice.objects.filter(
        status='overdue'
    ).aggregate(Sum('total'))['total__sum'] or Decimal('0.00')
    
    total_pending = Invoice.objects.filter(
        status='pending',
        due_date__gte=today
    ).aggregate(Sum('total'))['total__sum'] or Decimal('0.00')

    # 2. MÉTRICAS DE OPERAÇÃO
    receipts_signed_24h = Payment.objects.filter(
        validation_status='validated',
        confirmed_at__gte=timezone.now() - timezone.timedelta(hours=24),
        hash_control__isnull=False
    ).count()

    notifications_sent_today = Invoice.objects.filter(
        is_notified=True,
        due_date__lt=today
    ).count()

    # 3. INTELIGÊNCIA PREDITIVA (BI)
    projection_next_month = Decimal(get_revenue_projection())
    risk_students = get_revenue_risk_ranking()
    
    # Cálculo do valor total em risco (soma da dívida dos top devedores)
    total_risk_value = risk_students.aggregate(Sum('total_overdue'))['total_overdue__sum'] or Decimal('0.00')
    safe_revenue = max(0, projection_next_month - total_risk_value)

    # --- 4. GRÁFICO 1: TENDÊNCIA (BARRA) ---
    plt.figure(figsize=(5, 3))
    plt.bar(['Hoje', 'Projetado'], [float(cash_in_today), float(projection_next_month)], color=['#10b981', '#6366f1'])
    plt.title("Fluxo Real vs Projetado", fontsize=9, fontweight='bold')
    
    buf_tendencia = io.BytesIO()
    plt.savefig(buf_tendencia, format='png', bbox_inches='tight')
    graph_tendencia = base64.b64encode(buf_tendencia.getvalue()).decode('utf-8')
    buf_tendencia.close()
    plt.close()

    # --- 5. GRÁFICO 2: COMPOSIÇÃO DE RISCO (DONUT) ---
    plt.figure(figsize=(5, 3))
    risk_labels = ['Receita Segura', 'Em Risco']
    risk_values = [float(safe_revenue), float(total_risk_value)]
    
    # Só gera se houver valores para evitar erro de divisão por zero
    if sum(risk_values) > 0:
        plt.pie(risk_values, labels=risk_labels, colors=['#10b981', '#ef4444'], 
                autopct='%1.1f%%', startangle=90, pctdistance=0.85, textprops={'fontsize': 8})
        # Transforma em Donut
        centre_circle = plt.Circle((0,0), 0.70, fc='white')
        plt.gca().add_artist(centre_circle)
    else:
        plt.text(0.5, 0.5, 'Sem dados de risco', ha='center', va='center')
        
    plt.title("Qualidade da Receita Projetada", fontsize=9, fontweight='bold')
    
    buf_risk = io.BytesIO()
    plt.savefig(buf_risk, format='png', bbox_inches='tight')
    graph_risk = base64.b64encode(buf_risk.getvalue()).decode('utf-8')
    buf_risk.close()
    plt.close()

    # 1. Custo Operacional Invisível (Depreciação de Equipamentos)
    monthly_depreciation = get_monthly_depreciation_cost()
    
    # 2. Receita Líquida Real (Entradas - Depreciação)
    # Importante para o Diretor não gastar dinheiro que é necessário para repor ativos
    lucro_real_projetado = projection_next_month - monthly_depreciation
    
    # 3. Status de Submissão AGT
    docs_pending_agt = DocumentoFiscal.objects.filter(atcud__isnull=True, status='confirmed').count()

    context = {
        'cash_in_today': cash_in_today,
        'total_overdue': total_overdue,
        'total_pending': total_pending,
        'receipts_signed_24h': receipts_signed_24h,
        'notifications_sent_today': notifications_sent_today,
        'currency': "Kz",
        'projection_next_month': projection_next_month,
        'projection_graph': graph_tendencia,
        'risk_graph': graph_risk,
        'risk_students': risk_students,
        'total_risk_value': total_risk_value,
        'safe_revenue': safe_revenue, # ADICIONADO: Essencial para o card estratégico
        'active_enrollments_count': Enrollment.objects.filter(status='active').count(),
        'monthly_depreciation': monthly_depreciation,
        'lucro_real_projetado': lucro_real_projetado,
        'docs_pending_agt': docs_pending_agt,
    }
    
    return render(request, 'finance/daily_dashboard.html', context)



