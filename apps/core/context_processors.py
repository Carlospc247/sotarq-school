# apps/core/context_processors.py
from django.conf import settings
from apps.core.models import SchoolConfiguration
from apps.licenses.models import License
from apps.plans.models import PlanModule



def active_modules_processor(request):
    """SOTARQ Dynamic Menu Engine: Suporta Módulo de Formação Profissional."""
    if not hasattr(request, 'user') or not request.user.is_authenticated:
        return {'active_modules': []}

    if not hasattr(request, 'tenant') or request.tenant.schema_name == 'public':
        return {'active_modules': ['platform', 'billing', 'customers', 'core', 'formacao']}

    try:
        # Recupera licença com cache (simulado)
        license_obj = License.objects.filter(tenant=request.tenant, is_active=True).latest('created_at')
        
        plan_modules = PlanModule.objects.filter(plan=license_obj.plan).values_list('module__code', flat=True)
        extra_modules = license_obj.additional_modules.all().values_list('code', flat=True)
        
        # Mapeia tipologia para módulo automático
        # Se a escola é do tipo 'formacao', o módulo é ativado nativamente
        auto_modules = []
        if request.tenant.institution_type == 'formacao':
            auto_modules.append('formacao')

        active_modules = list(set(list(plan_modules) + list(extra_modules) + auto_modules))
        return {'active_modules': active_modules}
        
    except Exception:
        return {'active_modules': []}


def school_branding(request):
    """
    SOTARQ Access Control Engine v2.0
    Verifica granularmente:
    1. Acesso ao Site (Visual)
    2. Acesso às Matrículas (Funcional)
    """
    # Contexto padrão (Tudo bloqueado)
    context = {
        'school_branding': None,
        'site_access_blocked': True,      # Bloqueia o site todo
        'enrollment_access_blocked': True, # Bloqueia apenas o botão de matrículas
        'AGT_CERTIFICATE_NUMBER': getattr(settings, 'AGT_CERTIFICATE_NUMBER', 'Pendente')
    }

    if not hasattr(request, 'tenant') or request.tenant.schema_name == 'public':
        context['site_access_blocked'] = False
        context['enrollment_access_blocked'] = False
        return context

    try:
        # Busca a licença ativa (Cachear isto em produção é vital)
        active_license = License.objects.filter(tenant=request.tenant, is_active=True).latest('created_at')
        
        # Recupera todos os códigos de módulos ativos (Plano + Extras)
        plan_modules = set(PlanModule.objects.filter(plan=active_license.plan).values_list('module__code', flat=True))
        extra_modules = set(active_license.additional_modules.all().values_list('code', flat=True))
        all_active_modules = plan_modules.union(extra_modules)

        # --- VERIFICAÇÃO 1: SITE INSTITUCIONAL ---
        if 'site_institucional' in all_active_modules:
            context['site_access_blocked'] = False
            
            # Carrega a config apenas se tiver acesso ao site
            try:
                config = SchoolConfiguration.objects.first()
                if config:
                    context['school_branding'] = config
            except Exception:
                pass

        # --- VERIFICAÇÃO 2: MATRÍCULAS ONLINE (Independente do Site) ---
        if 'matriculas_online' in all_active_modules:
            context['enrollment_access_blocked'] = False

    except Exception:
        # Em caso de erro (sem licença), mantém tudo bloqueado por segurança
        pass

    return context


def school_theme(request):
    # Obtém a configuração (cache amigável para performance)
    config = SchoolConfiguration.objects.first()
    return {
        'school_config': config
    }