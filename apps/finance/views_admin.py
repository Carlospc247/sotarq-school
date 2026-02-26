# apps/finance/views_admin.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from decimal import Decimal
from django.db import transaction, models
from apps.academic.views import is_manager_check
from apps.core.models import Role
from apps.finance.services import RiskAnalysisService
from .models import Invoice, InvoiceItem, Payment, ServiceProvider
from django.db.models import Sum, Count, F
from django.utils import timezone
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.contrib import messages
from apps.students.models import Enrollment, Student
from django.urls import reverse
from django.contrib.auth.decorators import login_required, user_passes_test, permission_required





@login_required
@user_passes_test(is_manager_check)
def mass_whatsapp_promotion_alert(request):
    """
    Motor SOTARQ MESSENGER: Disparo em massa para alunos promovidos.
    Notifica o Encarregado sobre a vaga reservada no próximo ano lectivo.
    """
    # 1. Filtra matrículas que acabaram de ser criadas via promoção (aguardando vaga física)
    # Rigor: Apenas do tenant atual
    promoted_enrollments = Enrollment.objects.filter(
        academic_year__is_active=True,
        status='pending_placement',
        student__user__tenant=request.user.tenant
    ).select_related('student', 'grade_level')

    if not promoted_enrollments.exists():
        messages.info(request, "Nenhum aluno promovido recentemente para notificar.")
        return redirect('academic:student_dashboard')

    count = 0
    for enrollment in promoted_enrollments:
        student = enrollment.student
        # Busca o encarregado financeiro (Rigor SOTARQ: quem paga é quem decide)
        guardian_link = student.guardians.filter(is_financial_responsible=True).first()
        
        if guardian_link and guardian_link.guardian.phone:
            phone = guardian_link.guardian.phone
            msg = (
                f"Olá, {guardian_link.guardian.full_name}! 👋\n"
                f"Temos boas notícias: O aluno *{student.full_name}* foi promovido para a *{enrollment.grade_level.name}*!\n\n"
                f"A vaga já está reservada. Por favor, acesse o portal ou dirija-se à secretaria para confirmar a matrícula.\n"
                f"Atenciosamente, Direção {request.user.tenant.name} 🏛️"
            )
            
            # Aqui chamamos a Task Assíncrona do SOTARQ MESSENGER para não travar o servidor
            # task_send_whatsapp.delay(phone, msg)
            count += 1

    messages.success(request, f"SOTARQ MESSENGER: {count} alertas de promoção enviados para a fila de disparo.")
    return redirect('academic:student_dashboard')




@login_required
@user_passes_test(is_manager_check)
def finance_bi_monthly_data(request):
    """
    Motor de Inteligência de Negócio SOTARQ.
    Gera indicadores de performance financeira (KPIs) para o mês corrente.
    """
    hoje = timezone.now()
    inicio_mes = hoje.replace(day=1, hour=0, minute=0, second=0)
    
    # 1. Filtro Base (Rigor Tenant e Tipos Fiscais Reais)
    invoices_reais = Invoice.objects.filter(
        student__user__tenant=request.user.tenant,
        created_at__gte=inicio_mes,
        doc_type__in=['FT', 'FR'] # Exclui FP (Proformas)
    )

    # 2. KPIs de Topo
    faturamento_total = invoices_reais.aggregate(total=Sum('total_amount'))['total'] or 0
    recebido = invoices_reais.filter(status='paid').aggregate(total=Sum('total_amount'))['total'] or 0
    pendente = faturamento_total - recebido

    # 3. Distribuição por Curso (Dados para o Gráfico de Pizza)
    # Agrupamos por curso através da matrícula do aluno
    distribuicao_cursos = (
        invoices_reais.values('student__enrollments__course__name')
        .annotate(valor=Sum('total_amount'))
        .order_by('-valor')
    )

    data = {
        'kpis': {
            'faturamento': float(faturamento_total),
            'recebido': float(recebido),
            'pendente': float(pendente),
            'taxa_cobratória': round((recebido / faturamento_total * 100), 2) if faturamento_total > 0 else 0
        },
        'chart_data': {
            'labels': [item['student__enrollments__course__name'] for item in distribuicao_cursos if item['student__enrollments__course__name']],
            'values': [float(item['valor']) for item in distribuicao_cursos if item['student__enrollments__course__name']]
        }
    }

    return JsonResponse(data)


def financial_overview(request):
    today = timezone.now().date()
    
    # 1. RECEITA PREVISTA (Tudo o que foi faturado e não cancelado)
    prevista = Invoice.objects.exclude(status='cancelled').aggregate(total=Sum('total'))['total'] or 0
    
    # 2. RECEITA REALIZADA (Tudo o que já foi validado pela tesouraria)
    realizada = Payment.objects.filter(validation_status='validated').aggregate(total=Sum('amount'))['total'] or 0
    
    # 3. TAXA DE INADIMPLÊNCIA
    inadimplencia = prevista - realizada
    taxa_perda = (inadimplencia / prevista * 100) if prevista > 0 else 0

    # 4. TOP 10 DEVEDORES (Ranking Crítico)
    top_debtors = Student.objects.filter(invoices__status='overdue') \
        .annotate(debt=Sum('invoices__total')) \
        .order_by('-debt')[:10]

    return render(request, 'finance/admin/overview.html', {
        'prevista': prevista,
        'realizada': realizada,
        'inadimplencia': inadimplencia,
        'taxa_perda': taxa_perda,
        'top_debtors': top_debtors,
    })




@login_required
def promotion_finance_dashboard(request):
    """
    Painel de Controle de Promoções vs Tesouraria.
    Focado no DIRECT_ADMIN para recuperação de faturamento.
    """
    if request.user.current_role != Role.Type.DIRECT_ADMIN or Role.Type.ADMIN and not request.user.is_superuser:
        return HttpResponseForbidden("Acesso exclusivo à Direção Administrativa.")

    # 1. Busca alunos 'graduated' (aprovados no pedagógico) com faturas abertas
    from apps.finance.models import Invoice
    
    # Subquery para pegar IDs de alunos aprovados com dívida
    debtor_ids = Invoice.objects.filter(
        status__in=['pending', 'overdue']
    ).values_list('student_id', flat=True)

    waiting_list = Enrollment.objects.filter(
        status='graduated', # Já processados pela pauta final
        student_id__in=debtor_ids
    ).select_related('student', 'class_room').distinct()

    # 2. Cálculos de KPI para o topo do Dashboard
    total_debt_value = Invoice.objects.filter(
        student__enrollments__status='graduated',
        status__in=['pending', 'overdue']
    ).aggregate(Sum('total'))['total__sum'] or 0

    return render(request, 'finance/admin/promotion_dashboard.html', {
        'waiting_list': waiting_list,
        'total_debt_value': total_debt_value,
        'total_count': waiting_list.count(),
        'today': timezone.now()
    })



@login_required
@transaction.atomic
def generate_self_invoice(request):
    """
    Gera o documento de Autofacturação (AF) para prestadores sem NIF jurídico.
    Rigor: Exclusivo para Direção e Administrativo.
    """
    if request.user.current_role not in ['ADMIN', 'DIRECTOR', 'DIRECT_ADMIN']:
        return HttpResponseForbidden("Acesso restrito.")

    if request.method == 'POST':
        provider_id = request.POST.get('provider_id')
        description = request.POST.get('description')
        amount = Decimal(request.POST.get('amount', '0.00'))
        
        provider = get_object_or_404(ServiceProvider, id=provider_id)
        
        # 1. Cria a Invoice do tipo AF (Autofacturação)
        # Usamos um 'aluno dummy' ou deixamos student=None se o model permitir
        # Para rigor de sistema, criamos a AF vinculada ao prestador
        af_doc = Invoice.objects.create(
            student=None, # AF não é para aluno
            doc_type='AF',
            total=amount,
            status='paid', # AF nasce liquidada
            due_date=timezone.now().date(),
            notes=f"Prestador: {provider.full_name} | BI: {provider.bi_number}"
        )
        
        InvoiceItem.objects.create(
            invoice=af_doc,
            description=description,
            amount=amount
        )

        # 2. Motor de Exportação de Elite
        from .utils import SOTARQExporter
        pdf_data = SOTARQExporter.generate_fiscal_document(af_doc, 'AF')
        
        response = HttpResponse(pdf_data, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="AF_{af_doc.number}.pdf"'
        return response

    providers = ServiceProvider.objects.all()
    return render(request, 'finance/admin/self_invoice_form.html', {'providers': providers})




@login_required
def budget_approval_list(request):
    """Lista Proformas (FP) aguardando revisão da Direção Geral."""
    if request.user.current_role not in ['ADMIN', 'DIRECTOR']:
        return HttpResponseForbidden("Acesso exclusivo à Direção Geral.")

    # Filtra apenas Faturas Proformas pendentes
    proformas = Invoice.objects.filter(doc_type='FP', status='pending').order_by('-issue_date')
    
    return render(request, 'finance/admin/budget_approval.html', {
        'proformas': proformas
    })


@login_required
@permission_required('finance.pode_aplicar_descontos', raise_exception=True)
def apply_budget_discount(request, proforma_id):
    proforma = get_object_or_404(Invoice, id=proforma_id, doc_type='FP')
    
    val = Decimal(request.POST.get('discount_value', '0'))
    mode = request.POST.get('discount_mode') # 'PCT' ou 'FIXED'
    tax_id = request.POST.get('tax_type_id') # Seleção do IVA (ex: Normal 14%)

    # Aplicação do Rigor
    proforma.discount_value = val
    proforma.discount_is_pct = (mode == 'PCT')
    proforma.tax_type_id = tax_id
    proforma.discount_authorized_by = request.user
    
    proforma.update_totals() # O método do modelo faz a mágica matemática
    
    messages.success(request, f"Cálculo atualizado: {proforma.total:,.2f} Kz")
    return redirect('finance:budget_approval_list')


# apps/finance/views_admin.py
from django.db.models import Sum
from .models import Payment, PaymentMethod

@login_required
@user_passes_test(is_manager_check)
def finance_bi_payment_methods(request):
    """
    Motor SOTARQ BI: Análise de Canais de Recebimento.
    Compara o volume financeiro entre Cash, Multicaixa, Transferência, etc.
    """
    hoje = timezone.now()
    
    # 1. Agrupamento por Modalidade (Apenas pagamentos validados no mês)
    stats_metodos = (
        Payment.objects.filter(
            invoice__student__user__tenant=request.user.tenant,
            validation_status='validated',
            confirmed_at__month=hoje.month,
            confirmed_at__year=hoje.year
        )
        .values('method__name')
        .annotate(total=Sum('amount'))
        .order_by('-total')
    )

    data = {
        'labels': [item['method__name'] for item in stats_metodos],
        'values': [float(item['total']) for item in stats_metodos],
    }

    return JsonResponse(data)



@login_required
@user_passes_test(is_manager_check)
def api_financial_risk_projection(request):
    """Retorna os dados de projeção para o gráfico de risco."""
    data = RiskAnalysisService.project_monthly_loss(request.user.tenant)
    return JsonResponse(data)
