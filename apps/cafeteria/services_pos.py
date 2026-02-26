# apps/cafeteria/services_pos.py
from decimal import Decimal
from django.utils import timezone
from .models import CashSession, Transaction

class POSManager:
    @staticmethod
    def get_current_session(user):
        """Retorna a sessão aberta do operador atual."""
        return CashSession.objects.filter(user=user, status='open').first()

    @staticmethod
    def close_session(session, reported_cash):
        """
        Fecho de Caixa com Rigor de Auditoria.
        Calcula a diferença entre o esperado e o declarado.
        """
        # Soma entradas por tipo (CASH, WALLET, MULTICAIXA)
        totals = session.transactions.aggregate(
            total=models.Sum('amount')
        )['total'] or Decimal('0.00')
        
        # Rigor: Soma abertura + suprimentos - sangrias
        expected = session.opening_balance + totals + \
                   (session.inflows.aggregate(s=models.Sum('amount'))['s'] or 0) - \
                   (session.outflows.aggregate(s=models.Sum('amount'))['s'] or 0)
        
        session.expected_balance = expected
        session.reported_balance = reported_cash
        session.difference = reported_cash - expected
        session.status = 'closed'
        session.closed_at = timezone.now()
        session.save()
        
        return session