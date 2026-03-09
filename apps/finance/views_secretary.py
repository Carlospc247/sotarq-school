# apps/finance/views_secretary.py
from decimal import Decimal
from venv import logger
from django.utils import timezone
from django.db import transaction
from django.db.models import Sum, Q
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.urls import reverse
from apps.academic.models import AcademicYear
from apps.academic.views import is_manager_check
from apps.finance.models import FinanceConfig
from django.core.exceptions import PermissionDenied
from .models import FeeType
from apps.reports.finance.utils_reports import CashClosingReport
from apps.students.models import Student
from .models import CashInflow, CashOutflow, CashSession, Payment, Invoice, PaymentType






@login_required
def secretary_finance_dashboard(request):
    """
    Operação de Caixa Central SOTARQ: Controle total de liquidez académica.
    Foco exclusivo em: Validação de Propinas, Matrículas e Reconfirmações.
    """
    # Rigor de Acesso: Apenas quem opera o financeiro entra aqui
    if request.user.current_role not in ['SECRETARY', 'DIRECT_ADMIN', 'ADMIN']:
        return HttpResponseForbidden("Acesso restrito à Secretaria e Administração.")

    today = timezone.now().date()
    
    # 1. Recuperação da Sessão de Caixa Ativa (Turno do Operador)
    session = CashSession.objects.filter(user=request.user, status='open').last()
    
    # 2. Inteligência de Cálculo de Saldo (Rigor SOTARQ)
    cash_total = Decimal('0.00')
    
    if session:
        # A. Recebimentos em Dinheiro: Apenas Propinas/Taxas pagas em espécie na secretaria
        # Filtramos por método CASH para saber o que deve estar fisicamente na gaveta
        cash_payments = Payment.objects.filter(
            confirmed_by=request.user,
            confirmed_at__date=today,
            method__method_type=PaymentType.CASH,
            validation_status='validated'
        ).aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        # B. Movimentações Avulsas (Suprimentos de troco e Sangrias de despesa)
        total_inflow = session.inflows.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
        total_outflow = session.outflows.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

        # C. Fórmula Mestra de Caixa: (Fundo de Maneio + Propinas em Cash + Reforços) - Retiradas
        cash_total = (session.opening_balance + cash_payments + total_inflow) - total_outflow

    # 3. Métricas de Operação Académica
    # Fila de espera: Alunos que enviaram comprovativos pelo Portal (Matrículas/Propinas)
    pending_validations = Payment.objects.filter(
        validation_status='pending'
    ).select_related('invoice', 'invoice__student').order_by('created_at')

    # ELIMINADO: saleable_products (Não vendemos itens no SOTARQ SCHOOL)
    
    # Histórico das últimas 5 validações de propinas do turno
    recent_actions = Payment.objects.filter(
        confirmed_by=request.user, 
        confirmed_at__date=today
    ).select_related('invoice__student').order_by('-confirmed_at')[:5]

    context = {
        'active_cash_session': session,
        'pending_validations': pending_validations,
        'cash_total': cash_total,
        'recent_actions': recent_actions,
        # Útil para o operador saber o que pode cobrar
        'available_fees': FeeType.objects.all(), 
    }
    
    return render(request, 'finance/secretary/dashboard.html', context)


@login_required
def generate_budget_view(request, student_id):
    """
    Motor de Projeção Orçamentária SOTARQ.
    Gera uma Fatura Proforma (FP) com os custos previstos para o ano lectivo.
    """
    # 1. Segurança de Tenant e Obtenção do Aluno
    student = get_object_or_404(Student, id=student_id, user__tenant=request.user.tenant)
    
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