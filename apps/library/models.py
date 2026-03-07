# apps/library/models.py
from datetime import timedelta
from django.utils import timezone
from django.db import models
from apps.core.models import BaseModel, User
from decimal import Decimal




class Book(BaseModel):
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=255)
    isbn = models.CharField(max_length=20, unique=True, blank=True)
    barcode = models.CharField(max_length=50, unique=True)
    category = models.CharField(max_length=100)
    total_copies = models.PositiveIntegerField(default=1)
    available_copies = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.barcode} | {self.title}"

class Loan(BaseModel):
    class Status(models.TextChoices):
        ACTIVE = 'active', 'Emprestado'
        RETURNED = 'returned', 'Devolvido'
        OVERDUE = 'overdue', 'Em Atraso'
        LOST = 'lost', 'Extraviado'

    # Rigor: Vinculado ao User (Alunos, Professores, Staff)
    borrower = models.ForeignKey(
        User, 
        on_delete=models.CASCADE, 
        related_name='library_loans',
        null=True, # Adicione isto para a migração passar limpa
        blank=True
    )
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    loan_date = models.DateField(auto_now_add=True)
    expected_return_date = models.DateField()
    actual_return_date = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.ACTIVE)

    loan_duration_days = models.PositiveIntegerField(default=7, help_text="Prazo em dias definido pelo bibliotecário")
    notified_15_days = models.BooleanField(default=False, verbose_name="Notificado (Atraso > 15 dias)")

    def save(self, *args, **kwargs):
        if not self.pk: # Na criação
            self.expected_return_date = timezone.now().date() + timedelta(days=self.loan_duration_days)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.book.title} -> {self.borrower.get_full_name() or self.borrower.username}"



class LibraryConfig(models.Model):
    """Configuração global por Escola (Tenant)"""
    daily_fine_amount = models.DecimalField(max_digits=10, decimal_places=2, default=500.00) # Kz por dia
    max_loan_days = models.PositiveIntegerField(default=7)
    grace_period_days = models.PositiveIntegerField(default=1)

