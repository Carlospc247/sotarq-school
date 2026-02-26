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
        """Regista devolução com cálculo de multa automático."""
        loan = Loan.objects.get(id=loan_id)
        today = timezone.now().date()
        config = LibraryConfig.objects.first()
        
        loan.actual_return_date = today
        loan.status = Loan.Status.RETURNED
        
        if today > loan.expected_return_date:
            days_late = (today - loan.expected_return_date).days
            total_fine = days_late * config.daily_fine_amount
            
            # Geração de Fatura Rigorosa
            inv = Invoice.objects.create(
                student=loan.student,
                total=total_fine,
                due_date=today,
                doc_type='FT' # Fatura Direta
            )
            InvoiceItem.objects.create(
                invoice=inv,
                description=f"Multa Biblioteca: {loan.book.title} ({days_late} dias)",
                amount=total_fine
            )
        
        loan.book.available_copies += 1
        loan.book.save()
        loan.save()


class LibrarySecurityService:
    @staticmethod
    def can_borrow(student):
        """
        Verifica se o aluno está apto a requisitar livros.
        Regra: Nenhuma multa de biblioteca pendente há mais de 15 dias.
        """
        fifteen_days_ago = timezone.now().date() - timedelta(days=15)
        
        critical_fines = Invoice.objects.filter(
            student=student,
            items__description__icontains="Multa por Atraso",
            status__in=['pending', 'overdue'],
            issue_date__lt=fifteen_days_ago
        ).exists()

        if critical_fines:
            return False, "Bloqueio: Existem multas de biblioteca por liquidar há mais de 15 dias."
        
        if student.is_suspended:
            return False, "Bloqueio: O acesso do aluno está suspenso globalmente."
            
        return True, "Aprovado"

    @staticmethod
    def process_return_merit(loan):
        """
        Atribui pontos de mérito por devolução no prazo.
        """
        if loan.actual_return_date <= loan.expected_return_date:
            student = loan.student
            # Incrementa 10 pontos de mérito (MOCK: Campo adicionado ao Student)
            student.merit_points = (student.merit_points or 0) + 10
            student.save(update_fields=['merit_points'])
            return True
        return False

