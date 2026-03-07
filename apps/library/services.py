from django.utils import timezone
from apps.finance.models import Invoice, InvoiceItem
from .models import Loan, LibraryConfig
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from apps.finance.models import Invoice


# apps/library/services.py
from decimal import Decimal
from django.utils import timezone
from apps.finance.models import Invoice, InvoiceItem



class LibraryEngine:
    @staticmethod
    def register_return(loan_id):
        """Regista devolução física. Apenas log de atraso, sem faturas."""
        loan = Loan.objects.get(id=loan_id)
        today = timezone.now().date()
        
        loan.actual_return_date = today
        loan.status = Loan.Status.RETURNED
        
        # Apenas marcamos se houve atraso para fins de histórico/bloqueio
        if today > loan.expected_return_date:
            loan.had_delay = True # Assumindo campo booleano no model Loan
            loan.days_overdue = (today - loan.expected_return_date).days
        
        # Reposição de Stock
        loan.book.available_copies += 1
        loan.book.save()
        loan.save()



class LibrarySecurityService:
    @staticmethod
    def can_borrow(user):
        """
        Rigor Administrativo SOTARQ: Universal (Alunos e Staff).
        Verifica se o utente está apto a levar um novo livro.
        """
        today = timezone.now().date()
        
        # 1. Bloqueio por atraso crítico (Mais de 7 dias)
        critical_overdue = Loan.objects.filter(
            borrower=user,
            status__in=['active', 'overdue'],
            expected_return_date__lt=today - timezone.timedelta(days=7)
        ).exists()

        if critical_overdue:
            return False, "ACESSO NEGADO: Existe atraso crítico de mais de 7 dias."

        # 2. Verificação de bloqueios específicos do Aluno
        if hasattr(user, 'student_profile'):
            student = user.student_profile
            if student.is_suspended:
                return False, "ACESSO NEGADO: Aluno suspenso (Financeiro)."
            if student.is_blocked_for_fraud:
                return False, f"BLOQUEIO DE SEGURANÇA: {student.fraud_lock_details}"
        
        # 3. Verificação de conta ativa (Geral para Staff/Alunos)
        if not user.is_active:
            return False, "ACESSO NEGADO: Este perfil de utente está inativo."
            
        return True, "Aprovado"

    @staticmethod
    def process_return_merit(loan):
        """
        Garante o prêmio de 10 pontos por responsabilidade na devolução.
        Agora que merit_points existe no banco, o incremento é seguro.
        """
        if loan.actual_return_date and loan.actual_return_date <= loan.expected_return_date:
            if hasattr(loan.borrower, 'student_profile'):
                student = loan.borrower.student_profile
                # Incremento de mérito acadêmico
                student.merit_points += 10
                student.save(update_fields=['merit_points'])
                return True
        return False


