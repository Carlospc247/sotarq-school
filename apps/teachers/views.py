# apps/teachers/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy

from apps.academic.models import Class, Subject
from apps.teachers.forms import TeacherAllocationForm
from .models import Teacher, TeacherSubject
from django.views.generic import CreateView, DeleteView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import JsonResponse



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



def get_subjects_by_class(request):
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse([], safe=False)
    
    try:
        klass = Class.objects.get(id=class_id)
        # Buscamos as disciplinas que pertencem ao GradeLevel desta Turma
        subjects = Subject.objects.filter(grade_level=klass.grade_level).values('id', 'name')
        return JsonResponse(list(subjects), safe=False)
    except Class.DoesNotExist:
        return JsonResponse([], safe=False)
    

class TeacherAllocationListView(LoginRequiredMixin, ListView):
    model = TeacherSubject
    template_name = 'teachers/allocation_list.html'
    context_object_name = 'allocations'

    def get_queryset(self):
        # Garantimos o isolamento Multi-tenant
        return TeacherSubject.objects.filter(
            class_room__academic_year__is_active=True,
            teacher__user__tenant=self.request.user.tenant 
        ).select_related('teacher', 'subject', 'class_room', 'subject__grade_level')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Passamos o tenant atual para o formulário do modal
        context['form'] = TeacherAllocationForm(school=self.request.user.tenant)
        return context


class TeacherAllocationCreateView(LoginRequiredMixin, CreateView):
    model = TeacherSubject
    form_class = TeacherAllocationForm
    template_name = 'teachers/allocation_list.html' 
    success_url = reverse_lazy('teachers:allocation_list')

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        # Consistência com o campo 'tenant' do seu User model
        kwargs['school'] = self.request.user.tenant
        return kwargs

    def form_invalid(self, form):
        # Em caso de erro, recarregamos a lista com o contexto do tenant
        messages.error(self.request, "Erro na alocação. Verifique se este professor já não está nesta turma/disciplina.")
        
        # Usamos o get_queryset da ListView para manter o rigor
        allocations = TeacherSubject.objects.filter(
            class_room__academic_year__is_active=True,
            teacher__user__tenant=self.request.user.tenant 
        ).select_related('teacher', 'subject', 'class_room')

        return self.render_to_response(self.get_context_data(
            form=form,
            allocations=allocations,
            open_modal_on_load=True 
        ))


class TeacherAllocationDeleteView(DeleteView):
    model = TeacherSubject
    success_url = reverse_lazy('teachers:allocation_list')

    def get_queryset(self):
        # RIGOR SOTARQ: Garante que só deleta alocações do próprio Tenant
        return self.model.objects.filter(tenant=self.request.user.tenant)

    def delete(self, request, *args, **kwargs):
        messages.success(request, "Alocação removida com sucesso!")
        return super().delete(request, *args, **kwargs)


