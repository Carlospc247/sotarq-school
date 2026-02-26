# apps/reports/services/finance_bi.py
from django.db.models import Sum, Count
from apps.finance.models import Invoice, Payment
from django.utils import timezone

class MonthlyExplorationEngine:
    @staticmethod
    def get_monthly_summary(month, year, tenant_schema):
        """
        Consolidação de todos os tipos de documentos SOTARQ.
        Faturamento Bruto vs. Receita Realizada vs. Custos.
        """
        # Filtragem base por período
        base_invoices = Invoice.objects.filter(issue_date__month=month, issue_date__year=year)
        
        # 1. RECEITA REALIZADA (Dinheiro que entrou de verdade)
        receita_paga = Payment.objects.filter(
            confirmed_at__month=month, 
            confirmed_at__year=year,
            validation_status='validated'
        ).aggregate(total=Sum('amount'))['total'] or 0

        # 2. FATURAMENTO EM DÍVIDA (FT e ND não pagas)
        em_divida = base_invoices.filter(
            doc_type__in=['FT', 'ND'],
            status__in=['pending', 'overdue']
        ).aggregate(total=Sum('total'))['total'] or 0

        # 3. CUSTOS (AF - Autofacturação)
        saidas_af = base_invoices.filter(doc_type='AF').aggregate(total=Sum('total'))['total'] or 0

        # 4. ANULAÇÕES (NC - Nota de Crédito)
        estornos_nc = base_invoices.filter(doc_type='NC').aggregate(total=Sum('total'))['total'] or 0

        # 5. INFORMATIVOS (FP - Proforma)
        proformas = base_invoices.filter(doc_type='FP').aggregate(total=Sum('total'))['total'] or 0

        return {
            'periodo': f"{month}/{year}",
            'receita_realizada': receita_paga,
            'inadimplencia': em_divida,
            'custos_operacionais': saidas_af,
            'estornos': estornos_nc,
            'proforma_total': proformas,
            'lucro_liquido': receita_paga - saidas_af - estornos_nc,
            'faturamento_potencial': receita_paga + em_divida,
            'doc_count': base_invoices.count()
        }




class EfficiencyEngine:
    @staticmethod
    def get_staff_efficiency_score(month, year):
        """
        Calcula o Índice de Eficiência de Cobrança (IEC).
        Rigor: Quantas FT (Faturas) viraram RC (Recibos).
        """
        invoices = Invoice.objects.filter(
            issue_date__month=month, 
            issue_date__year=year,
            doc_type__in=['FT', 'FR'] # Faturas e Vendas a Pronto
        )
        
        total_issued = invoices.count()
        total_value_issued = invoices.aggregate(Sum('total'))['total'] or 0
        
        total_paid_invoices = invoices.filter(status='paid').count()
        total_value_received = invoices.filter(status='paid').aggregate(Sum('total'))['total'] or 0
        
        # Cálculo da Taxa de Conversão (Eficiência)
        if total_issued > 0:
            efficiency_rate = (total_paid_invoices / total_issued) * 100
        else:
            efficiency_rate = 0
            
        # Nota SOTARQ (0 a 10)
        score = round(efficiency_rate / 10, 1)
        
        return {
            'total_issued': total_issued,
            'total_paid': total_paid_invoices,
            'value_issued': total_value_issued,
            'value_received': total_value_received,
            'efficiency_rate': efficiency_rate,
            'score': score,
            'performance_label': "EXCELENTE" if score >= 9 else "BOM" if score >= 7 else "CRÍTICO"
        }


