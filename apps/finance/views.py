# apps/finance/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden # CORREÇÃO AQUI
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse

from apps.finance.utils.pdf_generator import SOTARQExporter
from apps.fiscal.models import DocumentoFiscal

# Imports dos teus modelos
from .models import Invoice, Payment, PaymentGatewayConfig, DebtAgreement
from apps.students.models import Student
from apps.academic.models import AcademicYear
# Assumindo que este serviço existe em finance/services.py
from .services import DebtRefinancingService, PenaltyEngine 


from django.shortcuts import render
from django.db.models import Sum
from django.db.models.functions import TruncDay
from django.utils import timezone
from datetime import timedelta
from .models import Payment, Invoice # Assumindo que você registrará despesas também

from django.shortcuts import render
from django.utils import timezone
from django.db.models import Sum
from django.db.models.functions import TruncDay
from datetime import timedelta
from django.contrib.auth.decorators import login_required
from .models import Payment, Invoice, FeeType, CashSession, Student


@login_required
def finance_dashboard(request):
    """Dash principal: Gráficos de 30 dias + Operações de Caixa + Produtos Rápidos."""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    # --- 1. Lógica Analítica (Chart.js) ---
    income_data = Payment.objects.filter(
        validation_status='validated',
        confirmed_at__date__gte=thirty_days_ago
    ).annotate(day=TruncDay('confirmed_at')).values('day').annotate(total=Sum('amount')).order_by('day')

    labels = []
    income_values = []
    income_dict = {item['day'].date(): float(item['total']) for item in income_data}
    
    for i in range(30):
        current_day = thirty_days_ago + timedelta(days=i)
        labels.append(current_day.strftime('%d/%m'))
        income_values.append(income_dict.get(current_day, 0))

    # --- 2. Lógica Operacional (Caixa e PDV) ---
    # Busca sessão ativa do usuário atual (Multi-tenant)
    active_session = CashSession.objects.filter(operator=request.user, status='open').first()
    
    # Produtos rápidos para o balcão
    #quick_products = FeeType.objects.filter(
    #    category__in=[FeeCategory.PRODUCT, FeeCategory.SERVICE]
    #).order_by('name')[:5]

    # Todos os produtos para o select do modal
    all_products = FeeType.objects.all()
    all_students = Student.objects.filter(is_active=True)

    context = {
        # Analítico
        'labels': labels,
        'income_values': income_values,
        'total_income_month': sum(income_values),
        'pending_invoices_count': Invoice.objects.filter(status='pending').count(),
        
        # Operacional
        'active_cash_session': active_session,
        #'quick_products': quick_products,
        'products': all_products,
        'students': all_students,
        'pending_validations': Payment.objects.filter(validation_status='pending'),
        'cash_total': active_session.current_balance if active_session else 0,
    }
    return render(request, 'finance/dashboard.html', context)



@login_required
@transaction.atomic
def process_manual_payment(request):
    """
    Processo Atómico SOTARQ: Cria Fatura + Regista Pagamento + Valida na Sessão.
    Elimina 3 passos manuais do operador.
    """
    if request.method != "POST":
        return redirect('finance:secretary_dashboard')

    student_id = request.POST.get('student_id')
    fee_type_id = request.POST.get('fee_type_id')
    method_type = request.POST.get('payment_method') # CASH ou TPA

    # Verificação de Segurança: Existe caixa aberto?
    session = CashSession.objects.filter(user=request.user, status='open').last()
    if not session:
        messages.error(request, "ERRO CRÍTICO: Não pode receber valores sem uma Sessão de Caixa aberta.")
        return redirect('finance:secretary_dashboard')

    try:
        # 1. Recuperar o tipo de taxa (Preço definido pelo Diretor/Admin)
        fee = FeeType.objects.get(id=fee_type_id)
        
        # 2. Gerar a Invoice (Fatura) - Estado 'paid' diretamente
        invoice = Invoice.objects.create(
            student_id=student_id,
            fee_type=fee,
            amount=fee.amount,
            status='paid', # Já nasce paga por ser presencial
            created_by=request.user
        )

        # 3. Gerar o Payment (O registro financeiro)
        # O rigor aqui é o validation_status='validated' imediato
        payment = Payment.objects.create(
            invoice=invoice,
            amount=fee.amount,
            method_type=method_type,
            validation_status='validated',
            confirmed_by=request.user,
            confirmed_at=timezone.now(),
            cash_session=session # Vinculamos ao turno atual para o saldo bater
        )

        messages.success(request, f"Recebimento de {fee.name} (KZ {fee.amount}) processado com sucesso!")
        
    except Exception as e:
        messages.error(request, f"Falha na operação: {str(e)}")
        # O transaction.atomic fará o rollback de tudo se algo falhar aqui

    return redirect('finance:secretary_dashboard')


def checkout_invoice(request, invoice_id):
    invoice = get_object_or_404(Invoice, id=invoice_id, student__user=request.user)
    config = PaymentGatewayConfig.objects.first() 
    
    entidade = config.mc_entity_code if config else "00000"
    referencia_pura = f"{invoice.id:09d}"
    
    context = {
        'invoice': invoice,
        'config': config,
        'referencia': f"{referencia_pura[:3]} {referencia_pura[3:6]} {referencia_pura[6:]}",
        'entidade': entidade,
    }
    return render(request, 'finance/checkout.html', context)



@staff_member_required
def validate_payment_fast(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    
    # Valida o pagamento (Garante auditoria e desbloqueio)
    payment.validate_payment(request.user)

    # Notificação via Celery
    schema_name = request.tenant.schema_name
    from apps.core.tasks import task_process_payment_notifications
    task_process_payment_notifications.delay(payment.id, schema_name)

    messages.success(request, f"Pagamento de {payment.amount} Kz validado com sucesso.")
    return redirect('finance:treasury_dashboard')


@login_required
def print_receipt(request, payment_id):
    payment = get_object_or_404(Payment, id=payment_id)
    page_format = request.GET.get('format', 'A4') # Default A4
    
    # Rigor: No multi-tenant, o get_object_or_404 já filtra pelo schema
    
    exporter = SOTARQExporter()
    # doc_type_code 'RC' para Recibo, 'FT' para Fatura
    pdf_buffer = exporter.generate_fiscal_document(
        instance=payment, 
        doc_type_code='RC', 
        page_format=page_format
    )
    
    pdf_buffer.seek(0)
    filename = f"Recibo_{payment.id}_{page_format}.pdf"
    
    return FileResponse(pdf_buffer, as_attachment=False, filename=filename)


def download_report_card(request, student_id):
    student = get_object_or_404(Student, id=student_id)
    
    # Verifica dívidas antes de liberar boletim
    has_debt = Invoice.objects.filter(
        student=student, 
        status__in=['pending', 'overdue'],
        due_date__lt=timezone.now().date()
    ).exists()

    if has_debt:
        messages.error(request, "Acesso bloqueado. Regularize as suas propinas para visualizar o boletim.")
        return redirect('finance:debt_list')

    # Placeholder para a função de geração de PDF
    return HttpResponse("Função de PDF ainda não implementada.", content_type='text/plain')

@login_required
def student_debt_negotiation(request):
    try:
        student = request.user.student_profile
    except AttributeError:
        return redirect('portal:dashboard')

    overdue_invoices = Invoice.objects.filter(
        student=student, 
        status__in=['pending', 'overdue'],
        due_date__lt=timezone.now().date()
    )
    
    if not overdue_invoices.exists():
        messages.info(request, "Não existem faturas pendentes para negociação.")
        return redirect('portal:dashboard')

    total_debt = sum(inv.total for inv in overdue_invoices)
    
    if request.method == 'POST':
        installments = int(request.POST.get('installments', 1))
        # Uso do serviço de refinanciamento
        agreement = DebtRefinancingService.create_agreement(student, installments)
        
        messages.success(request, f"Acordo #{agreement.id} firmado com sucesso!")
        return redirect('portal:dashboard')

    context = {
        'total_debt': total_debt,
        'invoices': overdue_invoices,
        'max_installments': 6,
    }
    return render(request, 'finance/portal/negotiate_debt.html', context)




@login_required
def imprimir_documento_fiscal(request, doc_id):
    """
    Motor v2.5: Força A4 no portal, permite escolha no ERP.
    """
    doc = get_object_or_404(DocumentoFiscal, id=doc_id)
    
    # Rigor de Origem:
    user_role = request.user.current_role
    if user_role in ['STUDENT', 'GUARDIAN']:
        page_format = 'A4' # Alunos não imprimem talão térmico
    else:
        page_format = request.GET.get('format', 'A4') # Staff escolhe
    
    pdf_content = SOTARQExporter.generate_fiscal_document(
        instance=doc, 
        doc_type_code=doc.tipo_documento, 
        page_format=page_format
    )
    
    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename = f"DOC_{doc.numero_documento}_{page_format}.pdf"
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    return response



@login_required
def invoice_list(request):
    """
    Listagem Inteligente de Faturas SOTARQ.
    Rigor: Alunos vêm as SUAS faturas. Staff vê TUDO do Tenant.
    """
    user = request.user
    
    # 1. Filtro por Hierarquia de Acesso
    if user.current_role in ['ADMIN', 'DIRECTOR', 'SECRETARY', 'ACCOUNTANT']:
        # Staff vê todas as faturas da instituição atual
        invoices = Invoice.objects.filter(student__user__tenant=user.tenant).select_related('student')
    else:
        # Aluno/Encarregado vê apenas as suas
        try:
            student = user.student_profile
            invoices = Invoice.objects.filter(student=student)
        except AttributeError:
            invoices = Invoice.objects.none()

    # 2. Filtros de Interface (Opcional, mas recomendado para o rigor)
    status_filter = request.GET.get('status')
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    context = {
        'invoices': invoices.order_by('-due_date'),
        'status_choices': Invoice.STATUS_CHOICES,
    }
    
    return render(request, 'finance/invoice_list.html', context)

@login_required
def invoice_detail(request, invoice_id):
    """
    Exibição Detalhada da Fatura com Auditoria Fiscal.
    Rigor: Mostra itens, multas, juros e o link com o DocumentoFiscal.
    """
    # Busca a fatura garantindo o isolamento do Tenant (Segurança Máxima)
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # Cálculos de Mora em tempo real (Motor de Rigor PenaltyEngine)
    multa, juros, total_atualizado = PenaltyEngine.calculate_invoice_mora(invoice)
    
    # Busca os pagamentos associados (validados ou não)
    payments = invoice.payments.all().order_by('-created_at')
    
    context = {
        'invoice': invoice,
        'items': invoice.items.all(),
        'payments': payments,
        'multa': multa,
        'juros': juros,
        'total_atualizado': total_atualizado,
        'is_staff': request.user.current_role in ['ADMIN', 'DIRECTOR', 'SECRETARY', 'ACCOUNTANT'],
    }
    
    return render(request, 'finance/invoice_detail.html', context)

