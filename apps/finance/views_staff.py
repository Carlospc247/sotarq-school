# apps/finance/views_staff.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

from apps.students.models import Student
from .models import Invoice, Payment
from django.utils import timezone
from django.contrib import messages
from django.db import transaction

# Rigor SOTARQ: Apenas Secretaria ou Admin podem validar
def is_treasury_staff(user):
    return user.current_role in ['SECRETARY', 'DIRECT_FINANC', 'ADMIN']

@login_required
@user_passes_test(is_treasury_staff)
def treasury_dashboard(request):
    """Painel de controle para a Tesouraria validar comprovativos."""
    pending_payments = Payment.objects.filter(
        validation_status='pending', 
        proof_file__isnull=False
    ).select_related('invoice', 'invoice__student').order_by('created_at')

    return render(request, 'finance/staff/treasury_dashboard.html', {
        'payments': pending_payments,
        'today': timezone.now()
    })

@login_required
@user_passes_test(is_treasury_staff)
@transaction.atomic
def validate_payment_fast(request, payment_id):
    """Valida o pagamento e dispara as notificações via Celery."""
    payment = get_object_or_404(Payment, id=payment_id)
    
    # 1. Validação Financeira
    payment.validate_payment(user=request.user) # Usa o método que já criamos no modelo
    
    # 2. Chamada Assíncrona para Notificações (Celery)
    schema_name = request.tenant.schema_name
    from apps.core.tasks import task_process_payment_notifications
    task_process_payment_notifications.delay(payment.id, schema_name)

    messages.success(request, f"Pagamento de {payment.invoice.student.full_name} liquidado e assinado RSA!")
    return redirect('finance:treasury_dashboard')

@login_required
@user_passes_test(is_treasury_staff)
def reject_payment(request, payment_id):
    """Rejeita o comprovativo e solicita novo envio ao pai."""
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)
        reason = request.POST.get('rejection_reason')
        
        payment.validation_status = 'rejected'
        payment.rejection_reason = reason
        payment.save()
        
        messages.warning(request, f"Pagamento de {payment.invoice.student.full_name} rejeitado.")
    return redirect('finance:treasury_dashboard')



@login_required
@user_passes_test(is_treasury_staff)
def void_payment_action(request, payment_id):
    """Executa a anulação de um pagamento por erro de validação."""
    if request.method == 'POST':
        payment = get_object_or_404(Payment, id=payment_id)
        reason = request.POST.get('reason')

        if not reason:
            messages.error(request, "É obrigatório indicar o motivo do estorno.")
            return redirect('finance:payment_history')

        try:
            payment.void_payment(request.user, reason)
            messages.success(request, f"O recebimento de {payment.invoice.student.full_name} foi anulado com sucesso.")
        except Exception as e:
            messages.error(request, f"Erro ao estornar: {str(e)}")

    return redirect('finance:treasury_dashboard')



@login_required
@user_passes_test(lambda u: u.current_role in ['DIRECT_FINANC', 'ADMIN'])
def waive_penalty_action(request, invoice_id):
    """Anula as multas e juros de uma fatura por decisão administrativa."""
    if request.method == 'POST':
        invoice = get_object_or_404(Invoice, id=invoice_id)
        reason = request.POST.get('reason')

        if not reason:
            messages.error(request, "Rigor: É obrigatório justificar o perdão da mora.")
            return redirect('finance:invoice_list')

        invoice.waive_penalty = True
        invoice.waive_reason = reason
        invoice.penalty_waived_by = request.user
        invoice.save()

        messages.success(request, f"Mora da fatura {invoice.number} perdoada com sucesso.")
    
    return redirect('finance:invoice_list')



@login_required
@user_passes_test(lambda u: u.current_role == 'ADMIN')
def fraud_report_list(request):
    """Relatório Geral de Infracções Digitais para o Diretor."""
    blocked_students = Student.objects.filter(is_blocked_for_fraud=True).select_related('user', 'current_class')
    
    return render(request, 'finance/staff/fraud_report.html', {
        'students': blocked_students,
    })

@login_required
@user_passes_test(lambda u: u.current_role == 'ADMIN')
@transaction.atomic
def unblock_student_fraud(request, student_id):
    """Desbloqueio manual após conferência física dos documentos."""
    student = get_object_or_404(Student, id=student_id)
    
    # Rigor SOTARQ: Limpeza total e log de auditoria
    student.is_blocked_for_fraud = False
    student.fraud_lock_details = None
    student.save()
    
    # Criar log no StudentAuditLog que o senhor definiu em academic.models
    from apps.academic.models import StudentAuditLog
    StudentAuditLog.objects.create(
        student=student,
        changed_by=request.user,
        field_changed="Bloqueio de Segurança",
        old_value="INTERDITADO (FRAUDE)",
        new_value="LIBERADO (CONFERÊNCIA FÍSICA)"
    )
    
    messages.success(request, f"O acesso de {student.full_name} foi restaurado.")
    return redirect('finance:fraud_report')


