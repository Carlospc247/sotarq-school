# apps/core/admin_site.py
from django.contrib.admin import AdminSite
from django.utils.translation import gettext_lazy as _


class SchoolAdminSite(AdminSite):
    """
    Site de Admin customizado que adapta o título e branding
    conforme o contexto (escola vs global).
    """
    
    site_header = _("Sistema de Gestão Escolar")
    site_title = _("SGE Admin")
    index_title = _("Painel de Administração")
    
    def each_context(self, request):
        context = super().each_context(request)
        
        if hasattr(request, 'tenant'):
            if request.tenant.schema_name == 'public':
                context['site_header'] = _("SGE - Administração Global")
                context['site_title'] = _("SGE Global")
                context['index_title'] = _("Gestão do Sistema SaaS")
            else:
                context['site_header'] = f"{request.tenant.name}"
                context['site_title'] = f"{request.tenant.name}"
                context['index_title'] = _("Painel de Administração")
        
        return context


# Instância do admin site customizado
school_admin_site = SchoolAdminSite(name='school_admin')