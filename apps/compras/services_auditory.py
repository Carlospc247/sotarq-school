# apps/compras/services_auditory.py
from django.db.models import Sum
from apps.finance.models import Invoice
from apps.compras.models import Purchase, Product
from apps.cafeteria.models import Transaction

class AuditoryService:
    @staticmethod
    def get_year_end_report(year):
        # 1. DRE Escolar (Receitas vs Despesas)
        receita_total = Invoice.objects.filter(due_date__year=year, status='paid').aggregate(Sum('total'))['total__sum'] or 0
        despesa_compras = Purchase.objects.filter(date__year=year, status='confirmed').aggregate(Sum('total_amount'))['total_amount__sum'] or 0
        
        # 2. Mapa de Inadimplência (Risco)
        valor_em_divida = Invoice.objects.filter(status__in=['pending', 'overdue']).aggregate(Sum('total'))['total__sum'] or 0
        alunos_devedores = Invoice.objects.filter(status='overdue').values('student').distinct().count()

        # 3. Relatório de Desperdício (Ajustes de Stock)
        # Analisamos movimentos do tipo ADJUST (Quebras/Validade)
        perda_stock = Product.objects.filter(movements__movement_type='ADJUST').aggregate(
            total_perda=Sum(models.F('movements__quantity') * models.F('cost_price'))
        )['total_perda'] or 0

        return {
            'dre': {
                'receita': receita_total,
                'despesas': despesa_compras,
                'ebitda': receita_total - despesa_compras - perda_stock
            },
            'risco': {
                'total_inadimplente': valor_em_divida,
                'qtd_devedores': alunos_devedores
            },
            'desperdicio': perda_stock
        }