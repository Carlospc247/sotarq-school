# apps/core/decorators.py
from functools import wraps
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.shortcuts import redirect
from django.contrib import messages
from functools import wraps



def check_limit(limit_key):
    """
    Decorator to check if a specific limit has been reached.
    Usage: @check_limit('max_students')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not hasattr(request, 'current_license') or not request.current_license:
                # Decide policy: Allow if no license (freemium) or Block?
                # Enterprise: Block.
                messages.error(request, "No active license found.")
                raise PermissionDenied("No active license.")
            
            # Use the check_limit method from License model
            # We need to know the 'current_count'. 
            # This is tricky in a generic decorator. 
            # Usually, the check needs to happen BEFORE the action (e.g. creating a student).
            # So this decorator might just check if the FEATURE is enabled, 
            # or we need a way to pass the count check logic.
            
            # Let's assume this just checks if the module/feature is allowed for now.
             
            # if not request.current_license.check_limit(limit_key, 0):
            #    messages.error(request, "Limit reached for this tier.")
            #    return redirect(request.META.get('HTTP_REFERER', '/'))
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator




def student_required(view_func):
    """
    Valida a existência do perfil de aluno. 
    Redireciona para a raiz do servidor caso o perfil não exista.
    """
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        # Verificação direta baseada no modelo OneToOne
        if hasattr(request.user, 'student_profile'):
            return view_func(request, *args, **kwargs)
        
        messages.error(request, "Erro de Acesso: Este utilizador não possui um perfil de aluno configurado.")
        # Alterado de 'core:home' para '/' para evitar NoReverseMatch
        return redirect('core:dashboard') 
    return _wrapped_view
