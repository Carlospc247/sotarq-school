from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.conf import settings

from apps.core.models import JobApplication, SchoolConfiguration, User, Role, UserRole
from apps.core.forms import JobApplicationForm
from apps.teachers.models import Teacher
from apps.core.services import WhatsAppService 

def public_job_apply(request):
    config = SchoolConfiguration.objects.first()
    
    if not config or not config.is_recruitment_open:
        return render(request, 'errors/generic.html', {
            'title': 'Candidaturas Fechadas',
            'message': 'O processo de recrutamento não está ativo neste momento.'
        })

    if request.method == 'POST':
        form = JobApplicationForm(request.POST, request.FILES)
        if form.is_valid():
            application = form.save(commit=False)
            selection = form.cleaned_data.get('area_selection')
            if selection and selection != 'Custom':
                application.applied_area = selection
            application.save()
            messages.success(request, "Candidatura submetida com sucesso.")
            return redirect('core:public_about') 
    else:
        form = JobApplicationForm()

    return render(request, 'core/recruitment/public_form.html', {'form': form, 'config': config})

@login_required
def recruitment_dashboard(request):
    user = request.user
    # INCLUÍDO RH CONFORME SOLICITADO
    if user.current_role not in [Role.Type.ADMIN, Role.Type.DIRECTOR, Role.Type.RH]:
        messages.error(request, "Acesso não autorizado.")
        return redirect('core:dashboard')
        
    applications = JobApplication.objects.filter(status__in=['PENDING', 'INTERVIEW']).order_by('-created_at')
    
    # IMPORTANTE: Carregar config para o template (Cadeado e Modal)
    config = SchoolConfiguration.objects.first()
    
    return render(request, 'core/recruitment/dashboard.html', {
        'applications': applications,
        'config': config
    })

@login_required
@transaction.atomic
def hire_candidate(request, application_id):
    user_requesting = request.user
    if user_requesting.current_role not in [Role.Type.ADMIN, Role.Type.DIRECTOR, Role.Type.RH]:
        return redirect('core:dashboard')
        
    candidate = get_object_or_404(JobApplication, id=application_id)
    
    if User.objects.filter(email=candidate.email).exists():
        messages.error(request, f"O email {candidate.email} já está em uso.")
        return redirect('core:recruitment_dashboard')
        
    username = candidate.email.split('@')[0]
    default_password = "Mudar.123" 
    
    new_user = User.objects.create_user(
        username=username,
        email=candidate.email,
        password=default_password,
        first_name=candidate.full_name.split()[0],
        last_name=candidate.full_name.split()[-1] if len(candidate.full_name.split()) > 1 else "",
        tenant=request.user.tenant,
        is_active=True
    )
    
    is_teacher_position = 'professor' in candidate.applied_area.lower() or 'docente' in candidate.applied_area.lower()
    role_code = Role.Type.TEACHER if is_teacher_position else Role.Type.SECRETARY
    
    role_obj, _ = Role.objects.get_or_create(code=role_code)
    UserRole.objects.create(user=new_user, role=role_obj)
    
    new_user.current_role = role_code
    new_user.save()

    if role_code == Role.Type.TEACHER:
        import random
        emp_num = f"T{random.randint(10000, 99999)}"
        Teacher.objects.create(
            user=new_user,
            employee_number=emp_num,
            academic_degree="Não Especificado"
        )

    candidate.status = JobApplication.Status.HIRED
    candidate.save()
    
    if candidate.phone:
        ws = WhatsAppService()
        msg = (
            f"Olá {candidate.full_name}, parabéns!\n"
            f"Fostes admitido na SOTARQ School.\n"
            f"Utilizador: {username}\nSenha: {default_password}"
        )
        ws.send_message(candidate.phone, msg)

    messages.success(request, f"Funcionário {new_user.get_full_name()} contratado com sucesso.")
    return redirect('core:recruitment_dashboard')

# --- NOVAS FUNÇÕES PARA O DASHBOARD (CADEADO E MODAL) ---

@login_required
def toggle_recruitment_status(request):
    """Abre ou Fecha o recrutamento."""
    if request.user.current_role not in [Role.Type.ADMIN, Role.Type.DIRECTOR, Role.Type.RH]:
        return redirect('core:dashboard')

    if request.method == 'POST':
        config = SchoolConfiguration.objects.first()
        if config:
            config.is_recruitment_open = not config.is_recruitment_open
            config.save()
            status = "aberto" if config.is_recruitment_open else "fechado"
            messages.success(request, f"Recrutamento {status}.")
            
    return redirect('core:recruitment_dashboard')

@login_required
def update_job_areas(request):
    """Salva as vagas definidas no Modal."""
    if request.user.current_role not in [Role.Type.ADMIN, Role.Type.DIRECTOR, Role.Type.RH]:
        return redirect('core:dashboard')

    if request.method == 'POST':
        areas = request.POST.get('available_job_areas', '')
        config = SchoolConfiguration.objects.first()
        if config:
            config.available_job_areas = areas
            config.save()
            messages.success(request, "Vagas atualizadas com sucesso.")
            
    return redirect('core:recruitment_dashboard')





@login_required
def delete_candidate(request, application_id):
    """Apaga uma candidatura."""
    if request.user.current_role not in [Role.Type.ADMIN, Role.Type.DIRECTOR, Role.Type.RH]:
        messages.error(request, "Acesso não autorizado.")
        return redirect('core:dashboard')

    if request.method == 'POST':
        candidate = get_object_or_404(JobApplication, id=application_id)
        candidate.delete() # Soft delete se estiver usando BaseModel, ou Hard delete
        messages.success(request, "Candidatura eliminada com sucesso.")
    
    return redirect('core:recruitment_dashboard')

@login_required
def send_candidate_whatsapp(request):
    """Envia mensagem personalizada via WhatsApp API."""
    if request.user.current_role not in [Role.Type.ADMIN, Role.Type.DIRECTOR, Role.Type.RH]:
        return redirect('core:dashboard')

    if request.method == 'POST':
        app_id = request.POST.get('candidate_id')
        message_text = request.POST.get('message_text')
        
        candidate = get_object_or_404(JobApplication, id=app_id)
        
        if candidate.phone and message_text:
            ws = WhatsAppService()
            # Envia a mensagem usando o serviço existente
            try:
                ws.send_message(candidate.phone, message_text)
                messages.success(request, f"Mensagem enviada para {candidate.full_name}.")
            except Exception as e:
                messages.error(request, f"Erro ao enviar: {str(e)}")
        else:
            messages.error(request, "Telefone ou mensagem inválidos.")
            
    return redirect('core:recruitment_dashboard')





