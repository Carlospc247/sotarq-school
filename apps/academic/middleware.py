# apps/academic/middleware.py
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve
from .models import AcademicEvent

class AcademicLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not request.user.is_authenticated:
            return self.get_response(request)

        # 1. Identifica se a URL atual é de lançamento de notas
        current_url_name = resolve(request.path_info).url_name
        protected_urls = ['grading_sheet', 'mass_grade_entry', 'update_grade_ajax']

        if current_url_name in protected_urls:
            # 2. Busca o estado da Pausa no Tenant atual
            lock_event = AcademicEvent.objects.filter(category='HOLIDAY', klass__isnull=True).first()
            
            if lock_event and lock_event.is_pedagogical_break:
                # 3. Verifica exceções
                is_exception = False
                try:
                    if hasattr(request.user, 'teacher_profile'):
                        is_exception = lock_event.break_exceptions.filter(id=request.user.teacher_profile.id).exists()
                    
                    # Diretores e Admins nunca são bloqueados
                    if request.user.current_role in ['ADMIN', 'DIRECTOR']:
                        is_exception = True
                except:
                    pass

                if not is_exception:
                    messages.error(request, "ACESSO BLOQUEADO: O sistema está em Pausa Pedagógica para apuramento de notas.")
                    return redirect('academic:student_dashboard')

        return self.get_response(request)