# apps/platform/metrics.py
from django.db.models import Sum, Count
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from apps.billing.models import SaaSInvoice
from apps.customers.models import Client, SubAgent
from apps.licenses.models import License

def get_saas_metrics():
    """Calcula KPIs reais de negócio para gestão do SaaS."""
    now = timezone.now()
    last_30_days = now - relativedelta(days=30)
    
    # MRR: Apenas faturas pagas (Cash Flow Real)
    mrr = SaaSInvoice.objects.filter(
        status='paid', 
        created_at__gte=last_30_days
    ).aggregate(total=Sum('amount'))['total'] or 0

    # Base de Clientes
    total_clients = Client.objects.exclude(schema_name='public').count()
    
    # Churn: Escolas com licença expirada mas que eram ativas
    expired_licenses = License.objects.filter(
        is_active=True, 
        expiry_date__lt=now.date()
    ).count()
    
    # Cálculos Seguros
    churn_rate = (expired_licenses / total_clients * 100) if total_clients > 0 else 0
    avg_ticket = mrr / total_clients if total_clients > 0 else 0
    
    # LTV (Lifetime Value): Previsão de quanto cada escola renderá
    if churn_rate > 0:
        ltv = avg_ticket / (churn_rate / 100)
    else:
        ltv = avg_ticket * 24  # Estimativa de 2 anos se não houver churn

    return {
        'mrr': mrr,
        'churn': round(churn_rate, 2),
        'ltv': round(ltv, 2),
        'active_schools': total_clients - expired_licenses,
        'total_clients': total_clients
    }



def get_subagent_performance():
    """Analisa a eficiência de cada parceiro na rede SOTARQ."""
    agents = SubAgent.objects.all().annotate(
        total_schools=Count('my_clients'),
        # MRR gerado apenas pelas faturas pagas dos clientes deste agente
        total_revenue=Sum('my_clients__saasinvoice__amount', 
                          filter=models.Q(my_clients__saasinvoice__status='paid')),
        # Taxa de Retenção (escolas ativas vs total trazido)
        active_schools=Count('my_clients', 
                             filter=models.Q(my_clients__is_active=True))
    )
    
    performance_data = []
    for agent in agents:
        retention = (agent.active_schools / agent.total_schools * 100) if agent.total_schools > 0 else 0
        performance_data.append({
            'name': agent.user.get_full_name(),
            'revenue': agent.total_revenue or 0,
            'schools': agent.total_schools,
            'retention': round(retention, 2),
            'commission': agent.get_total_earned() # Método que criamos antes
        })
    
    return sorted(performance_data, key=lambda x: x['revenue'], reverse=True)



