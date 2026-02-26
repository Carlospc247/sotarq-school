# apps/finance/analytics.py
from apps.finance.models import Invoice

def calculate_payment_risk_score(student):
    """
    Rigor SOTARQ: Analisa probabilidade de inadimplência.
    Utilizado para bloquear acesso ao Portal ou Transporte Preventivamente.
    """
    last_invoices = Invoice.objects.filter(student=student).order_by('-due_date')[:6]
    if not last_invoices: return 0

    delays = []
    for inv in last_invoices:
        if inv.status == 'paid' and hasattr(inv, 'payment_date'):
            delay = (inv.payment_date.date() - inv.due_date).days
            delays.append(max(0, delay))
        elif inv.status in ['pending', 'overdue']:
            delays.append(30) # Penalidade máxima por dívida aberta

    # Média ponderada de atrasos (Rigor Matemático)
    risk_score = (sum(delays) / (len(last_invoices) * 30)) * 100
    return min(100, risk_score)

