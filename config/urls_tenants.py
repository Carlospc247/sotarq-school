#urls_tenants.py
print("!!! CARREGANDO URLS DO TENANT !!!")
from django.urls import path
from apps.billing.views import billing_webhook
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.views.generic import RedirectView


# Título do Admin (Para ficar profissional)
admin.site.site_header = "Sotarq School | Administração"
admin.site.site_title = "Portal Admin"
admin.site.index_title = "Gestão do Sistema"

urlpatterns = [
    # 1. Administração (Acesso ao Cofre de Chaves, Utilizadores, etc.)
    path('', RedirectView.as_view(pattern_name='core:login', permanent=False)),
    path('', include('apps.core.urls')), 
    
    #path('admin/', admin.site.urls), # REMOVI PORQUE, CADA ESCOLA NÃO DEVE TER SEU PRÓPRIO DJANGO-ADMIN
    # e também para evitar avisos de erros de duas rotas admin no sistema.

    # Agrupamento de módulos por funcionalidade
    path('academic/', include('apps.academic.urls', namespace='academic')),
    path('teachers/', include('apps.teachers.urls', namespace='teachers')),
    path('students/', include('apps.students.urls', namespace='students')),
    path('transport/', include('apps.transport.urls', namespace='transport')),
    path('portal/', include('apps.portal.urls', namespace='portal')),
    path('finance/', include('apps.finance.urls')),
    path('saft/', include('apps.saft.urls')),
    path('library/', include('apps.library.urls')),
    path('inventory/', include('apps.inventory.urls')),
    path('reports/', include('apps.reports.urls')),
    path('audit/', include('apps.audit.urls')),
    path('fiscal/', include('apps.fiscal.urls')),
    path('compras/', include('apps.compras.urls')),
    path('documents/', include('apps.documents.urls')),
    path('accounts/', include('apps.accounts.urls')),

    path('billing/webhook-gateway-secret-123/', billing_webhook, name='billing_webhook'),

    #path('', include('apps.core.urls', namespace='core')), # ATENÇÃO: Mantenha sempre no final da lista porque contém a rota vazia ''.
    #path('', include('apps.core.urls')),
]

if settings.DEBUG:
    # Desenvolvimento: Django serve tudo
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
else:
    # Produção: O Nginx ou WhiteNoise cuidam disso. 
    # Deixamos as URLs limpas para performance.
    pass