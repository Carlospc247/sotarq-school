from django.views.generic import ListView, CreateView
from django.urls import reverse_lazy
from django.db import transaction
from .models import Client, Domain

class AdminClientListView(ListView):
    model = Client
    template_name = 'customers/client_list.html'
    context_object_name = 'tenants'
    # Ordenar por criação para ver as escolas mais recentes primeiro
    ordering = ['-created_on']

class AdminClientCreateView(CreateView):
    model = Client
    template_name = 'customers/client_form.html'
    # Removido 'domain_url' porque ele não existe no modelo Client
    fields = ['schema_name', 'name', 'institution_type', 'primary_color', 'logo']
    success_url = reverse_lazy('customers:client_list')

    @transaction.atomic
    def form_valid(self, form):
        # 1. Salva o Client (Tenant)
        response = super().form_valid(form)
        
        # 2. Cria o Domínio associado automaticamente
        # Nota: Em produção, o domain deve incluir o seu domínio principal
        domain_name = f"{self.object.schema_name}.sotarq.com" 
        
        Domain.objects.create(
            domain=domain_name,
            tenant=self.object,
            is_primary=True
        )
        
        return response

