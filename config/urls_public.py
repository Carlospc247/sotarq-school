# config/urls_public.py
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.http import Http404
from django.http import HttpResponse

def tenant_router(request, *args, **kwargs):
    """
    FORÇA O DIRECIONAMENTO: Se houver um tenant, ele ignora este arquivo 
    e vai para o urls_tenants.
    """
    from django.urls import resolve, create_urlconf, set_urlconf
    import importlib
    
    # Se o middleware já identificou o tenant, forçamos o uso do urls_tenants
    if hasattr(request, 'tenant') and request.tenant.schema_name != 'public':
        urlconf = 'config.urls_tenants'
        set_urlconf(urlconf)
        # Tenta resolver a URL dentro do tenant
        try:
            resolver = importlib.import_module(urlconf)
            return include(resolver.urlpatterns)
        except Exception:
            pass

    # Caso contrário, segue o fluxo normal do public
    return []

def robots_txt(request):
    content = "User-agent: *\nDisallow: /admin/" # Protege o admin global de robôs
    return HttpResponse(content, content_type="text/plain")

urlpatterns = [
    path('admin/', admin.site.urls),
    #path('', include('apps.core.urls_public')),
    path('platform/', include('apps.platform.urls')),
    path('tenants/', include('apps.customers.urls')),
    path('billing/', include('apps.billing.urls')),
    
    # ESTA É A LINHA QUE MATA O PROBLEMA:
    # Se nada acima bater, e for um subdomínio, ele tenta o urls_tenants
    path('', include('config.urls_tenants')),
    path("robots.txt", robots_txt, name="robots_txt"),
]