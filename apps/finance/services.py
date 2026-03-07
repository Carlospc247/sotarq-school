# apps/finance/services.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone
from django.db.models import Count, Sum, Q, F, Case, When, Value, BooleanField
from datetime import timedelta
from io import BytesIO

# Imports do Django
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

# Imports da Aplicação
from apps.students.models import Enrollment, Student

# Imports para PDF
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Q, Avg





class DebtRefinancingService:
    """Motor de Engenharia Financeira para Acordos de Dívida."""
    
    @staticmethod
    @transaction.atomic
    def create_agreement(student, installments_count=3, discount=Decimal('0.00')):
        # 1. Somar todas as faturas vencidas ou pendentes
        from apps.finance.models import DebtAgreement, Invoice
        overdue_invoices = Invoice.objects.filter(
            student=student, 
            status__in=['pending', 'overdue'],
            due_date__lt=timezone.now().date()
        )
        
        total_debt = sum(inv.total for inv in overdue_invoices)
        
        if total_debt <= 0:
            raise ValueError("O aluno não possui dívidas vencidas para refinanciamento.")

        # 2. Criar o registo do Acordo
        agreement = DebtAgreement.objects.create(
            student=student,
            total_debt_original=total_debt,
            discount_applied=discount,
            installments_count=installments_count,
            is_active=True
        )

        # 3. Cancelar faturas antigas
        overdue_invoices.update(status='cancelled')

        # 4. Gerar as novas faturas (Prestações)
        amount_after_discount = total_debt - discount
        installment_value = (amount_after_discount / installments_count).quantize(Decimal('0.01'))
        
        for i in range(1, installments_count + 1):
            Invoice.objects.create(
                student=student,
                total=installment_value,
                due_date=timezone.now().date() + timedelta(days=30 * (i - 1)),
                status='pending',
                notes=f"Prestação {i}/{installments_count} do Acordo #{agreement.id}"
            )
        return agreement

# --- Funções de BI e Certidões ---

def get_revenue_projection(tenant):
    """
    Projeção baseada no catálogo FeeType (Rigor SOTARQ).
    Em vez de procurar no Curso, somamos as taxas recorrentes e multiplicamos pelos alunos.
    """
    from apps.finance.models import FeeType
    from apps.students.models import Student
    
    # 1. Busca o valor total de todas as taxas marcadas como recorrentes (Mensalidades)
    monthly_fees_sum = FeeType.objects.filter(
        recurring=True
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
    
    # 2. Conta os alunos ativos do Tenant (Escola)
    active_students_count = Student.objects.filter(
        user__tenant=tenant,
        is_active=True
    ).count()
    
    # Resultado: Soma das Propinas x Número de Alunos
    return monthly_fees_sum * active_students_count



def get_revenue_risk_ranking(tenant): # ARGUMENTO OBRIGATÓRIO
    """Identifica alunos com risco de inadimplência isolado por Escola."""
    from apps.students.models import Student # Import local para evitar circularity
    churn_limit = timezone.now() - timedelta(days=30)
    
    return Student.objects.filter(
        user__tenant=tenant, # RIGOR DE SEGURANÇA
        enrollments__status='active'
    ).annotate(
        total_overdue=Sum('invoices__total', filter=Q(invoices__status='overdue')),
        last_access=F('user__last_login'),
        is_churn_risk=Case(
            When(user__last_login__lt=churn_limit, then=Value(True)),
            default=Value(False),
            output_field=BooleanField(),
        )
    ).filter(total_overdue__gt=0).order_by('-is_churn_risk', '-total_overdue')[:10]

    

def generate_clearance_certificate(student, academic_year):
    """Gera PDF de Quitação Anual."""
    from apps.finance.models import Invoice
    pending_debt = Invoice.objects.filter(
        student=student,
        academic_year=academic_year,
        status__in=['pending', 'overdue']
    ).exists()

    if pending_debt:
        return None

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    styles = getSampleStyleSheet()
    style_center = ParagraphStyle('Center', parent=styles['Normal'], alignment=1, leading=16)
    
    elements = []
    school_name = getattr(student.user, 'tenant', 'Sotarq School')
    
    elements.append(Paragraph(f"<b>{str(school_name).upper()}</b>", style_center))
    elements.append(Paragraph("Direção Administrativa e Financeira", style_center))
    elements.append(Spacer(1, 40))
    
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, fontSize=18, spaceAfter=30)
    elements.append(Paragraph("CERTIDÃO DE QUITAÇÃO ANUAL", title_style))

    content = (
        f"Certificamos que o(a) aluno(a) <b>{student.full_name}</b>, "
        f"processo nº <b>{student.registration_number}</b>, no Ano Lectivo <b>{academic_year.name}</b>, "
        f"encontra-se em situação de <b>PLENA QUITAÇÃO</b> financeira."
    )
    elements.append(Paragraph(content, styles['Normal']))
    
    today = timezone.now()
    elements.append(Spacer(1, 60))
    elements.append(Paragraph(f"Malanje, {today.day} de Janeiro de {today.year}", style_center))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf



def check_promotion_eligibility(student):
    """
    Verifica se o aluno pode ser promovido financeiramente.
    Regra SOTARQ: Nenhuma fatura pending ou overdue.
    """
    from apps.finance.models import Invoice

    return not Invoice.objects.filter(
        student=student, 
        status__in=['pending', 'overdue']
    ).exists()



@transaction.atomic
def generate_annual_budget_proforma(student, academic_year, include_kit=True):
    """
    Gera Proforma (FP) baseada nos valores REAIS definidos pela Direção Financeira.
    Busca no catálogo FeeType.
    """
    from apps.finance.models import Invoice, InvoiceItem, FeeType

    # 1. Cria a Proforma no Banco
    fp = Invoice.objects.create(
        student=student,
        doc_type='FP',
        due_date=timezone.now().date(),
        status='pending',
        notes=f"Orçamento Estimado para o Ano Lectivo {academic_year.name}"
    )

    # 2. Busca de Valores Oficiais (Rigor SOTARQ)
    # Procuramos os nomes exatos no catálogo definido pelo Diretor Financeiro
    
    # A. Matrícula ou Reconfirmação
    term_search = "Matrícula" if not student.is_active else "Reconfirmação"
    fee_admission = FeeType.objects.filter(name__icontains=term_search).first()
    
    if fee_admission:
        InvoiceItem.objects.create(
            invoice=fp, 
            description=f"Taxa de {term_search}", 
            amount=fee_admission.amount
        )
    else:
        # Se não existir, o Diretor Financeiro falhou na configuração
        raise ValueError(f"ERRO: A taxa de {term_search} não foi configurada no sistema. Tente mais tarde")

    # B. Propinas (Multiplicamos o valor mensal recorrente por 10 meses)
    fee_tuition = FeeType.objects.filter(name__icontains="Propina", recurring=True).first()
    if fee_tuition:
        total_tuition = fee_tuition.amount * 10
        InvoiceItem.objects.create(
            invoice=fp, 
            description=f"Projeção de Propinas (10 Meses x {fee_tuition.amount:,.2f} Kz)", 
            amount=total_tuition
        )

    # C. Kit de Uniformes (Se solicitado)
    if include_kit:
        fee_kit = FeeType.objects.filter(name__icontains="Kit").first()
        if fee_kit:
            InvoiceItem.objects.create(
                invoice=fp, 
                description=f"Kit Escolar Oficinal ({fee_kit.name})", 
                amount=fee_kit.amount
            )

    # 3. Consolidação e Cálculo Final
    fp.total = sum(item.amount for item in fp.items.all())
    fp.save()

    # 4. Geração do PDF de Elite com o design SOTARQExporter
    #from .utils import SOTARQExporter
    from apps.finance.utils.pdf_generator import SOTARQExporter
    return SOTARQExporter.generate_fiscal_document(fp, 'FP')



class PenaltyEngine:
    """
    Motor Supremo de Penalizações SOTARQ.
    Calcula Multas e Juros com base na política rigorosa do Tenant (Escola).
    """

    @staticmethod
    def calculate_invoice_mora(invoice):
        """
        Retorna (valor_multa, valor_juros, total_atualizado)
        Rigor SOTARQ: 
        1. Verifica Isenção Manual (waive_penalty).
        2. Valida Status e Data de Vencimento.
        3. Aplica Carência (grace_period_days).
        4. Calcula Multa Fixa e Juros Diários Acumulados.
        """
        from .models import FinanceConfig
        
        # 1. Verificação de Isenção ou Estado Inválido para Mora
        if invoice.waive_penalty or invoice.status == 'paid' or invoice.status == 'cancelled':
            return Decimal('0.00'), Decimal('0.00'), invoice.total

        hoje = timezone.now().date()
        
        # 2. Se ainda não venceu, não há cálculo de mora
        if hoje <= invoice.due_date:
            return Decimal('0.00'), Decimal('0.00'), invoice.total

        # 3. Importação tardia do modelo para evitar Importação Circular
        from .models import FinanceConfig
        config = FinanceConfig.objects.first()
        
        # Fallback caso a configuração do Tenant ainda não tenha sido criada
        if not config:
            return Decimal('0.00'), Decimal('0.00'), invoice.total

        days_late = (hoje - invoice.due_date).days
        
        # 4. Verificação do Período de Carência (Definido pelo Diretor)
        if days_late <= config.grace_period_days:
            return Decimal('0.00'), Decimal('0.00'), invoice.total

        # 5. Cálculo Matemático Rigoroso
        # Multa Fixa: Percentagem única sobre o valor base
        multa = invoice.total * (config.late_fee_percentage / 100)

        # Juros Diários: Taxa ao dia multiplicada pelo total de dias de atraso
        juros = invoice.total * (config.daily_interest_rate / 100) * days_late

        total_atualizado = invoice.total + multa + juros
        
        # 6. Arredondamento Financeiro (Enterprise Standard: 2 casas decimais)
        arredondar = Decimal('0.01')
        return (
            multa.quantize(arredondar), 
            juros.quantize(arredondar), 
            total_atualizado.quantize(arredondar)
        )




class RiskAnalysisService:
    @staticmethod
    def project_monthly_loss(tenant):
        """
        Motor de Projeção SOTARQ:
        Calcula o potencial de arrecadação baseado nos FeeTypes recorrentes.
        """
        from apps.finance.models import FeeType, Invoice

        today = timezone.now().date()
        
        # 1. RECEITA PROJETADA (Baseada em FeeTypes Recorrentes)
        # Somamos todos os FeeTypes marcados como recorrentes (mensalidades)
        base_monthly_fee = FeeType.objects.filter(
            recurring=True
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0.00')
        
        # Contamos alunos ativos no tenant
        active_students_count = Student.objects.filter(
            user__tenant=tenant,
            is_active=True
        ).count()
        
        # Previsão Bruta = Alunos Ativos * Soma das Propinas Recorrentes
        projected_revenue = base_monthly_fee * active_students_count
        
        # 2. VALOR EM RISCO (Faturas Overdue no Tenant)
        total_risk_value = Invoice.objects.filter(
            student__user__tenant=tenant,
            status='overdue'
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')
        
        # 3. RECEITA SEGURA (O que já foi pago este mês)
        safe_revenue = Invoice.objects.filter(
            student__user__tenant=tenant,
            status='paid',
            issue_date__month=today.month,
            issue_date__year=today.year
        ).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

        return {
            'projection_next_month': float(projected_revenue),
            'total_risk_value': float(total_risk_value),
            'safe_revenue': float(safe_revenue),
            'risk_percentage': round(float((total_risk_value / projected_revenue) * 100), 2) if projected_revenue > 0 else 0
        }
    
