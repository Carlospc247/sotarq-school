# apps/core/admin_mixins.py
from django.contrib import admin
from django.contrib import messages
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.db.models import Q


class SaaSOnlyAdminMixin:
    """
    Acesso EXCLUSIVO ao esquema Public (Tu, o Dono do Sistema).
    
    Garante que apenas no schema 'public' estas funcionalidades são visíveis.
    Escolas NUNCA veem estes modelos no admin.
    """
    
    def has_module_permission(self, request):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name == 'public' and request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name == 'public' and request.user.is_superuser

    def has_add_permission(self, request):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name == 'public' and request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name == 'public' and request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name == 'public' and request.user.is_superuser


class TenantOnlyAdminMixin:
    """
    Acesso EXCLUSIVO às Escolas (Diretores e Admins da Escola).
    
    Estes modelos SÓ aparecem quando estamos num schema de tenant (escola).
    No schema public, são invisíveis.
    """
    
    def has_module_permission(self, request):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name != 'public'

    def has_view_permission(self, request, obj=None):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name != 'public'

    def has_add_permission(self, request):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name != 'public'

    def has_change_permission(self, request, obj=None):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name != 'public'

    def has_delete_permission(self, request, obj=None):
        if not hasattr(request, 'tenant'):
            return False
        return request.tenant.schema_name != 'public'


class TenantScopedAdminMixin:
    """
    FILTRO DE SEGURANÇA MÁXIMA para Admins de Escola.
    
    Este mixin garante:
    1. Esconde TODOS os campos sensíveis do sistema global
    2. Filtra permissões para não mostrar apps globais
    3. Impede visualização de dados de outras escolas
    4. Auto-preenche o tenant ao criar novos registos
    """
    
    # Apps que NUNCA devem ser visíveis para escolas
    GLOBAL_APPS = [
        'customers', 
        'keys', 
        'licenses', 
        'plans', 
        'billing', 
        'platform', 
        'saft',
        'django_tenants',
        'contenttypes',
        'sessions',
        'admin',
    ]
    
    # Campos que devem ser escondidos das escolas
    HIDDEN_FIELDS_FOR_TENANTS = [
        'tenant',
        'schema_name',
        'is_superuser',
    ]
    
    def get_queryset(self, request):
        """
        Filtra o queryset para mostrar apenas dados do tenant atual.
        """
        qs = super().get_queryset(request)
        
        # Se estamos no public, mostra tudo (admin global)
        if request.tenant.schema_name == 'public':
            return qs
        
        # Se o modelo tem campo tenant, filtra
        if hasattr(qs.model, 'tenant'):
            qs = qs.filter(tenant=request.tenant)
        
        return qs
    
    def get_exclude(self, request, obj=None):
        """
        Esconde campos sensíveis para admins de escola.
        """
        exclude = list(super().get_exclude(request, obj) or [])
        
        if request.tenant.schema_name != 'public':
            for field in self.HIDDEN_FIELDS_FOR_TENANTS:
                if hasattr(self.model, field) and field not in exclude:
                    exclude.append(field)
        
        return exclude or None
    
    def get_readonly_fields(self, request, obj=None):
        """
        Adiciona campos como readonly para escolas se necessário.
        """
        readonly = list(super().get_readonly_fields(request, obj) or [])
        
        # Escolas não podem alterar certos campos
        if request.tenant.schema_name != 'public':
            sensitive_readonly = ['created_at', 'updated_at', 'deleted_at']
            for field in sensitive_readonly:
                if hasattr(self.model, field) and field not in readonly:
                    readonly.append(field)
        
        return readonly
    
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Filtra ForeignKeys para mostrar apenas dados do tenant atual.
        """
        # Se estamos numa escola, nunca mostra o campo tenant
        if db_field.name == 'tenant':
            if request.tenant.schema_name != 'public':
                # Força o tenant atual e esconde o campo
                kwargs['queryset'] = db_field.related_model.objects.filter(
                    pk=request.tenant.pk
                )
                kwargs['initial'] = request.tenant
        
        # Filtra outras FKs pelo tenant se aplicável
        if request.tenant.schema_name != 'public':
            related_model = db_field.related_model
            if hasattr(related_model, 'tenant'):
                kwargs['queryset'] = related_model.objects.filter(
                    tenant=request.tenant
                )
        
        return super().formfield_for_foreignkey(db_field, request, **kwargs)
    
    def formfield_for_manytomany(self, db_field, request, **kwargs):
        """
        Filtra campos M2M para esconder apps e permissões globais.
        """
        # Filtro de Permissões - Esconde apps sensíveis
        if db_field.name in ["permissions", "user_permissions"]:
            if request.tenant.schema_name != 'public':
                kwargs["queryset"] = db_field.related_model.objects.exclude(
                    content_type__app_label__in=self.GLOBAL_APPS
                )
        
        # Filtra roles para mostrar apenas do tenant
        if db_field.name == 'roles':
            if request.tenant.schema_name != 'public':
                # Mostra apenas roles do sistema (is_system_role=True) 
                # ou roles customizados criados neste tenant
                from apps.core.models import Role
                kwargs["queryset"] = Role.objects.filter(
                    Q(is_system_role=True) | Q(pk__in=self._get_tenant_roles(request))
                )
        
        return super().formfield_for_manytomany(db_field, request, **kwargs)
    
    def _get_tenant_roles(self, request):
        """
        Retorna IDs de roles que pertencem ao tenant atual.
        """
        from apps.core.models import Role
        # Aqui podes adicionar lógica para roles específicas do tenant
        return Role.objects.filter(is_system_role=False).values_list('pk', flat=True)
    
    def save_model(self, request, obj, form, change):
        """
        Auto-preenche o tenant ao criar novos objetos numa escola.
        """
        if not change and hasattr(obj, 'tenant'):
            if request.tenant.schema_name != 'public':
                obj.tenant = request.tenant
        
        super().save_model(request, obj, form, change)
    
    def save_formset(self, request, form, formset, change):
        """
        Auto-preenche o tenant em inlines.
        """
        instances = formset.save(commit=False)
        
        for instance in instances:
            if hasattr(instance, 'tenant') and request.tenant.schema_name != 'public':
                instance.tenant = request.tenant
            instance.save()
        
        formset.save_m2m()


class HybridAdminMixin(TenantScopedAdminMixin):
    """
    Mixin para modelos que existem tanto no public quanto nos tenants,
    mas com comportamentos diferentes em cada contexto.
    
    - No PUBLIC: Vê TUDO (todos os tenants)
    - No TENANT: Vê apenas dados do próprio tenant
    """
    
    def has_module_permission(self, request):
        return True
    
    def has_view_permission(self, request, obj=None):
        if request.tenant.schema_name == 'public':
            return request.user.is_superuser
        return True
    
    def has_add_permission(self, request):
        return True
    
    def has_change_permission(self, request, obj=None):
        if request.tenant.schema_name == 'public':
            return request.user.is_superuser
        
        # No tenant, verifica se o objeto pertence ao tenant
        if obj and hasattr(obj, 'tenant'):
            return obj.tenant == request.tenant
        
        return True
    
    def has_delete_permission(self, request, obj=None):
        if request.tenant.schema_name == 'public':
            return request.user.is_superuser
        
        if obj and hasattr(obj, 'tenant'):
            return obj.tenant == request.tenant
        
        return True