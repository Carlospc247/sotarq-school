from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Role, UserRole, SupportTicket, HelpArticle, Notification, SchoolConfiguration

class UserRoleInline(admin.TabularInline):
    model = UserRole
    extra = 1


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    inlines = [UserRoleInline]
    list_display = ('username', 'email', 'tenant', 'current_role', 'is_staff')
    list_filter = ('tenant', 'is_staff', 'is_superuser')
    fieldsets = UserAdmin.fieldsets + (
        ('Sotarq School Context', {'fields': ('tenant', 'current_role')}),
    )

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(tenant=request.tenant)

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'is_system_role')
    filter_horizontal = ('permissions',)

#@admin.register(SchoolConfiguration)
#class SchoolConfigurationAdmin(admin.ModelAdmin):
#    list_display = ('school_name', 'tax_id', 'official_email')
# apps/core/admin.py

@admin.register(SchoolConfiguration)
class SchoolConfigurationAdmin(admin.ModelAdmin):
    # 1. LISTAGEM: Permite identificar rapidamente qual Tenant (Escola) você vai editar
    #list_display = ('school_name', 'tax_id', 'official_email', 'news_ticker')
    list_display = ('school_name', 'nif', 'official_email', 'news_ticker')
    
    # 2. BUSCA: A "opção de escolher o tenant" é feita através da busca pelo nome da escola
    search_fields = ('school_name', 'nif', 'official_email')
    
    # 3. FILTROS: Útil para ver quais escolas estão com matrículas abertas ou modos de exibição específicos
    list_filter = ('hero_mode', 'is_enrollment_open')

    # 4. ORGANIZAÇÃO (FIELDSETS): Agrupa os dados para facilitar a sua gestão de conteúdo
    fieldsets = (
        # Identificação do Tenant
        ('Identificação da Escola (Tenant)', {
            'fields': ('school_name', 'nif', 'official_email'),
            'description': 'Dados principais para identificar o cliente.'
        }),

        # --- ÁREA DE GESTÃO DE CONTEÚDO (O seu foco principal) ---
        ('Gestão de Conteúdo & Marketing (Admin Global)', {
            'fields': ('news_ticker', 'custom_html_content'),
            'description': 'Use esta área para publicar novidades na barra de topo ou inserir scripts/anúncios HTML no site desta escola.',
            'classes': ('wide', 'extrapretty'), # Destaque visual no Django Admin
        }),

        # Aparência do Site (Hero Section)
        ('Portal do Aluno (Hero & Banner)', {
            'fields': ('hero_mode', 'hero_title', 'hero_subtitle', 'hero_image_1', 'hero_image_2', 'hero_image_3'),
            'classes': ('collapse',), # Oculto por padrão para limpar a visualização
        }),

        # Identidade Visual
        ('Branding', {
            'fields': ('logo', 'favicon', 'primary_color', 'secondary_color')
        }),

        # Dados Financeiros e Contato
        ('Dados Financeiros & Localização', {
            'fields': ('bank_name', 'iban_primary', 'phone_contact', 'address')
        }),

        # Redes Sociais
        ('Presença Digital', {
            'fields': ('website_link', 'facebook_link', 'instagram_link', 'linkedin_link'),
            'classes': ('collapse',)
        }),

        # Permissões do Sistema
        ('Permissões e Acessos', {
            'fields': ('is_enrollment_open', 'allow_secretary_export', 'allow_secretary_import', 'allow_teacher_export')
        }),
    )

    # Ordenação padrão alfabética para facilitar encontrar a escola
    ordering = ('school_name',)

