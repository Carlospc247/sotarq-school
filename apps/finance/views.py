# apps/finance/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden # CORREÇÃO AQUI
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required

#from apps.finance.utils import SOTARQExporter
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

def finance_dashboard(request):
    """Gera os dados para o gráfico de barras e indicadores de saúde financeira."""
    today = timezone.now().date()
    thirty_days_ago = today - timedelta(days=30)

    # 1. Dados de Entradas (Pagamentos validados)
    income_data = Payment.objects.filter(
        validation_status='validated',
        confirmed_at__date__gte=thirty_days_ago
    ).annotate(day=TruncDay('confirmed_at')).values('day').annotate(total=Sum('amount')).order_by('day')

    # 2. Preparação para o Chart.js (Labels e Valores)
    labels = []
    income_values = []
    
    # Criamos um dicionário para mapear datas e evitar buracos no gráfico
    income_dict = {item['day'].date(): float(item['total']) for item in income_data}
    
    for i in range(30):
        current_day = thirty_days_ago + timedelta(days=i)
        labels.append(current_day.strftime('%d/%m'))
        income_values.append(income_dict.get(current_day, 0))

    context = {
        'labels': labels,
        'income_values': income_values,
        'total_income_month': sum(income_values),
        'pending_invoices_count': Invoice.objects.filter(status='pending').count(),
    }
    return render(request, 'finance/dashboard.html', context)



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


# apps/finance/views.py

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
    invoice = get_object_or_404(Invoice, id=invoice_id, student__user__tenant=request.user.tenant)
    
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

