# apps/finance/views_portal.py
from decimal import Decimal
from pyexpat.errors import messages
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from apps.finance.models import Invoice, Payment, PaymentMethod
from apps.students.models import Student

@login_required
def upload_proof(request, invoice_id):
    if request.method == 'POST' and request.FILES.get('proof'):
        invoice = get_object_or_404(Invoice, id=invoice_id, student__user=request.user)
        proof = request.FILES['proof']
        
        # 1. Registro do Pagamento PENDING
        payment = Payment.objects.create(
            invoice=invoice,
            amount=invoice.calculate_current_total(), # Usa sua função de mora
            method=PaymentMethod.objects.get(method_type='TR'), # Ex: Transferência
            proof_file=proof,
            validation_status='pending'
        )

        # 2. Perícia Digital SOTARQ
        is_fraud, details = AntiFraudEngine.analyze_file(payment.proof_file.path)

        if is_fraud:
            # RIGOR: Bloqueio no modelo STUDENT fornecido pelo chefe
            student = invoice.student
            student.is_blocked_for_fraud = True
            student.fraud_lock_details = f"Metadados suspeitos em {timezone.now()}: {details}"
            student.save()

            # Registro no Pagamento para o Tesoureiro ver
            payment.is_suspicious = True
            payment.fraud_details = {"errors": details}
            payment.save()

            messages.error(request, "ALERTA: Documento inválido. A sua conta foi suspensa por motivos de segurança.")
            return redirect('portal:blocked_page')
        
        messages.success(request, "Comprovativo enviado! A tesouraria foi notificada.")
        return redirect('portal:dashboard')

    return redirect('portal:dashboard')

# apps/portal/views.py (ou views_portal.py)
from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def blocked_page(request):
    """Página dinâmica de interdição por fraude."""
    # Rigor: Acessamos o profile definido na OneToOneField do Aluno
    student = getattr(request.user, 'student_profile', None)
    
    if not student or not student.is_blocked_for_fraud:
        # Se o aluno não estiver bloqueado, ele não deve estar nesta página
        return redirect('portal:dashboard')

    return render(request, 'portal/blocked_page.html', {
        'student': student,
        'lock_reason': student.fraud_lock_details,
        'lock_date': student.updated_at # Campo do seu BaseModel
    })

