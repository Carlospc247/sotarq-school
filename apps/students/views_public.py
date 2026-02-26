# apps/students/views_public.py
from django.shortcuts import render, redirect
from django.db import transaction
from django.utils import timezone
from django.contrib import messages
from django.conf import settings

from apps.core.models import SchoolConfiguration, User, Role, UserRole
from apps.academic.models import Course, GradeLevel
from apps.finance.models import Invoice, InvoiceItem, FeeType
from .models import Student, EnrollmentRequest

@transaction.atomic
def public_enrollment_form(request):
    config = SchoolConfiguration.objects.first()
    
    # VALIDACÃO DE SEGURANÇA: Se estiver fechado ou fora do prazo, bloqueia.
    if not config or not config.check_enrollment_window():
        return render(request, 'errors/generic.html', {
            'title': 'Matrículas Encerradas', 
            'message': 'O período de candidaturas não está ativo no momento.'
        })
    if request.method == 'POST':
        try:
            data = request.POST
            files = request.FILES
            
            full_name = data.get('full_name')
            email = data.get('guardian_email')
            phone = data.get('guardian_phone')
            
            # Validação
            if User.objects.filter(username=email).exists():
                messages.error(request, "Este email já possui conta. Faça login no portal.")
                return redirect('core:login')

            # 1. User
            user_password = getattr(settings, 'DEFAULT_CANDIDATE_PASSWORD', 'Sotarq.Mudar123')
            user = User.objects.create_user(
                username=email,
                email=email,
                password=user_password,
                first_name=full_name.split()[0],
                last_name=full_name.split()[-1] if len(full_name.split()) > 1 else "",
                current_role=Role.Type.STUDENT,
                is_active=True 
            )
            
            role_student, _ = Role.objects.get_or_create(code=Role.Type.STUDENT)
            UserRole.objects.create(user=user, role=role_student)

            # 2. Student
            student = Student.objects.create(
                user=user,
                full_name=full_name,
                gender=data.get('gender', 'M'),
                birth_date=data.get('birth_date'),
                registration_number=f"CAND-{timezone.now().strftime('%Y%m%d%H%M')}", 
                is_active=False, 
            )

            # 3. Enrollment Request (Unificado com novos campos)
            enrollment_req = EnrollmentRequest.objects.create(
                student=student,
                course_id=data.get('course_id'),
                grade_level_id=data.get('grade_level_id'),
                guardian_name=data.get('guardian_name'),
                guardian_phone=phone,
                guardian_email=email,
                
                # Ficheiros
                doc_bi=files.get('doc_bi'),
                doc_health=files.get('doc_health'),
                doc_certificate=files.get('doc_certificate'),
                photo_passport=files.get('photo_passport'),
                
                # Dados Clínicos
                has_special_needs=data.get('has_special_needs') == 'True',
                observations=data.get('observations'),
                
                status='pending_payment'
            )

            # 4. Financeiro
            fee, _ = FeeType.objects.get_or_create(
                name__icontains="Matrícula", 
                defaults={'name': 'Taxa de Inscrição', 'amount': 5000.00}
            )
            
            invoice = Invoice.objects.create(
                student=student,
                total=fee.amount,
                due_date=timezone.now().date(),
                status='pending',
                doc_type='FT'
            )
            
            InvoiceItem.objects.create(
                invoice=invoice,
                fee_type=fee,
                description=f"Taxa de Inscrição - {full_name}",
                amount=fee.amount
            )
            
            enrollment_req.invoice = invoice
            enrollment_req.save()

            messages.success(request, "Candidatura submetida! Prossiga para o pagamento.")
            return redirect('finance:checkout', invoice_id=invoice.id)

        except Exception as e:
            messages.error(request, f"Erro: {str(e)}")
            # Log em produção seria ideal aqui
    
    context = {
        'courses': Course.objects.all(),
        'levels': GradeLevel.objects.all().order_by('level_index'), # Ordenação correta
    }

    return render(request, 'students/public/enrollment_form.html', context)



