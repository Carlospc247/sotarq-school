# apps/finance/models.py
import logging
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel
#from apps.finance.services import PenaltyEngine
from apps.students.models import Student
from django.utils import timezone
from decimal import Decimal
from apps.core.utils import generate_document_number
from django.db.models import Sum
from apps.fiscal.models import DocType
from django.db import transaction, models




logger = logging.getLogger(__name__)

class PaymentType(models.TextChoices):
    CASH = 'CH', _('Dinheiro / Cash')
    TRANSFER = 'TR', _('Transferência Bancária')
    MULTICAIXA = 'MC', _('Referência Multicaixa')
    DEPOSIT = 'DP', _('Depósito Bancário')


class FeeType(models.Model):
    """
    Catálogo Estrito: Apenas Propinas, Matrículas e Reconfirmações.
    O valor é definido pelo Diretor no Admin.
    """
    name = models.CharField(max_length=100, help_text="Ex: Mensalidade, Matrícula, Reconfirmação")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    recurring = models.BooleanField(default=False, help_text="Marcar True para Propinas mensais")
    
    
    def __str__(self):
        return f"{self.name} - {self.amount} Kz"


class Invoice(models.Model):
    STATUS_CHOICES = (
        ('pending', _('Pendente')),
        ('paid', _('Pago')),
        ('cancelled', _('Cancelado')),
        ('overdue', _('Vencido')), # Practical addition
    )


    doc_type = models.CharField(max_length=2, choices=DocType.choices, default=DocType.FT)
    number = models.CharField(max_length=50, unique=True, editable=False)    
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='invoices')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    hash_control = models.CharField(max_length=255, blank=True, null=True, editable=False)
    
    issue_date = models.DateField(auto_now_add=True)
    due_date = models.DateField()

    is_notified = models.BooleanField(default=False)


    subtotal = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)
    
    # FK com o Fiscal: Rigor AGT
    tax_type = models.ForeignKey(
        'fiscal.TaxaIVAAGT', 
        on_delete=models.PROTECT, 
        null=True, blank=True,
        verbose_name="Regime de IVA Aplicável"
    )
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    # Lógica de Desconto Híbrido
    discount_value = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, help_text="Valor bruto ou % digitado")
    discount_is_pct = models.BooleanField(default=True, verbose_name="Desconto em %?")
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0.00, verbose_name="Valor real abatido")

    # Adicione esta FK ao seu modelo Invoice em finance/models.py
    fiscal_doc = models.OneToOneField(
        'fiscal.DocumentoFiscal', 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='invoice_comercial'
    )
    total = models.DecimalField(max_digits=15, decimal_places=2, default=0.00)

    waive_penalty = models.BooleanField(default=False) # Se True, ignora multas/juros
    penalty_waived_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, blank=True, 
        related_name='waived_invoices'
    )
    waive_reason = models.TextField(blank=True, null=True)
    
    def update_totals(self):
        """
        Motor de Cálculo Enterprise:
        1. Soma itens -> 2. Aplica Desconto -> 3. Calcula IVA -> 4. Resultado Final
        """
        self.subtotal = sum(item.amount for item in self.items.all())

        # A. Processamento do Desconto Híbrido
        if self.discount_is_pct:
            self.discount_amount = (self.subtotal * (self.discount_value / 100))
        else:
            self.discount_amount = self.discount_value

        base_apos_desconto = self.subtotal - self.discount_amount

        # B. Processamento do IVA via FK Fiscal
        if self.tax_type:
            # Cálculo conforme percentagem oficial da AGT
            self.tax_amount = (base_apos_desconto * (self.tax_type.tax_percentage / 100))
        else:
            self.tax_amount = 0

        # C. Valor Final (Líquido a Pagar)
        self.total = base_apos_desconto + self.tax_amount
        self.save()

    def save(self, *args, **kwargs):
        if not self.number:
            self.number = generate_document_number(self, self.doc_type)
        super().save(*args, **kwargs)
    
    def calculate_current_total(self):
        """Retorna o valor original + multas se estiver vencido."""
        from apps.finance.services import PenaltyEngine
        if self.status in ['pending', 'overdue'] and self.due_date < timezone.now().date():
            config = FinanceConfig.objects.first()
            if not config:
                return self.total # Retorna original se não houver config definida
                
            days_late = (timezone.now().date() - self.due_date).days
            
            if days_late > config.grace_period_days:
                multa = self.total * (config.late_fee_percentage / 100)
                juros = self.total * (config.daily_interest_rate / 100) * days_late
                return self.total + multa + juros
        return self.total
    
    @property
    def mora_data(self):
        """Cache temporário do cálculo de mora para evitar múltiplas consultas."""
        if not hasattr(self, '_mora_cache'):
            self._mora_cache = PenaltyEngine.calculate_invoice_mora(self)
        return self._mora_cache

    @property
    def current_multa(self):
        return self.mora_data[0]

    @property
    def current_juros(self):
        return self.mora_data[1]

    @property
    def current_total(self):
        return self.mora_data[2]
    
    @classmethod
    def update_overdue_invoices(cls):
        """
        Varre o sistema e marca faturas como 'overdue'.
        Ideal para rodar num cron job (Celery) todas as noites.
        """
        today = timezone.now().date()
        return cls.objects.filter(
            status='pending', 
            due_date__lt=today
        ).update(status='overdue')
    
    def __str__(self):
        return f"Inv #{self.number} - {self.student} [{self.get_status_display()}]"


class InvoiceItem(models.Model):
    """
    Line items within an invoice.
    """
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='items')
    fee_type = models.ForeignKey(FeeType, on_delete=models.SET_NULL, null=True)
    description = models.CharField(max_length=255) # Snapshot of fee name or custom
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f"{self.description} ({self.amount})"

class CashFlow(BaseModel):
    """
    Consolidação de Fluxo de Caixa Global da Escola.
    Unifica Entradas (Payments) e Saídas (Outflows/Despesas).
    """
    class TransactionType(models.TextChoices):
        INFLOW = 'IN', _('Entrada')
        OUTFLOW = 'OUT', _('Saída')

    description = models.CharField(max_length=255)
    amount = models.DecimalField(max_digits=15, decimal_places=2)
    transaction_type = models.CharField(max_length=3, choices=TransactionType.choices)
    
    # Origem do dinheiro
    payment = models.OneToOneField(
        'finance.Payment', on_delete=models.CASCADE, null=True, blank=True, related_name='cash_flow_entry'
    )
    outflow = models.OneToOneField(
        'finance.CashOutflow', on_delete=models.CASCADE, null=True, blank=True, related_name='cash_flow_entry'
    )
    
    # Categorização simples (Rigor Vistogest)
    category = models.CharField(max_length=100, help_text="Ex: Propinas, Salários, Manutenção")
    date = models.DateField(default=timezone.now)
    
    # Auditoria
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    class Meta:
        verbose_name = "Fluxo de Caixa"
        verbose_name_plural = "Fluxos de Caixa"
        ordering = ['-date', '-created_at']

    def __str__(self):
        prefix = "+" if self.transaction_type == self.TransactionType.INFLOW else "-"
        return f"{prefix} {self.amount} Kz - {self.description}"


class PaymentMethod(models.Model):
    """
    Define como a escola aceita pagamentos.
    Configurado uma vez no setup da escola.
    """
    name = models.CharField(max_length=50)
    method_type = models.CharField(
        max_length=2, 
        choices=PaymentType.choices, # Agora o Python já leu esta classe acima
        default=PaymentType.CASH
    )
    is_active = models.BooleanField(default=True)
    
    # Lógica de Automação
    requires_bank_account = models.BooleanField(default=False)
    requires_file_upload = models.BooleanField(default=True)
    auto_validate = models.BooleanField(default=False, help_text="Validar sem intervenção humana (ex: Referências)")

    def __str__(self):
        return f"{self.name} ({self.get_method_type_display()})"

class BankAccount(models.Model):
    """Contas Bancárias da Instituição (Substitui os 12 campos manuais)"""
    bank_name = models.CharField(max_length=50) # BAI, BFA, etc.
    iban = models.CharField(max_length=21, unique=True)
    account_holder = models.CharField(max_length=100, help_text="Nome do Titular")
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.bank_name} - {self.iban}"


class Payment(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name='payments')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT)
    reference = models.CharField(max_length=100, blank=True, help_text="Transaction ID or Receipt details")
    
    confirmed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    hash_control = models.CharField(max_length=255, blank=True, null=True, editable=False)

    
    proof_file = models.FileField(
        upload_to='payments/proofs/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name="Comprovativo de Pagamento"
    )

    receipt_pdf = models.FileField(
        upload_to='payments/receipts/%Y/%m/', 
        null=True, 
        blank=True,
        verbose_name="Recibo Oficial (PDF)"
    )
    class ValidationStatus(models.TextChoices):
        PENDING = 'pending', _('Aguardando Validação')
        VALIDATED = 'validated', _('Validado')
        REJECTED = 'rejected', _('Rejeitado')

    validation_status = models.CharField(
        max_length=20, 
        choices=ValidationStatus.choices, 
        default=ValidationStatus.PENDING
    )
    rejection_reason = models.TextField(blank=True, null=True, help_text="Motivo caso o comprovativo seja inválido")
    
    voided_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='voided_payments')
    voided_at = models.DateTimeField(null=True, blank=True)
    void_reason = models.TextField(blank=True, null=True)

    @transaction.atomic
    def void_payment(self, user, reason):
        """
        Anula um recebimento validado.
        Rigor: Reverte a fatura para 'pending' e invalida o hash RSA.
        """
        if self.validation_status != 'validated':
            raise ValueError("Apenas pagamentos validados podem ser estornados.")

        # 1. Reverter Fatura
        self.invoice.status = 'pending'
        self.invoice.save()

        # 2. Marcar Pagamento como Rejeitado/Anulado
        self.validation_status = 'rejected'
        self.voided_by = user
        self.voided_at = timezone.now()
        self.void_reason = reason
        
        # 3. Segurança: O PDF do recibo antigo deve ser "esquecido"
        self.receipt_pdf = None
        self.save()

        # 4. Log de Auditoria (Essencial para o Chefe saber o que houve)
        logger.warning(f"ESTORNO: Pagamento {self.id} anulado por {user.username}. Motivo: {reason}")
    


    def get_previous_hash(self):
        """
        Busca o hash do último recibo (RC/REC) validado para este Tenant.
        """
        last_valid_payment = Payment.objects.filter(
            validation_status='validated',
            hash_control__isnull=False
        ).order_by('-confirmed_at').first()
        
        return last_valid_payment.hash_control if last_valid_payment else ""


    def generate_provisional_slip(self):
        """
        Gera os metadados para o Slip de Matrícula Provisória.
        Rigor: Só para alunos 'graduated' que acabaram de limpar a dívida.
        """
        student = self.invoice.student
        enrollment = student.enrollments.filter(status='graduated').last()
        
        if enrollment:
            next_grade = enrollment.grade_level.next_level()
            return {
                'student_name': student.full_name,
                'process_number': student.registration_number,
                'next_grade': next_grade.name if next_grade else "Nível Seguinte",
                'amount_paid': self.amount,
                'date': self.confirmed_at,
                'status_text': "VAGA RESERVADA - SUJEITO A CONFIRMAÇÃO NA SECRETARIA",
                'auth_hash': self.hash_control[:12] if self.hash_control else "OFFLINE-VALIDATION"
            }
        return None


    def validate_payment(self, user):
        from django.db import transaction, connection
        from django.utils import timezone
        from .utils.pdf_generator import generate_receipt_pdf
        from .tasks import task_process_payment_notifications
        
        # Imports Locais dos Módulos Acadêmico e Core
        from apps.students.models import EnrollmentRequest, Enrollment
        from apps.academic.models import AcademicYear, Class, VacancyRequest
        from apps.core.models import Notification, User, Role

        with transaction.atomic():
            # 1. Validação Financeira (Padrão)
            self.validation_status = self.ValidationStatus.VALIDATED
            self.confirmed_by = user
            self.confirmed_at = timezone.now()
            
            # Gera o Recibo PDF (Se implementado)
            # generate_receipt_pdf(self)
            
            self.invoice.status = 'paid'
            self.invoice.save()
            self.save()

            from .models import CashFlow # Import local se não quiser mover a classe para cima
            CashFlow.objects.create(
                description=f"Recebimento: {self.invoice.number} - {self.invoice.student.full_name}",
                amount=self.amount,
                transaction_type='IN',
                payment=self,
                category="Mensalidades/Serviços",
                created_by=user 
            )

            # 2. Orquestração de Matrícula (Se for Candidatura)
            enroll_req = EnrollmentRequest.objects.filter(invoice=self.invoice).first()
            
            if enroll_req and enroll_req.status == 'pending_payment':
                student = enroll_req.student
                
                # A. Ativar o Aluno e Utilizador (Converte Candidato -> Aluno)
                student.is_active = True
                student.is_suspended = False
                student.save()
                
                if student.user:
                    student.user.is_active = True
                    student.user.save()

                # B. Buscar Ano Letivo Ativo
                current_year = AcademicYear.objects.filter(is_active=True).first()
                if not current_year:
                    # Fallback crítico
                    current_year = AcademicYear.objects.order_by('-start_date').first()

                # C. ALGORITMO DE AUTO-ALOCAÇÃO DE TURMA
                candidate_classes = Class.objects.filter(
                    academic_year=current_year,
                    grade_level=enroll_req.grade_level,
                    # O curso é obrigatório no modelo Class? Se não, filtrar pelo grade_level é suficiente
                    # pois grade_level já está ligado a um course.
                )

                selected_class = None
                
                # Verifica vagas disponíveis (Capacity > Occupancy)
                for klass in candidate_classes:
                    if klass.has_vacancy: # Usa a property do modelo Class
                        selected_class = klass
                        break
                
                if selected_class:
                    # CASO A: Vaga Automática (Matrícula Direta)
                    enrollment = Enrollment.objects.create(
                        student=student,
                        academic_year=current_year,
                        course=enroll_req.course, # Campo obrigatório do modelo Enrollment
                        class_room=selected_class,
                        status='active'
                    )
                    
                    enroll_req.status = 'enrolled'
                    enroll_req.save()
                    
                    # Notifica Sucesso ao Aluno
                    Notification.objects.create(
                        user=student.user,
                        title="Matrícula Confirmada! 🎉",
                        message=f"Bem-vindo! Fostes alocado na turma {selected_class.name}.",
                        link="/portal/dashboard/",
                        icon="check-circle"
                    )

                else:
                    # CASO B: Sem Vaga (Fluxo de Aprovação Manual - Despacho)
                    # Cria a Matrícula sem turma (estado 'pending_placement')
                    enrollment = Enrollment.objects.create(
                        student=student,
                        academic_year=current_year,
                        course=enroll_req.course,
                        class_room=None, # Aguardando decisão (permitido pelo ajuste anterior)
                        status='pending_placement'
                    )
                    
                    # Registo de Auditoria para o Diretor (usando message)
                    sys_msg = f"Solicitação automática gerada via Pagamento #{self.id}. Validado por: {user.username}."
                    
                    # Cria o Pedido de Vaga usando apenas os campos do seu modelo
                    vacancy = VacancyRequest.objects.create(
                        student=student,
                        target_grade=enroll_req.grade_level,
                        status='pending',
                        message=sys_msg, 
                        is_resolved=False
                    )

                    # Notificações para Staff (Secretaria)
                    # Filtra secretários do tenant atual
                    secretaries = User.objects.filter(tenant=self.invoice.student.user.tenant, current_role=Role.Type.SECRETARY)
                    for sec in secretaries:
                        Notification.objects.create(
                            user=sec,
                            title="⚠️ Solicitação de Vaga Pendente",
                            message=f"O aluno {student.full_name} pagou mas não tem vaga automática na {enroll_req.grade_level}. Analise o pedido.",
                            link=f"/academic/vacancy/manage/{vacancy.id}/", # URL que criaremos a seguir
                            icon="clock"
                        )
                    
                    # Atualiza estado da candidatura
                    enroll_req.status = 'processing'
                    enroll_req.save()
                    
                    # Feedback Transparente ao Aluno
                    Notification.objects.create(
                        user=student.user,
                        title="Pagamento Recebido - Em Análise",
                        message="O pagamento foi confirmado. O teu processo foi enviado à Direção Pedagógica para atribuição de vaga manual.",
                        icon="info"
                    )

            # 3. Lógica de Desbloqueio de Devedores (Dívidas Antigas)
            first_item = self.invoice.items.first()
            if first_item and "Acordo de Dívida" in first_item.description:
                if self.invoice.student.is_suspended:
                    self.invoice.student.is_suspended = False
                    self.invoice.student.save()

        # Disparo da Task de Notificação Assíncrona
        task_process_payment_notifications.delay(self.id, connection.schema_name)

        
    
    def __str__(self):
        return f"{self.amount} for {self.invoice.number}"


class PaymentGatewayConfig(models.Model):
    """
    Configurado pelo Admin da Escola.
    Cada escola (tenant) preenche os seus próprios dados.
    """
    # Referência Multicaixa (Ex: ProxyPay, Pagamento de Serviços)
    mc_entity_code = models.CharField(max_length=10, verbose_name="Entidade Multicaixa")
    mc_api_key = models.CharField(max_length=255, blank=True, null=True)
    
    # Cartão (Stripe, Flutterwave ou similar)
    card_api_public_key = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"Configuração de Gateways - Entidade {self.mc_entity_code}"




class FinanceConfig(models.Model):
    """Configuração de multas por escola (Tenant)"""
    late_fee_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=10.00) # Ex: 10%
    daily_interest_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.1) # Ex: 0.1% ao dia
    grace_period_days = models.PositiveIntegerField(default=5) # Dias de carência

class DebtAgreement(models.Model):
    """Acordos de Dívida para alunos inadimplentes"""
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    total_debt_original = models.DecimalField(max_digits=12, decimal_places=2)
    discount_applied = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    installments_count = models.PositiveIntegerField(default=1) # Número de prestações
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    contract_pdf = models.FileField(upload_to='agreements/%Y/', null=True, blank=True)
    hash_control = models.CharField(max_length=255, blank=True) # Para integridade AGT
    is_activated = models.BooleanField(default=False) # Só vira True após o 1º pagamento
    
    def check_activation(self):
        """Verifica se a primeira parcela foi paga para ativar o acordo e desbloquear o aluno."""
        # CORREÇÃO: Usamos .filter() sucessivos para procurar os dois termos no mesmo campo
        first_installment = Invoice.objects.filter(
            items__description__icontains=f"Prestação 1/"
        ).filter(
            items__description__icontains=f"Acordo #{self.id}"
        ).first()
        
        if first_installment and first_installment.status == 'paid':
            self.is_activated = True
            self.save()
            
            # Desbloqueio do aluno
            student = self.student
            student.is_blocked = False # Garante que o campo existe no modelo Student
            student.save()
            return True
        return False



class CashSession(BaseModel):
    """
    Controla o Ciclo de Vida do Caixa (Abertura -> Sangrias/Suprimentos -> Fecho).
    """
    STATUS_CHOICES = [('open', 'Aberto'), ('closed', 'Fechado')]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='cash_sessions')
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, verbose_name="Fundo de Maneio")
    closing_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, verbose_name="Saldo Final Declarado")

    expected_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    reported_balance = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    difference = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    justification = models.TextField(null=True, blank=True, help_text="Justificativa em caso de divergência")
    
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='open')

    def __str__(self):
        return f"Sessão #{self.id} - {self.user.username} ({self.get_status_display()})"

    class Meta:
        verbose_name = "Sessão de Caixa"
        verbose_name_plural = "Sessões de Caixa"


class CashInflow(BaseModel):
    """
    Motor de Suprimento: Reforço de caixa (trocos ou aporte).
    """
    session = models.ForeignKey(CashSession, on_delete=models.CASCADE, related_name='inflows')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, default="Reforço de Trocos")
    authorized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return f"+{self.amount} Kz (Suprimento)"


class CashOutflow(BaseModel):
    """
    Motor de Sangria: Regista saídas de dinheiro em espécie durante o turno.
    """
    session = models.ForeignKey(CashSession, on_delete=models.CASCADE, related_name='outflows')
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, help_text="Ex: Compra de material de limpeza")
    authorized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"-{self.amount} Kz ({self.description})"


