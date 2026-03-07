# apps/academic/middleware.py
from django.shortcuts import redirect
from django.contrib import messages
from django.urls import resolve
from .models import AcademicEvent

class AcademicLockMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 0. RIGOR SOTARQ: Se estivermos no schema 'public', saímos imediatamente.
        # Não existe lógica académica no nível de infraestrutura global.
        if not hasattr(request, 'tenant') or request.tenant.schema_name == 'public':
            return self.get_response(request)

        if not request.user.is_authenticated:
            return self.get_response(request)

        # 1. Identifica se a URL atual é de lançamento de notas
        # Usamos try/except porque o resolve pode falhar em URLs de outros apps
        try:
            current_url_name = resolve(request.path_info).url_name
        except:
            current_url_name = None
            
        protected_urls = ['grading_sheet', 'mass_grade_entry', 'update_grade_ajax']

        if current_url_name in protected_urls:
            # 2. Busca o estado da Pausa no Tenant atual
            lock_event = AcademicEvent.objects.filter(category='HOLIDAY', klass__isnull=True).first()
            
            if lock_event and lock_event.is_pedagogical_break:
                # 3. Verifica exceções
                is_exception = False
                try:
                    # Diretores e Admins nunca são bloqueados (Cheque rápido de role)
                    if request.user.current_role in ['ADMIN', 'DIRECTOR']:
                        is_exception = True
                    elif hasattr(request.user, 'teacher_profile'):
                        is_exception = lock_event.break_exceptions.filter(id=request.user.teacher_profile.id).exists()
                except:
                    pass

                if not is_exception:
                    messages.error(request, "ACESSO BLOQUEADO: O sistema está em Pausa Pedagógica para apuramento de notas.")
                    return redirect('academic:student_dashboard')

        return self.get_response(request)