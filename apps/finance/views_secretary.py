# apps/finance/views_secretary.py
from decimal import Decimal
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from apps.academic.models import AcademicYear, Class
from apps.academic.views import is_manager_check
from apps.core.models import Role
from apps.finance.models import FinanceConfig
from django.core.exceptions import PermissionDenied
from .models import FeeType
from apps.reports.finance.utils_reports import CashClosingReport
from apps.students.models import Student
from .models import CashInflow, CashOutflow, CashSession, Payment, Invoice, InvoiceItem, PaymentType, PaymentMethod


import logging
logger = logging.getLogger(__name__)



@login_required
def secretary_finance_dashboard(request):
    """
    Operação de Caixa Central SOTARQ: Controle total de liquidez académica.
    """
    if request.user.current_role not in ['SECRETARY', 'DIRECT_ADMIN', 'ADMIN']:
        return HttpResponseForbidden("Acesso restrito à Secretaria e Administração.")

    today = timezone.now().date()
    
    # 1. Recuperação da Sessão de Caixa Ativa
    session = CashSession.objects.filter(user=request.user, status='open').last()
    
    # 2. Inteligência de Cálculo de Saldo
    cash_total = Decimal('0.00')
    
    if session:
        cash_payments = Payment.objects.filter(
            confirmed_by=request.user,
            confirmed_at__date=today,
            method__method_type=PaymentType.CASH,
            validation_status='validated'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        total_inflow = session.inflows.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        total_outflow = session.outflows.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        cash_total = (session.opening_balance + cash_payments + total_inflow) - total_outflow

    # 3. Métricas de Operação Académica
    pending_validations = Payment.objects.filter(
        validation_status='pending'
    ).select_related('invoice', 'invoice__student').order_by('created_at')

    recent_actions = Payment.objects.filter(
        confirmed_by=request.user, 
        confirmed_at__date=today
    ).select_related('invoice__student').order_by('-confirmed_at')[:5]

    # --- CORREÇÃO AQUI ---
    # Como o modelo Class não tem 'status', contamos turmas sem professor como "pendentes"
    pending_classes_count = Class.objects.filter(main_teacher__isnull=True).count()
    
    context = {
        'active_cash_session': session,
        'pending_validations_count': pending_validations.count(),
        'pending_classes_count': pending_classes_count,
        'pending_validations': pending_validations,
        'cash_total': cash_total,
        'user_is_high_director': request.user.current_role in ['ADMIN', 'DIRECTOR', 'PEDAGOGIC'],
        'is_director': True, 
        'recent_actions': recent_actions,
        'available_fees': FeeType.objects.all(), 
    }
    
    return render(request, 'finance/secretary/dashboard.html', context)


# Em apps/finance/views_secretary.py
def global_search_2(request):
    query = request.GET.get('q', '').strip()
    if not query or len(query) < 2:
        return HttpResponse("") 

    students = Student.objects.filter(
        full_name__icontains=query
    ).prefetch_related(
        'enrollments__class_room__grade_level',
        'enrollments__course'
    )[:10] 
    
    # CORREÇÃO: Verifique se este caminho existe exatamente assim
    return render(request, 'finance/global_search_2.html', {'students': students})



@login_required
@transaction.atomic
def process_manual_payment(request):
    # SEGURANÇA: Verificar se o operador tem uma sessão aberta AGORA
    session = CashSession.objects.filter(user=request.user, status='open').last()
    if not session:
        messages.error(request, "ERRO: Operação bloqueada. Você não possui um turno de trabalho aberto.")
        return redirect('finance:secretary_dashboard')
    
    if request.method == "POST":
        # 1. Captura de Dados com Rigor
        student_id = request.POST.get('student_id')
        fee_type_id = request.POST.get('fee_type_id')
        quantity = int(request.POST.get('quantity', 1))
        start_month = int(request.POST.get('start_month'))
        method_code = request.POST.get('payment_method')

        # 2. Recuperação de Objetos Base
        student = get_object_or_404(Student, id=student_id)
        fee_type = get_object_or_404(FeeType, id=fee_type_id)
        payment_method = get_object_or_404(PaymentMethod, method_code=method_code, is_active=True)
        
        # 3. Inteligência de Preço SOTARQ (Hierarquia Académica vs Financeira)
        is_propina = "propina" in fee_type.name.lower() or "mensalidade" in fee_type.name.lower()
        unit_price = fee_type.amount  # Valor padrão do catálogo financeiro

        if is_propina:
            # Busca matrícula ativa para aplicar o preço calculado (Base + % da Classe)
            enrollment = student.enrollments.filter(
                status='active', 
                academic_year__is_active=True
            ).select_related('course', 'class_room__grade_level').first()
            
            if enrollment:
                if enrollment.class_room and enrollment.class_room.grade_level:
                    # Preço da 10ª, 11ª, 12ª etc (com o incremento percentual)
                    unit_price = enrollment.class_room.grade_level.calculated_monthly_fee
                else:
                    # Preço base do curso (aluno matriculado mas sem turma)
                    unit_price = enrollment.course.monthly_fee

        total_amount = unit_price * quantity

        # 4. Criação da Fatura Mãe
        invoice = Invoice.objects.create(
            student=student,
            amount=total_amount,
            status='paid',
            description=f"Liquidação: {quantity}x {fee_type.name}",
            issue_date=timezone.now()
        )

        # 5. Distribuição por Competência (Garante auditoria de meses individuais)
        for i in range(quantity):
            # Lógica de rotação de meses (12 + 1 vira 1)
            competence_month = ((start_month + i - 1) % 12) + 1
            
            InvoiceItem.objects.create(
                invoice=invoice,
                description=f"{fee_type.name} - Mês {competence_month}",
                amount=unit_price,
                quantity=1,
                competence_month=competence_month if is_propina else None
            )

        # 6. Registro do Pagamento e Validação Automática
        payment = Payment.objects.create(
            invoice=invoice,
            amount=total_amount,
            method=payment_method,
            confirmed_by=request.user,
            confirmed_at=timezone.now(),
            validation_status='validated'
        )

        # 7. Acionamento do Motor de Baixa (MonthlyControl)
        # O método validate_payment deve ler os InvoiceItems para baixar cada mês
        payment.validate_payment(request.user)

        messages.success(request, f"Sucesso! {quantity} mês(es) liquidado(s) para {student.full_name} no valor de {total_amount:,.2f} Kz.")
        return redirect('finance:print_invoice', invoice_id=invoice.id)
        #return redirect('finance:secretary_dashboard')

@login_required
def print_invoice_view(request, invoice_id):
    """
    Interface de Saída SOTARQ: Renderiza a fatura para impressão imediata.
    """
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Validação de Segurança: Apenas o dono do caixa ou admin visualiza
    if not request.user.is_staff and invoice.confirmed_by != request.user:
         return HttpResponseForbidden("Não tem permissão para imprimir esta fatura.")

    try:
        # Aqui chamamos o seu motor de exportação
        from .utils_reports import SOTARQExporter 
        
        exporter = SOTARQExporter(invoice)
        pdf_content = SOTARQExporter.generate_fiscal_document(invoice, doc_type_code='FT')

        response = HttpResponse(pdf_content, content_type='application/pdf')
        
        # 'inline' abre no navegador (permitindo Ctrl+P), 'attachment' baixa o arquivo.
        filename = f"FATURA_{invoice.invoice_number}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        
        return response

    except Exception as e:
        logger.error(f"Erro ao imprimir fatura {invoice_id}: {str(e)}")
        messages.error(request, "Erro ao gerar o documento de impressão.")
        return redirect('finance:secretary_dashboard')

      
@login_required
def generate_budget_view(request, student_id):
    """
    Motor de Projeção Orçamentária SOTARQ.
    Gera uma Fatura Proforma (FP) com os custos previstos para o ano lectivo.
    """
    # 1. Segurança de Tenant e Obtenção do Aluno
    student = get_object_or_404(Student, id=student_id)
    
    # 2. Obtenção do Ano Lectivo Ativo
    active_year = AcademicYear.objects.filter(is_active=True).first()
    if not active_year:
        messages.error(request, "ERRO CRÍTICO: Não existe um ano lectivo ativo para gerar o orçamento.")
        return redirect('students:student_list')

    # 3. Lógica de Parâmetros (Opcional: incluir kit escolar?)
    include_kit = request.GET.get('kit', 'false').lower() == 'true'

    try:
        # 4. Chamada ao Serviço de Engenharia Financeira
        # Este método cria a Invoice(FP) e retorna o binário do PDF
        from .services import generate_annual_budget_proforma
        pdf_content = generate_annual_budget_proforma(
            student=student, 
            academic_year=active_year, 
            include_kit=include_kit
        )

        # 5. Entrega do Documento
        response = HttpResponse(pdf_content, content_type='application/pdf')
        filename = f"PROFORMA_{student.registration_number}_{active_year.name}.pdf".replace("/", "-")
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    except ValueError as e:
        messages.error(request, str(e))
        return redirect('students:student_list')
    except Exception as e:
        messages.error(request, f"Erro inesperado ao gerar proforma: {str(e)}")
        return redirect('students:student_list')


@login_required
@transaction.atomic
def open_cash_daily(request):
    """Abre o turno e declara o Fundo de Maneio."""
    if request.method == 'POST':
        initial_amount = Decimal(request.POST.get('initial_amount', '0.00'))
        
        # Rigor: Impede abertura dupla para o mesmo operador
        if CashSession.objects.filter(user=request.user, status='open').exists():
            messages.error(request, "Já existe um caixa aberto para o seu utilizador.")
            return redirect('finance:secretary_dashboard')

        CashSession.objects.create(
            user=request.user,
            opening_balance=initial_amount,
            status='open'
        )
        messages.success(request, f"Caixa aberto. Fundo de Maneio: {initial_amount:,.2f} Kz")
    
    return redirect('finance:secretary_dashboard')


@login_required
@transaction.atomic
def close_cash_daily(request):
    """
    Motor de Fecho de Turno SOTARQ v2.2.
    Rigor: Confronto de Saldos, Auditoria WhatsApp e Geração de Mapa PDF.
    """
    session = CashSession.objects.filter(user=request.user, status='open').last()
    if not session or request.method != 'POST':
        return redirect('finance:secretary_dashboard')

    # 1. Recuperação e Validação de Dados do Formulário
    reported_balance = Decimal(request.POST.get('reported_balance', '0'))
    justification = request.POST.get('justification', '')
    today = timezone.now().date()

    # 2. Re-Cálculo de Auditoria (Rigor Anti-Fraude)
    # Buscamos todos os pagamentos validados do operador hoje
    payments = Payment.objects.filter(
        confirmed_by=request.user, 
        confirmed_at__date=today,
        validation_status='validated'
    ).select_related('invoice', 'invoice__student', 'method')

    # Totais por método para o PDF
    totals = {
        p_type: payments.filter(method__method_type=p_type).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00') 
        for p_type in PaymentType.values
    }

    cash_sales = totals.get(PaymentType.CASH, Decimal('0.00'))
    total_in = session.inflows.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    total_out = session.outflows.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    
    # Fórmula Mestra
    expected_balance = (session.opening_balance + cash_sales + total_in) - total_out
    difference = reported_balance - expected_balance

    # 3. Disparo de Alerta de Divergência Crítica
    if difference != 0:
        alert_msg = (
            f"🚨 *ALERTA DE DIVERGÊNCIA DE CAIXA*\n"
            f"Escola: {request.tenant.name}\n"
            f"Operador: {request.user.get_full_name()}\n"
            f"Esperado: {expected_balance:,.2f} Kz\n"
            f"Contado: {reported_balance:,.2f} Kz\n"
            f"Diferença: *{difference:,.2f} Kz*\n"
            f"Justificativa: {justification if justification else 'Sem justificativa.'}"
        )
        # Integração SOTARQ MESSENGER (Simulado)
        # task_send_whatsapp_alert.delay(settings.DIRECTOR_FINANCE_PHONE, alert_msg)
        messages.warning(request, f"Fecho realizado com divergência de {difference:,.2f} Kz. A direção foi alertada.")
    else:
        messages.success(request, "Caixa fechado com balanço perfeito.")

    # 4. Gravação Final da Sessão (Encerramento)
    session.expected_balance = expected_balance
    session.reported_balance = reported_balance
    session.difference = difference
    session.justification = justification
    session.status = 'closed'
    session.closed_at = timezone.now()
    session.save()

    # 5. Geração do Documento de Prestação de Contas (PDF)
    pdf_content = CashClosingReport.generate_daily_closing(session, payments, request.user, totals)
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Fecho_{request.user.username}_{today}.pdf"'
    
    return response

@login_required
@transaction.atomic
def process_sangria(request):
    """Retirada de valor (Saída)."""
    if request.method == 'POST':
        session = CashSession.objects.filter(user=request.user, status='open').last()
        amount = Decimal(request.POST.get('amount', '0'))
        
        if session and amount > 0:
            CashOutflow.objects.create(
                session=session,
                amount=amount,
                description=request.POST.get('reason'),
                authorized_by=request.user
            )
            messages.warning(request, f"Sangria de {amount:,.2f} Kz registrada.")
            
    return redirect('finance:secretary_dashboard')


@login_required
@transaction.atomic
def process_suprimento(request):
    """Reforço de caixa (Entrada)."""
    if request.method == 'POST':
        session = CashSession.objects.filter(user=request.user, status='open').last()
        amount = Decimal(request.POST.get('amount', '0'))
        
        if session and amount > 0:
            CashInflow.objects.create(
                session=session,
                amount=amount,
                description=request.POST.get('reason', 'Reforço de Caixa'),
                authorized_by=request.user
            )
            messages.success(request, f"Suprimento de {amount:,.2f} Kz registrado.")
            
    return redirect('finance:secretary_dashboard')




from django.shortcuts import render, redirect
from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from decimal import Decimal, InvalidOperation
import logging

logger = logging.getLogger(__name__)


@login_required
def caixa_central_view(request):
    """
    Dashboard de Rigor SOTARQ: Focado exclusivamente em Taxas Académicas.
    Eliminada venda de itens, cantina e produtos.
    """
    # 1. Filtramos apenas as Taxas Académicas Oficiais (Propinas, Matrículas, etc.)
    # Como não temos mais FeeCategory, listamos todos os FeeTypes ativos.
    taxas_academicas = FeeType.objects.all()

    # 2. Sessão de Caixa Ativa (Segurança de Operação)
    active_session = CashSession.objects.filter(user=request.user, status='open').first()

    # 3. Pagamentos Pendentes de Validação (Onde o operador valida o talão/comprovativo)
    # Focado em Propinas, Matrículas e Reconfirmações vindas do Portal ou Secretaria.
    pending_validations = Payment.objects.filter(
        validation_status='pending'
    ).select_related('invoice__student', 'method')

    context = {
        'taxas': taxas_academicas,
        'active_cash_session': active_session,
        # Saldo esperado em gaveta
        'cash_total': active_session.expected_balance if active_session else 0,
        'pending_validations': pending_validations,
        # Lista de alunos para busca rápida de faturas
        'students': Student.objects.filter(is_active=True).only('full_name', 'registration_number'),
    }
    
    return render(request, 'finance/caixa_central.html', context)


@login_required
@user_passes_test(is_manager_check)
def setup_wizard(request):
    """
    Painel de Ativação Crítica: Crucial para o funcionamento do SOTARQ SCHOOL.
    Centraliza os requisitos mínimos para o Tenant operar.
    """
    checks = {
        'academic_year': {
            'status': AcademicYear.objects.filter(is_active=True).exists(),
            'title': 'Ano Letivo Ativo',
            'description': 'Necessário para matrículas, turmas e pautas.',
            # No seu urls.py: name='year_list' dentro do namespace 'academic'
            'link': reverse('academic:year_list'), 
        },
        'finance_config': {
            'status': FinanceConfig.objects.exists(),
            'title': 'Configurações de Multas/Juros',
            'description': 'Define o rigor financeiro sobre as faturas vencidas.',
            # Como o app finance não tem namespace no include, usamos 'finance:...'
            # Nota: Você ainda não definiu a rota de "Settings" no seu finance/urls.py,
            # então redirecionamos para o Dashboard de Secretária como fallback seguro.
            'link': reverse('finance:secretary_dashboard'), 
        },
        'system_ready': False
    }

    # Verifica se tudo está OK
    checks['system_ready'] = all(item['status'] for key, item in checks.items() if key != 'system_ready')

    return render(request, 'core/setup_wizard.html', {'checks': checks})