# apps/customers/models.py
from django.conf import settings
from django.db import models
from django_tenants.models import TenantMixin, DomainMixin
from cloudinary.models import CloudinaryField
from apps.core.models import BaseModel



class SubAgent(BaseModel):
    """Subagentes: Podem ser Pessoas (BI) ou Empresas (NIF)."""
    # No seu arquivo de constantes ou no modelo de SubAgent
    SUBAGENT_PERMISSIONS = [
        ('can_view_assigned_tenants', 'Pode ver apenas as suas escolas'),
        ('can_activate_license', 'Pode ativar licenças (Pós-pagamento)'),
        ('can_suspend_license', 'Pode suspender por quebra de contrato'),
        ('can_view_billing_history', 'Pode ver histórico financeiro dos seus clientes'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    commission_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    is_verified = models.BooleanField(default=False)

    commission_pct = models.DecimalField(max_digits=5, decimal_places=2, default=10.00)

    def get_total_earned(self):
        """Soma total de comissões de faturas pagas pelos seus clientes."""
        return self.my_clients.filter(saasinvoice__status='paid').aggregate(
            total=models.Sum(models.F('saasinvoice__amount') * self.commission_pct / 100)
        )['total'] or 0


class Client(TenantMixin):
    name = models.CharField(max_length=100)
    sub_agent = models.ForeignKey(SubAgent, on_delete=models.SET_NULL, null=True, blank=True, related_name='my_clients') # A Escola (Tenant) vinculada a um Subagente.
    name = models.CharField(max_length=100)
    logo = CloudinaryField('logo', blank=True, null=True)
    primary_color = models.CharField(max_length=7, default='#4338ca') 
    secondary_color = models.CharField(max_length=7, default='#ffffff')

    #########
    address = models.TextField(blank=True, null=True, verbose_name="Endereço")
    phone = models.CharField(max_length=50, blank=True, null=True, verbose_name="Telefone")
    email = models.EmailField(blank=True, null=True)
    website = models.URLField(blank=True, null=True)
    nif = models.CharField(max_length=50, blank=True, null=True, verbose_name="NIF")  # Se não existir
    #########
    
    # Especialização K12 (Essencial para regras de notas automáticas)
    TYPE_CHOICES = (
        ('primario', 'Ensino Primário'),
        ('complexo', 'Complexo Escolar (I e II Ciclos)'),
        ('medio', 'Ensino Médio Técnico'),
        ('colegio', 'Colégio / Liceu'),
        ('formacao', 'Centro de Formação') # Acrescido e será usado como módulo e como CHOICE independente, igual ao complexo, por exemplo.
    )
    institution_type = models.CharField(max_length=20, choices=TYPE_CHOICES, default='complexo')
    
    is_active = models.BooleanField(default=True)
    created_on = models.DateField(auto_now_add=True)
    auto_create_schema = True

    @property
    def calculation_regime(self):
        """
        Retorna o regime de notas baseado no tipo da instituição.
        Isso é usado pelas Views e Models do Tenant para decidir o que exibir.
        """
        if self.institution_type == 'primario':
            return 'QUALITATIVE' # Apenas palavras até a 4ª classe
        return 'QUANTITATIVE'    # Números (Padrão para Secundário/Complexo)
    
    @property
    def get_legal_regime(self):
        """
        Retorna o regime jurídico aplicável.
        'GERAL': Decreto Executivo 424/25 (Primário e Secundário Geral)
        'TECNICO': Decreto Presidencial 167/23 (Médio Técnico)
        """
        if self.institution_type in ['medio']:
            return 'TECNICO'
        return 'GERAL'

    def __str__(self):
        return self.name

class Domain(DomainMixin):
    def __str__(self):
        return self.domain