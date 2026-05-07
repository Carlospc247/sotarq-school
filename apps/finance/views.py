# apps/finance/views.py
from datetime import timedelta
from decimal import Decimal
from venv import logger

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum, Count, Q
from django.urls import reverse_lazy
from django.utils import timezone
from django.http import FileResponse, HttpResponse, HttpResponseForbidden # CORREÇÃO AQUI
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .forms import FeeTypeForm, PriceUpdateForm

from apps.core.models import Role
from apps.finance.utils.pdf_generator import SOTARQExporter
from apps.fiscal.models import DocumentoFiscal

# Imports dos teus modelos
from .models import BankAccount, CashSession, FeePriceHistory, FeeType, Invoice, Payment, PaymentGatewayConfig, DebtAgreement, PaymentMethod, PaymentType
from apps.students.models import Student
from apps.academic.models import AcademicYear, Course
# Assumindo que este serviço existe em finance/services.py
from .services import DebtRefinancingService, PenaltyEngine 

from django.db.models.functions import TruncDay
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, UpdateView, DeleteView


from .models import Invoice, Receipt, Payment
from apps.fiscal.models import DocType





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
    # CORRETO (Rigor SOTARQ: Usando o campo 'user' definido no Model)
    session = CashSession.objects.filter(user=request.user, status='open').last()

    # CORRETO
    active_session = CashSession.objects.filter(user=request.user, status='open').first()
    
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
def pricing_manager(request):
    """
    CENTRAL DE COMANDO FINANCEIRO (SOTARQ RIGOR)
    Gerencia: Criação, Histórico de Preços e Vínculo com Cursos.
    """
    fees = FeeType.objects.all()
    history_logs = FeePriceHistory.objects.all().select_related('fee_type')[:15]
    courses = Course.objects.all()
    
    # RIGOR SOTARQ: Separar taxas por tipo para facilitar a escolha no template
    # Se você não tiver um campo 'category', use o que tiver para filtrar
    enrollment_fees = FeeType.objects.all() # Ou filtre por matrículas
    monthly_fees = FeeType.objects.all()    # Ou filtre por mensalidades

    update_form = PriceUpdateForm()
    create_form = FeeTypeForm()

    payment_methods = PaymentMethod.objects.all()

    #activated_codes = [m.method_type for m in payment_methods if m.is_active]
    
    activated_codes = [str(m.method_type) for m in payment_methods if m.is_active]


    if request.method == 'POST':
        # --- CASO 1: CRIAR NOVO TIPO DE TAXA ---
        if 'btn_create_fee' in request.POST:
            create_form = FeeTypeForm(request.POST)
            if create_form.is_valid():
                create_form.save()
                messages.success(request, "Novo serviço/taxa registrado no catálogo.")
                return redirect('finance:pricing_manager')

        # --- CASO 2: ATUALIZAR PREÇO EXISTENTE (COM AUDITORIA) ---
        elif 'fee_id' in request.POST and 'amount' in request.POST:
            update_form = PriceUpdateForm(request.POST)
            if update_form.is_valid():
                fee_id = update_form.cleaned_data['fee_id']
                new_val = update_form.cleaned_data['amount']
                fee = get_object_or_404(FeeType, id=fee_id)
                
                if fee.amount != new_val:
                    FeePriceHistory.objects.create(
                        fee_type=fee,
                        old_amount=fee.amount,
                        new_amount=new_val
                    )
                    fee.amount = new_val
                    fee.save()
                    messages.success(request, f"Tarifário de {fee.name} atualizado: {new_val} Kz.")
                return redirect('finance:pricing_manager')
        
        # --- CASO 3: GESTÃO DE MÉTODOS DE PAGAMENTO (ATIVAÇÃO/DESATIVAÇÃO) ---
        elif 'btn_toggle_method' in request.POST:
            method_code = request.POST.get('method_code')
            name = request.POST.get('method_name')
            
            # Busca o método ou cria se nunca tiver existido para este tenant
            method, created = PaymentMethod.objects.get_or_create(
                method_type=method_code,
                defaults={'name': name, 'is_active': True}
            )
            
            if not created:
                # Se já existia, inverte o status atual
                method.is_active = not method.is_active
                method.save()
            
            status_msg = "ativado" if method.is_active else "desativado"
            messages.success(request, f"Método {name} {status_msg} com sucesso.")
            return redirect('finance:pricing_manager')


    context = {
        'fees': fees,
        'enrollment_fees': enrollment_fees, # ESSENCIAL PARA O SELECT
        'monthly_fees': monthly_fees,       # ESSENCIAL PARA O SELECT
        'history_logs': history_logs,
        'payment_methods': payment_methods,
        'activated_codes': activated_codes,
        'payment_types': PaymentType.choices, # Passamos as opções do TextChoices
        'courses': courses,
        'update_form': update_form,
        'create_form': create_form,
    }
    return render(request, 'finance/pricing_manager.html', context)


@login_required
def save_course_pricing_unified(request):
    if request.method == 'POST':
        course_id = request.POST.get('course_id')
        enrollment_fee_id = request.POST.get('enrollment_fee_type')
        monthly_fee_id = request.POST.get('monthly_fee_type')
        
        course = get_object_or_404(Course, id=course_id)
        
        # Rigor SOTARQ: Se o ID vier vazio (string vazia), setamos None
        course.default_enrollment_fee_type_id = enrollment_fee_id if enrollment_fee_id else None
        course.default_monthly_fee_type_id = monthly_fee_id if monthly_fee_id else None
            
        course.save()
        messages.success(request, f"Configuração de preços para {course.name} salva com sucesso!")
        
    return redirect('finance:pricing_manager')


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


# Exemplo de lógica na View de Confirmação
def confirm_enrollment_view(request, student_id):
    student = Student.objects.get(id=student_id)
    course = student.course 
    
    # 1. Recuperar o preço configurado para este curso
    # Supondo que você salvou a relação no modelo Course ou numa tabela de preços
    fee_type = course.default_enrollment_fee  
    
    # 2. Criar a Invoice (Fatura) no banco de dados primeiro
    # O rigor multi-tenant garante que cai no schema certo
    invoice = Invoice.objects.create(
        student=student,
        description=f"Matrícula/Confirmação - {course.name}",
        subtotal=fee_type.amount,
        tax_amount=fee_type.amount * 0.14, # Exemplo 14% IVA
        total=fee_type.amount * 1.14,
        status='paid' # Ou 'pending' se NÃO houver comprovativo
    )

    # 3. Gerar o PDF usando o seu SOTARQExporter
    #from apps.finance.utils.pdf_generators import SOTARQExporter
    pdf_content = SOTARQExporter.generate_fiscal_document(
        instance=invoice, 
        doc_type_code='FR', # Fatura Recibo
        page_format='A4'
    )

    # 4. Retornar o PDF para exibição/impressão imediata
    response = HttpResponse(pdf_content, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Fatura_{invoice.number}.pdf"'
    return response

"""

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


"""

from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from .models import Invoice, PaymentGatewayConfig




@login_required
def checkout_invoice(request, invoice_id):
    """
    View unificada SOTARQ SCHOOL.
    Resolve o erro 404 ao diferenciar busca para Staff e Alunos.
    """
    # 1. Busca da Fatura com Rigor de Permissão
    if request.user.current_role in ['ADMIN', 'DIRECTOR', 'SECRETARY']:
        # Se for staff, busca apenas pelo ID (visão total do tenant)
        invoice = get_object_or_404(Invoice, id=invoice_id)
    else:
        # Se for aluno, OBRIGA que a fatura pertença ao perfil dele
        try:
            student = request.user.student_profile
            invoice = get_object_or_404(Invoice, id=invoice_id, student=student)
        except AttributeError:
            return HttpResponseForbidden("Usuário não possui perfil de estudante.")

    # 2. Configuração do Gateway
    config = PaymentGatewayConfig.objects.first() 
    entidade = config.mc_entity_code if config and config.mc_entity_code else "00000"
    
    # 3. Referência Multicaxa (9 dígitos)
    referencia_pura = f"{invoice.id:09d}"
    referencia_formatada = f"{referencia_pura[:3]} {referencia_pura[3:6]} {referencia_pura[6:]}"
    
    context = {
        'invoice': invoice,
        'config': config,
        'referencia': referencia_formatada,
        'entidade': entidade,
    }
    return render(request, 'finance/checkout.html', context)


@login_required
@transaction.atomic
def convert_to_receipt(request, invoice_id):
    """
    MOTOR SOTARQ: Liquidação de Fatura (FT) gerando Recibo (RC).
    Correção: Uso de ForeignKey 'method' em vez de string 'payment_method'.
    """
    # 1. Validação de Acesso
    allowed_roles = [Role.Type.ADMIN, Role.Type.DIRECTOR, Role.Type.SECRETARY, Role.Type.ACCOUNTANT]
    if request.user.current_role not in allowed_roles:
        return HttpResponseForbidden("Acesso restrito à Tesouraria.")

    invoice = get_object_or_404(Invoice, id=invoice_id)

    # 2. Guard Clause
    if invoice.status == 'paid':
        messages.warning(request, f"O documento #{invoice.number} já se encontra liquidado.")
        return redirect('finance:invoice_list')

    # 3. Captura do Objeto PaymentMethod (Obrigatório conforme seu Model)
    # Buscamos pelo ID vindo do formulário. 
    # Se não vier no POST, buscamos o primeiro ativo como fallback de segurança.
    method_id = request.POST.get('payment_method')
    
    if method_id:
        payment_method_obj = get_object_or_404(PaymentMethod, id=method_id)
    else:
        payment_method_obj = PaymentMethod.objects.filter(is_active=True).first()
        if not payment_method_obj:
            messages.error(request, "ERRO: Nenhum Método de Pagamento configurado no sistema.")
            return redirect('finance:invoice_list')

    try:
        # 4. Registro de Fluxo de Caixa
        session = CashSession.objects.filter(user=request.user, status='open').last()
        if not session:
            messages.error(request, "ERRO: Não existe uma sessão de caixa aberta.")
            return redirect('finance:invoice_list')

        # CORREÇÃO DEFINITIVA: 
        # Nome do campo: 'method' (conforme seu models.py)
        # Valor: Instância do objeto 'payment_method_obj'
        payment = Payment.objects.create(
            invoice=invoice,
            amount=invoice.total,
            method=payment_method_obj, # <--- FK correta
            validation_status='validated',
            confirmed_by=request.user,
            confirmed_at=timezone.now(),
            cash_session=session,
            reference=request.POST.get('reference', f"LIQ-{invoice.number}")
        )

        # 5. MOTOR DE ASSINATURA E GERAÇÃO DE RC
        # Nota: O seu validate_payment já faz invoice.status = 'paid' e save()
        receipt = payment.validate_payment(request.user)

        # 6. Motor de Exportação Fiscal (PDF)
        from apps.finance.utils.pdf_generator import SOTARQExporter
        exporter = SOTARQExporter()
        pdf_buffer = exporter.generate_fiscal_document(
            instance=receipt, 
            doc_type_code='RC', 
            page_format='A4'
        )

        messages.success(request, f"Fatura #{invoice.number} liquidada com sucesso.")
        
        response = HttpResponse(pdf_buffer, content_type='application/pdf')
        filename = f"RC_{receipt.number}_{invoice.student.registration_number}.pdf"
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response

    except Exception as e:
        logger.error(f"CRÍTICO SOTARQ - Falha na liquidação (ID: {invoice_id}): {str(e)}")
        messages.error(request, f"Falha na conversão fiscal: {str(e)}")
        return redirect('finance:invoice_list')


@login_required
def student_print_invoice(request, invoice_id):
    """
    Gera o PDF da Fatura usando o design Enterprise do SOTARQExporter.
    Implementa Rigor de Impressão e Segurança Multi-Tenant.
    """
    # 1. Busca a Fatura com rigor de Tenant (FUNDAMENTAL)
    # Filtramos pelo tenant do usuário logado para evitar que um admin de outra escola veja esta fatura
    invoice = get_object_or_404(Invoice, id=invoice_id)
    
    # 2. Verificar permissão (Secretaria, Direção ou o próprio Aluno)
    # Adicionei o 'MANAGER' caso use esse termo no seu Role.Type
    allowed_roles = ['ADMIN', 'DIRECTOR', 'SECRETARY', 'MANAGER']
    is_staff = request.user.current_role in allowed_roles
    is_owner = invoice.student.user == request.user

    if not (is_staff or is_owner):
        return HttpResponseForbidden("SOTARQ: Acesso Negado. Você não tem permissão para este documento.")

    # 3. Marcar como Impressa ANTES de gerar o PDF (Garante o bloqueio de edição)
    if not invoice.is_printed:
        invoice.is_printed = True
        invoice.printed_at = timezone.now()
        invoice.printed_by = request.user
        # Usamos save com update_fields para não disparar o erro de "bloqueio de alteração" no Signal
        invoice.save(update_fields=['is_printed', 'printed_at', 'printed_by'])

    # 4. Chamar o Exportador Unificado SOTARQ
    from apps.finance.utils.pdf_generator import SOTARQExporter
    
    exporter = SOTARQExporter()
    page_format = request.GET.get('format', 'A4')
    
    # Se já estava impressa antes deste acesso, marcamos como "Cópia" para AGT
    # Se é a PRIMEIRA vez (is_printed era False), podemos considerar o original
    is_copy = True if invoice.printed_at and (timezone.now() - invoice.printed_at).seconds > 5 else False

    pdf_content = exporter.generate_fiscal_document(
        instance=invoice, 
        doc_type_code='FT', 
        is_copy=is_copy,
        page_format=page_format
    )

    # 5. Entrega do Documento
    response = HttpResponse(pdf_content, content_type='application/pdf')
    
    # Nome do arquivo rigoroso
    filename = f"FT_{invoice.number}.pdf".replace("/", "-") 
    response['Content-Disposition'] = f'inline; filename="{filename}"'
    
    return response




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


"""
@login_required
def invoice_list(request):
    user = request.user
    
    # Base Queryset com isolamento Tenant
    if user.current_role in ['ADMIN', 'DIRECTOR', 'SECRETARY', 'ACCOUNTANT']:
        base_invoices = Invoice.objects.filter(student__user__tenant=user.tenant)
    else:
        try:
            student = user.student_profile
            base_invoices = Invoice.objects.filter(student=student)
        except AttributeError:
            base_invoices = Invoice.objects.none()

    # Contadores para o Dashboard
    total_unpaid = base_invoices.filter(status__in=['pending', 'overdue']).count()
    
    # Aplicar filtros da URL (Status, etc)
    status_filter = request.GET.get('status')
    invoices = base_invoices
    if status_filter:
        invoices = invoices.filter(status=status_filter)

    context = {
        'invoices': invoices.order_by('-due_date'),
        'status_choices': Invoice.STATUS_CHOICES,
        'total_unpaid': total_unpaid, # Injetado no contexto
    }
    
    return render(request, 'finance/invoice_list.html', context)


"""
###################################

@login_required
def invoice_list_view(request):
    """
    Gestão Unificada de FT e FR.
    Inclui filtragem dinâmica e métricas globais de liquidez.
    """
    # 1. Base do Queryset (Rigor Tenant)
    base_queryset = Invoice.objects.filter(
        student__user__tenant=request.user.tenant,
        doc_type__in=[DocType.FT, DocType.FR]
    ).select_related('student', 'fiscal_doc').order_by('-issue_date')

    # 2. Métricas Globais (Independente do filtro de pesquisa atual)
    stats = base_queryset.aggregate(
        total_ft_pending=Sum('total', filter=Q(doc_type=DocType.FT, status__in=['pending', 'overdue'])),
        count_ft_pending=Count('id', filter=Q(doc_type=DocType.FT, status__in=['pending', 'overdue'])),
        total_fr_paid=Sum('total', filter=Q(doc_type=DocType.FR, status='paid')),
        count_fr_paid=Count('id', filter=Q(doc_type=DocType.FR, status='paid')),
    )

    # 3. Aplicação de Filtros de Pesquisa
    status_filter = request.GET.get('status')
    queryset = base_queryset
    if status_filter:
        queryset = queryset.filter(status=status_filter)

    return render(request, 'finance/invoice_list.html', {
        'invoices': queryset,
        'stats': stats,
        'status_choices': Invoice.STATUS_CHOICES,
        'title': 'Conta Corrente Académica'
    })


@login_required
def receipt_list_view(request):
    """Histórico de Recibos (RC) e Fluxo de Caixa Realizado."""
    queryset = Receipt.objects.filter(
        payment__invoice__student__user__tenant=request.user.tenant
    ).select_related('payment__invoice__student').order_by('-issue_date')

    stats = queryset.aggregate(
        total_rc=Sum('amount_paid'),
        count_rc=Count('id')
    )

    return render(request, 'finance/receipt_list.html', {
        'receipts': queryset,
        'stats': stats,
        'title': 'Recibos (RC)'
    })

@login_required
def credit_note_list_view(request):
    """Lista as Notas de Crédito (NC) com contagem rigorosa."""
    queryset = Invoice.objects.filter(
        student__user__tenant=request.user.tenant,
        doc_type=DocType.NC
    ).select_related('student', 'fiscal_doc').order_by('-issue_date')

    stats = queryset.aggregate(
        total_nc=Sum('total'),
        count_nc=Count('id')
    )

    return render(request, 'finance/credit_note_list.html', {
        'notes': queryset,
        'stats': stats,
        'title': 'Notas de Crédito'
    })

"""
@login_required
def credit_note_list_view(request):
    
    queryset = Invoice.objects.filter(
        student__user__tenant=request.user.tenant,
        doc_type=DocType.NC
    ).select_related('student', 'fiscal_doc').order_by('-issue_date')

    stats = queryset.aggregate(
        total_nc=Sum('total'),
        count_nc=Count('id')
    )

    return render(request, 'finance/credit_note_list.html', {
        'notes': queryset,
        'stats': stats,
        'title': 'Notas de Crédito'
    })

"""

###############################
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
        'is_staff_tenant': request.user.current_role in ['ADMIN', 'DIRECTOR', 'SECRETARY', 'ACCOUNTANT'],
    }
    
    return render(request, 'finance/invoice_detail.html', context)



class BankAccountListView(LoginRequiredMixin, ListView):
    model = BankAccount
    template_name = 'finance/bank_account_list.html'
    context_object_name = 'accounts'

    def get_queryset(self):
        # Rigor Multi-tenant: Garante que só vê as contas do tenant atual
        return BankAccount.objects.filter(is_active=True).order_by('bank_name')


class BankAccountCreateView(LoginRequiredMixin, CreateView):
    model = BankAccount
    # Removido 'account_holder' e adicionado 'account_number'
    fields = ['bank_name', 'account_number', 'iban', 'is_active']
    template_name = 'finance/bank_account_form.html'
    success_url = reverse_lazy('finance:bank_accounts')

    def form_valid(self, form):
        # O rigor SOTARQ exige que as mensagens sejam claras
        messages.success(self.request, "Conta bancária registada com sucesso no sistema.")
        return super().form_valid(form)

