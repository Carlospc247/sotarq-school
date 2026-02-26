# apps/teachers/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from .models import Teacher, TeacherSubject

@login_required
def teacher_dashboard(request):
    """
    Painel principal do professor: Lista as turmas e disciplinas alocadas.
    """
    try:
        teacher = request.user.teacher_profile
    except Teacher.DoesNotExist:
        messages.error(request, "Você não possui perfil de professor.")
        return redirect('core:dashboard')  # ou outra página segura
    
    # Busca as alocações (Quem, O quê, Onde)
    my_allocations = TeacherSubject.objects.filter(
        teacher=teacher, 
        teacher__is_active=True # Filtro extra se adicionares no futuro
    ).select_related('subject', 'class_room')

    context = {
        'teacher': teacher,
        'allocations': my_allocations,
    }
    return render(request, 'teachers/dashboard.html', context)
