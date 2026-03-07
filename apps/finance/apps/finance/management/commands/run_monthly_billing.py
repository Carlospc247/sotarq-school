# apps/finance/management/commands/run_monthly_billing.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction
from apps.finance.models import Invoice, InvoiceItem, FeeType
from apps.academic.models import GradeLevelPricing, AcademicYear
from apps.students.models import Enrollment
import logging

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Rigor SOTARQ: Gera faturas de propinas para alunos ativos baseadas no preçário da classe.'

    def handle(self, *args, **options):
        today = timezone.now().date()
        # Referência do mês (Ex: "Março/2026")
        month_ref = today.strftime('%B/%Y')
        
        # 1. Busca o Ano Letivo Ativo (Rigor Académico)
        academic_year = AcademicYear.objects.filter(is_active=True).first()
        if not academic_year:
            self.stdout.write(self.style.ERROR("ERRO: Nenhum Ano Letivo ativo encontrado."))
            return

        # 2. Filtra matrículas ativas no ano corrente
        active_enrollments = Enrollment.objects.filter(
            status='active', 
            academic_year=academic_year
        ).select_related('student', 'grade_level')

        self.stdout.write(self.style.SUCCESS(f"Iniciando faturamento de {month_ref}..."))

        created_count = 0
        skipped_count = 0

        for enrollment in active_enrollments:
            student = enrollment.student
            grade = enrollment.grade_level

            # 3. Busca o Preçário específico para a classe dele (Rigor SOTARQ)
            pricing = GradeLevelPricing.objects.filter(
                grade_level=grade,
                fee_type__recurring=True,
                fee_type__is_active=True,
                fee_type__name__icontains="Propina"
            ).first()

            if not pricing:
                logger.warning(f"SOTARQ SCHOOL: Preçário ausente para {grade.name} (Aluno: {student.full_name})")
                skipped_count += 1
                continue

            # 4. Verificação de Duplicidade: Evita faturar o mesmo mês/serviço duas vezes
            already_billed = Invoice.objects.filter(
                student=student,
                items__description__icontains=month_ref,
                items__fee_type=pricing.fee_type
            ).exists()

            if already_billed:
                skipped_count += 1
                continue

            # 5. Processamento Transacional (Tudo ou Nada)
            try:
                with transaction.atomic():
                    # Cria a Fatura (O save() gera o número e hash AGT automaticamente)
                    invoice = Invoice.objects.create(
                        student=student,
                        status='pending',
                        due_date=today + timezone.timedelta(days=5), # Prazo SOTARQ: 5 dias
                        tax_type=pricing.fee_type.tax_type # IVA do catálogo
                    )

                    # Cria o Item da Fatura
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        fee_type=pricing.fee_type,
                        description=f"{pricing.fee_type.name} - {month_ref}",
                        amount=pricing.amount
                    )

                    # Atualiza Totais, Descontos e IVA (Motor Enterprise do modelo Invoice)
                    invoice.update_totals()
                    
                created_count += 1
            except Exception as e:
                logger.error(f"FALHA CRÍTICA no faturamento do aluno {student.id}: {str(e)}")
                self.stdout.write(self.style.ERROR(f"Erro em {student.full_name}: {str(e)}"))

        self.stdout.write(self.style.SUCCESS(
            f"Faturamento concluído: {created_count} faturas geradas, {skipped_count} ignoradas."
        ))