# apps/cafeteria/analytics.py
from django.db.models import Sum, Q
from django.utils import timezone
from .models import CashSession, CafeteriaSale

class CafeteriaAuditor:
    @staticmethod
    def get_daily_executive_summary(tenant):
        hoje = timezone.now().date()
        # Filtra sessões do tenant que foram abertas hoje
        sessoes_hoje = CashSession.objects.filter(
            user__tenant=tenant,
            opened_at__date=hoje
        )

        # Agregação por Modalidade (Rigor SOTARQ)
        vendas_hoje = CafeteriaSale.objects.filter(session__in=sessoes_hoje)
        
        resumo_pagamentos = vendas_hoje.aggregate(
            cash=Sum('total_final', filter=Q(payment_method='CASH')),
            wallet=Sum('total_final', filter=Q(payment_method='WALLET')),
            multicaixa=Sum('total_final', filter=Q(payment_method='MULTICAIXA'))
        )

        # Auditoria de Quebras (Diferenças declaradas no fecho)
        quebras = sessoes_hoje.filter(status='closed').aggregate(
            total_falta=Sum('difference', filter=Q(difference__lt=0)),
            total_sobra=Sum('difference', filter=Q(difference__gt=0))
        )

        return {
            'total_bruto': (resumo_pagamentos['cash'] or 0) + (resumo_pagamentos['multicaixa'] or 0) + (resumo_pagamentos['wallet'] or 0),
            'por_metodo': {
                'cash': resumo_pagamentos['cash'] or 0,
                'wallet': resumo_pagamentos['wallet'] or 0,
                'multicaixa': resumo_pagamentos['multicaixa'] or 0,
            },
            'operacional': {
                'sessoes_abertas': sessoes_hoje.filter(status='open').count(),
                'total_quebras': quebras['total_falta'] or 0,
                'total_sobras': quebras['total_sobra'] or 0,
            }
        }