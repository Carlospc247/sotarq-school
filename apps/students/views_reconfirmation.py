# apps/students/views_reconfirmation.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db import transaction
from apps.core.models import SchoolConfiguration, Notification, User, Role
from apps.students.models import Student, EnrollmentRequest
from .forms import ReconfirmationForm
from django.contrib.auth.decorators import user_passes_test
from django.views.decorators.http import require_POST



def check_reconfirmation_window(request):
    config = SchoolConfiguration.objects.first()
    if not config or not config.check_reconfirmation_window():
        return False
    return True

def notify_admin_reconfirmation(req):
    admins = User.objects.filter(
        tenant=req.student.user.tenant, 
        current_role__in=[Role.Type.ADMIN, Role.Type.DIRECTOR]
    )
    for admin in admins:
        Notification.objects.create(
            user=admin,
            title="Nova Reconfirmação 🔄",
            message=f"O aluno {req.student.full_name} solicitou reconfirmação.",
            link=f"/management/enrollments/{req.id}/"
        )





# Função auxiliar para verificar se é Staff
def is_staff_check(user):
    return user.is_staff

@login_required
@user_passes_test(is_staff_check) # Bloqueia acesso público
@require_POST
def internal_reconfirmation_process(request):
    """
    Processa a reconfirmação feita presencialmente no balcão.
    """
    if request.method == 'POST':
        student_id = request.POST.get('student_id') # Vem do input hidden ou text
        
    if not check_reconfirmation_window(request):
        messages.error(request, "O período de reconfirmação está fechado nas configurações.")
        return redirect('students:student_list')

    student_reg_number = request.POST.get('student_id') # O input chama-se student_id mas é o Nº de Matrícula
    payment_proof = request.FILES.get('doc_payment_proof')

    if not student_reg_number:
        messages.error(request, "Deve indicar o Nº de Matrícula.")
        return redirect('students:student_list')

    # 1. Tentar encontrar o aluno
    try:
        student = Student.objects.get(registration_number=student_reg_number)
    except Student.DoesNotExist:
        messages.error(request, f"Aluno com Nº {student_reg_number} não encontrado.")
        return redirect('students:student_list')
    
    student = Student.objects.get(registration_number=student_id) # Exemplo

    # CAPTURA DA FOTO NO POST
    photo = request.FILES.get('photo_passport_file')

    # 2. Verificar se já existe pedido pendente
    if EnrollmentRequest.objects.filter(student=student, status='pending').exists():
        messages.warning(request, f"O aluno {student.full_name} já tem uma reconfirmação pendente.")
        return redirect('students:student_list')

    # 3. Criar o Pedido Interno
    try:
        req = EnrollmentRequest.objects.create(
            student=student,
            request_type=EnrollmentRequest.RequestType.RECONFIRMATION,
            status='pending', # Fica pendente para validação financeira ou 'confirmed' se quiser aprovar direto
            doc_payment_proof=payment_proof,
            photo_passport=photo if photo else None,
            guardian_name=f"Presencial: {request.user.username}" # Regista quem fez a operação
        )
        
        notify_admin_reconfirmation(req)
        messages.success(request, f"Reconfirmação presencial registada para {student.full_name}.")
        
    except Exception as e:
        messages.error(request, f"Erro ao processar: {str(e)}")

    return redirect('students:student_list')



@login_required
@transaction.atomic
def portal_reconfirmation(request):
    if not check_reconfirmation_window(request):
        messages.error(request, "O período de reconfirmação encontra-se encerrado.")
        return redirect('portal:dashboard')

    target_student = None
    if hasattr(request.user, 'student_profile'):
        target_student = request.user.student_profile
    elif hasattr(request.user, 'guardian_profile'):
        student_id = request.GET.get('student_id')
        if student_id:
            target_student = Student.objects.filter(id=student_id, guardians__guardian__user=request.user).first()
    
    if not target_student:
        messages.error(request, "Aluno não identificado.")
        return redirect('portal:dashboard')

    if request.method == 'POST':
        form = ReconfirmationForm(request.POST, request.FILES)
        if form.is_valid():
            req = form.save(commit=False)
            req.student = target_student
            req.request_type = EnrollmentRequest.RequestType.RECONFIRMATION
            req.status = 'pending' 
            req.save()
            notify_admin_reconfirmation(req)
            messages.success(request, f"Reconfirmação submetida para {target_student.full_name}.")
            return redirect('portal:dashboard')
    else:
        form = ReconfirmationForm()

    return render(request, 'students/portal/reconfirmation_form.html', {'form': form, 'student': target_student})


