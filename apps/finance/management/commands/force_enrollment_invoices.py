import traceback
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone
from apps.students.models import Student, Enrollment, EnrollmentRequest
from apps.finance.models import Invoice, InvoiceItem, FeeType
from apps.academic.models import AcademicYear

class Command(BaseCommand):
    help = 'Força a geração de Faturas de Matrícula/Reconfirmação para todos os alunos ativos no ano atual.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Iniciando processamento em massa..."))
        
        # 1. Obter Ano Académico Corrente
        academic_year = AcademicYear.objects.filter(is_active=True).first()
        if not academic_year:
            self.stdout.write(self.style.ERROR("ERRO: Nenhum Ano Académico activo encontrado."))
            return

        # 2. Buscar todos os alunos com matrículas activas ou pedidos pagos/aprovados
        # Filtramos alunos que JÁ NÃO tenham uma fatura vinculada ao pedido de matrícula deste ano
        enrollments = Enrollment.objects.filter(
            academic_year=academic_year, 
            status='active'
        ).select_related('student', 'course')

        created_count = 0
        skipped_count = 0

        for enrollment in enrollments:
            student = enrollment.student
            course = enrollment.course

            # RIGOR: Verificar se já existe fatura de matrícula para este aluno no ano atual
            # Evita duplicidade se rodar o script duas vezes
            already_has_invoice = Invoice.objects.filter(
                student=student,
                items__description__icontains="Matrícula",
                issue_date__year=timezone.now().year
            ).exists()

            if already_has_invoice:
                skipped_count += 1
                continue

            try:
                with transaction.atomic():
                    # A. Determinar o tipo de taxa (Usa o default do Curso que configuramos)
                    fee_type = course.default_enrollment_fee_type
                    if not fee_type:
                        self.stdout.write(self.style.ERROR(f"Pular: Curso {course.name} sem taxa de matrícula definida."))
                        continue

                    # B. Criar a Invoice (Pendente até que o operador valide o pagamento)
                    invoice = Invoice.objects.create(
                        student=student,
                        status='pending',
                        due_date=timezone.now().date(),
                        tax_type=course.taxa_iva, # Rigor AGT: Puxa o IVA do Curso
                        subtotal=0, # Será calculado no save/update_totals
                        total=0
                    )

                    # C. Criar o Item da Fatura
                    InvoiceItem.objects.create(
                        invoice=invoice,
                        fee_type=fee_type,
                        description=f"{fee_type.name} - {academic_year.name}",
                        amount=fee_type.amount
                    )

                    # D. Forçar Recálculo de Totais (IVA + Descontos)
                    invoice.update_totals()

                    # E. Vincular ao EnrollmentRequest se existir
                    enrollment_request = EnrollmentRequest.objects.filter(
                        student=student,
                        status__in=['pending', 'paid'],
                        course=course,
                        invoice__isnull=True
                    ).first()

                    if enrollment_request:
                        enrollment_request.invoice = invoice
                        enrollment_request.save()
                        self.stdout.write(self.style.SUCCESS(f"   -> Vinculado ao Pedido de {enrollment_request.get_request_type_display()}"))

                    created_count += 1
                    self.stdout.write(self.style.SUCCESS(f"Fatura {invoice.number} gerada para {student.full_name}"))
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Falha ao processar {student.full_name}: {str(e)}"))
                traceback.print_exc()
                # traceback.print_exc() # Use para debug se necessário

        self.stdout.write(self.style.SUCCESS(
            f"PROCESSO CONCLUÍDO: {created_count} faturas geradas, {skipped_count} puladas (já existiam)."
        ))


# Se quiser rodar apenas para a escola 'excellence'
#python manage.py tenant_command force_enrollment_invoices --schema=excellence

# Se quiser rodar para TODAS as escolas (Tenants) de uma vez
#python manage.py all_tenants_command force_enrollment_invoices