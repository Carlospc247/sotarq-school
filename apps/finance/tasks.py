# apps/finance/tasks.py
import requests
from email.message import EmailMessage
from celery import shared_task
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from django.db import transaction
from django_tenants.utils import schema_context
from apps.core.models import User
from apps.core.servicos.notifications import AlertService
from apps.customers.models import Client
from apps.finance.models import Invoice, InvoiceItem, FeeType
from apps.finance.services import PenaltyEngine, RiskAnalysisService
from apps.students.models import Student
from apps.core.services import WhatsAppService
from celery import shared_task
from decimal import Decimal
from .models import DebtAgreement, Invoice, FinanceConfig, Payment
from apps.reports.services.finance_bi import MonthlyExplorationEngine
from django.db.models import Sum



@shared_task
def generate_monthly_invoices():
    """
    Motor de Faturação em Lote.
    Gera faturas de propinas e serviços (Transporte) para todos os alunos activos.
    Recomendado correr no dia 25 de cada mês via Celery Beat.
    """
    today = timezone.now().date()
    # Preparação para o mês seguinte
    next_month_date = today + timedelta(days=15)
    month_name = next_month_date.strftime("%m/%Y")
    
    tenants = Client.objects.exclude(schema_name='public')

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            active_students = Student.objects.filter(is_active=True)
            tuition_fee = FeeType.objects.filter(name__icontains="Propina").first()
            
            if not tuition_fee:
                continue 

            for student in active_students:
                invoice_desc = f"Propina Mensal - {month_name}"
                
                # Evita duplicidade
                if Invoice.objects.filter(student=student, items__description=invoice_desc).exists():
                    continue

                with transaction.atomic():
                    invoice = Invoice.objects.create(
                        student=student,
                        doc_type='FT',
                        due_date=next_month_date.replace(day=10), # Vencimento fixo dia 10
                        status='pending'
                    )

                    InvoiceItem.objects.create(
                        invoice=invoice,
                        description=invoice_desc,
                        amount=tuition_fee.amount
                    )

                    # Integração com Módulo de Transportes
                    transport = getattr(student, 'transportenrollment', None)
                    if transport and transport.is_active:
                        InvoiceItem.objects.create(
                            invoice=invoice,
                            description=f"Serviço de Transporte - {transport.zone.name}",
                            amount=transport.zone.monthly_fee
                        )

                    total_invoice = sum(item.amount for item in invoice.items.all())
                    invoice.total = total_invoice
                    invoice.save()
            
            # Opcional: Notificar todos os alunos que novas faturas foram geradas
            # task_notify_new_invoices.delay(tenant.schema_name, month_name)

@shared_task
def task_billing_rule_daily():
    """
    Régua de Cobrança Diária: D-5, D-Day e D+2.
    Execução: Diária (ex: 08:00 AM).
    """
    today = timezone.now().date()
    tenants = Client.objects.exclude(schema_name='public')
    ws = WhatsAppService()

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            # 1. D-5: Lembrete Preventivo (5 dias antes do vencimento)
            target_d5 = today + timedelta(days=5)
            invoices_d5 = Invoice.objects.filter(due_date=target_d5, status='pending')
            send_notifications(invoices_d5, "Lembrete amigável: A sua fatura vence em 5 dias.", ws)

            # 2. D-Day: Aviso de Vencimento Hoje
            invoices_d0 = Invoice.objects.filter(due_date=today, status='pending')
            send_notifications(invoices_d0, "Aviso: A sua fatura vence hoje. Evite multas de atraso.", ws)

            # 3. D+2: Alerta Crítico e Risco de Suspensão
            target_d2 = today - timedelta(days=2)
            invoices_d2 = Invoice.objects.filter(due_date=target_d2, status__in=['pending', 'overdue'])
            send_notifications(invoices_d2, "ALERTA CRÍTICO: Fatura vencida há 2 dias. Risco de suspensão de acesso ao portal.", ws)

def send_notifications(queryset, base_message, ws_service):
    """
    Lógica de extração do contacto e envio via WhatsApp.
    """
    for inv in queryset:
        # Busca o responsável financeiro vinculado ao aluno da fatura
        guardian_link = inv.student.guardians.filter(is_financial_responsible=True).first()
        
        if guardian_link and guardian_link.guardian.phone:
            phone = guardian_link.guardian.phone
            full_name = guardian_link.guardian.full_name
            
            # Mensagem Profissional Personalizada
            message = (
                f"Prezado(a) Sr(a). *{full_name}*,\n\n"
                f"{base_message}\n\n"
                f"📄 *Fatura:* {inv.number}\n"
                f"💰 *Valor:* {inv.total} Kz\n"
                f"📅 *Vencimento:* {inv.due_date.strftime('%d/%m/%Y')}\n\n"
                f"Pode efectuar o pagamento via Multicaixa ou no nosso Portal.\n"
                f"Obrigado por escolher a nossa instituição."
            )
            
            # Disparo via API (UltraMsg ou similar configurada no Service)
            ws_service.send_message(phone, message)



@shared_task(name="apps.finance.tasks.update_overdue_payments_and_interests")
def update_overdue_payments_and_interests():
    """
    PRODUÇÃO: Meia-noite.
    Percorre todos os tenants e aplica multas/juros conforme a FinanceConfig local.
    """
    today = timezone.now().date()
    tenants = Client.objects.exclude(schema_name='public')

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            config = FinanceConfig.objects.first()
            if not config:
                continue

            # 1. Marcar como Vencido faturas que passaram do prazo hoje
            Invoice.objects.filter(status='pending', due_date__lt=today).update(status='overdue')

            # 2. Aplicar Juros e Multas
            overdue_invoices = Invoice.objects.filter(status='overdue')
            
            for invoice in overdue_invoices:
                days_late = (today - invoice.due_date).days
                
                if days_late > config.grace_period_days:
                    with transaction.atomic():
                        # Calculamos com base no valor BASE (original) da fatura 
                        # para evitar juros sobre juros (anatocismo), que pode ser ilegal.
                        valor_base = invoice.total 
                        
                        multa = valor_base * (config.late_fee_percentage / 100)
                        juros_diarios = valor_base * (config.daily_interest_rate / 100) * days_late
                        
                        invoice.total = valor_base + multa + juros_diarios
                        invoice.save(update_fields=['total'])

    return "Processamento de juros concluído para todos os tenants."

@shared_task(name="apps.finance.tasks.task_send_debt_agreement_docs")
def task_send_debt_agreement_docs(agreement_id, tenant_schema):
    """
    Envia o Contrato de Confissão de Dívida assinado para o encarregado.
    """
    from apps.core.services import WhatsAppService
    
    with schema_context(tenant_schema):
        agreement = DebtAgreement.objects.get(id=agreement_id)
        student = agreement.student
        guardian = student.guardians.filter(is_financial_responsible=True).first().guardian
        
        # 1. Envio de E-mail
        if guardian.email:
            email = EmailMessage(
                f"Contrato de Acordo de Dívida #{agreement.id} - {student.user.tenant.name}",
                f"Prezado {guardian.full_name}, segue em anexo o contrato assinado digitalmente.",
                settings.DEFAULT_FROM_EMAIL,
                [guardian.email],
            )
            if agreement.contract_pdf:
                email.attach_file(agreement.contract_pdf.path)
            email.send(fail_silently=True)

        # 2. Envio de WhatsApp (Contrato em PDF)
        if guardian.phone:
            ws = WhatsAppService()
            caption = (
                f"📄 *CONTRATO DE ACORDO FIRMADO*\n\n"
                f"Olá {guardian.full_name}, seu acordo de parcelamento foi registrado.\n"
                f"Anexo enviamos o contrato com validade jurídica.\n\n"
                f"Lembre-se: O acesso será liberado após o pagamento da 1ª prestação."
            )
            
            if agreement.contract_pdf:
                ws.send_document(
                    phone=guardian.phone,
                    document_url=agreement.contract_pdf.url,
                    filename=f"Contrato_Acordo_{agreement.id}.pdf",
                    caption=caption
                )




@shared_task
def task_automated_monthly_closure():
    """
    FECHAMENTO AUTOMÁTICO SOTARQ: Executa em todos os Tenants.
    Gera Mapa, Salva no Cofre e Envia WhatsApp.
    """
    today = timezone.now()
    month, year = today.month, today.year
    tenants = Client.objects.exclude(schema_name='public')

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            # 1. Gera os dados via Motor de BI (Reports App)
            data = MonthlyExplorationEngine.get_monthly_summary(month, year, tenant.schema_name)
            
            # 2. Cria o registro de fechamento para arquivo (Simulado em log/documento)
            # Aqui poderíamos gerar o PDF e salvar em apps.documents.models.Document
            
            # 3. Disparo do Resumo Executivo via WhatsApp (AlertService)
            directors = User.objects.filter(current_role='DIRECTOR')
            for director in directors:
                if director.phone: # Assumindo campo phone no User ou Profile
                    message = (
                        f"📊 *FECHAMENTO MENSAL SOTARQ*\n"
                        f"Instituição: {tenant.name}\n"
                        f"Período: {data['periodo']}\n\n"
                        f"💰 Rec. Realizada: {data['receita_realizada']:,} Kz\n"
                        f"💸 Custos (AF): {data['custos_operacionais']:,} Kz\n"
                        f"📉 Estornos (NC): {data['estornos']:,} Kz\n"
                        f"--------------------------\n"
                        f"✅ *LUCRO LÍQUIDO: {data['lucro_liquido']:,} Kz*"
                    )
                    AlertService.send_generic_whatsapp(director.phone, message)


# apps/finance/tasks.py (Extensão)

@shared_task
def task_daily_cash_report_whatsapp():
    """
    Relatório Executivo às 18:00 para os gestores da escola.
    """
    today = timezone.now().date()
    tenants = Client.objects.exclude(schema_name='public')
    ws = WhatsAppService()

    for tenant in tenants:
        with schema_context(tenant.schema_name):
            # Agregação de dados do dia
            total_cash = Payment.objects.filter(
                confirmed_at__date=today, 
                method__method_type='CH' # Dinheiro
            ).aggregate(Sum('amount'))['amount__sum'] or 0
            
            total_portal = Payment.objects.filter(
                confirmed_at__date=today, 
                method__method_type__in=['MC', 'TR'] # Multicaixa/Transferência
            ).aggregate(Sum('amount'))['amount__sum'] or 0

            message = (
                f"📈 *RELATÓRIO DIÁRIO DE CAIXA - {tenant.name}*\n"
                f"📅 Data: {today.strftime('%d/%m/%Y')}\n\n"
                f"💵 *Dinheiro em Mão:* {total_cash:,.2f} Kz\n"
                f"🏛️ *Portal/Bancos:* {total_portal:,.2f} Kz\n"
                f"--------------------------\n"
                f"💰 *TOTAL ENTRADAS:* {total_cash + total_portal:,.2f} Kz\n\n"
                f"Acesse o SOTARQ para o detalhamento completo."
            )

            # Notifica apenas quem tem autoridade máxima
            target_roles = ['ADMIN','DIRECTOR', 'DIRECT_FINANC']
            managers = User.objects.filter(current_role__in=target_roles)
            
            for m in managers:
                if m.phone:
                    ws.send_message(m.phone, message)





@shared_task(name="task_apply_daily_penalties")
def task_apply_daily_penalties():
    """
    Rigor SOTARQ: Varre faturas overdue e atualiza a mora conforme config do Diretor.
    """
    overdue_invoices = Invoice.objects.filter(status__in=['pending', 'overdue'], due_date__lt=timezone.now().date())
    ws = WhatsAppService()

    for inv in overdue_invoices:
        multa, juros, total = PenaltyEngine.calculate_invoice_mora(inv)
        
        if multa > 0 or juros > 0:
            # Marcamos como overdue se ainda estiver pendente
            inv.status = 'overdue'
            inv.save() # Dispara sinais de auditoria

            # Notificação automática (Opcional, configurável por escola)
            if inv.student.user.phone:
                message = (
                    f"🔔 *ALERTA DE PAGAMENTO SOTARQ*\n\n"
                    f"A fatura {inv.number} encontra-se vencida.\n"
                    f"Valor Base: {inv.total:,.2f} Kz\n"
                    f"Multas/Juros: {multa + juros:,.2f} Kz\n"
                    f"--------------------------\n"
                    f"🏦 *Total p/ hoje: {total:,.2f} Kz*\n\n"
                    f"Regularize no portal para evitar suspensão de serviços."
                )
                ws.send_message(inv.student.user.phone, message)




@shared_task(name="task_automated_debt_reminder")
def task_automated_debt_reminder(tenant_id):
    """
    Rigor SOTARQ: Disparo inteligente de cobrança preventiva.
    Filtra faturas que vencem em 3 dias.
    """
    hoje = timezone.now().date()
    target_date = hoje + timezone.timedelta(days=3)
    
    # 1. Busca faturas a vencer
    invoices = Invoice.objects.filter(
        due_date=target_date,
        status='pending'
    ).select_related('student', 'student__user')

    messenger = SotarqWhatsAppAPI()
    
    for inv in invoices:
        student = inv.student
        guardian_link = student.guardians.filter(is_financial_responsible=True).first()
        
        if not guardian_link or not guardian_link.guardian.phone:
            continue

        # 2. Inteligência de Risco: Define o tom da mensagem
        # Analisamos se este encarregado tem histórico de atraso
        risk_data = RiskAnalysisService.get_student_risk_score(student)
        
        if risk_data['is_high_risk']:
            # Mensagem Firme (Para quem costuma atrasar)
            msg = (
                f"⚠️ *AVISO DE VENCIMENTO - {request.tenant.name}*\n"
                f"Olá, {guardian_link.guardian.full_name}. Lembramos que a fatura do aluno *{student.full_name}* "
                f"vence em 72h ({inv.due_date.strftime('%d/%m')}).\n\n"
                f"Valor: *{inv.total:,.2f} Kz*\n"
                f"Evite multas e juros de mora. regularize via Multicaixa no portal."
            )
        else:
            # Mensagem Gentil (Para quem paga em dia)
            msg = (
                f"Olá, {guardian_link.guardian.full_name}! 👋\n"
                f"Passamos para lembrar que a propina de *{student.full_name}* vence daqui a 3 dias.\n"
                f"Agradecemos pela sua pontualidade habitual! 😊"
            )

        messenger.send_message(guardian_link.guardian.phone, msg)


