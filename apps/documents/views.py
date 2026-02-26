from django.shortcuts import render, get_object_or_404
from django.http import Http404, HttpResponseForbidden
from django.utils import timezone
from .models import DocumentAccessToken
from django_tenants.utils import get_tenant_domain_model, get_public_schema_name, schema_context

def verify_document_view(request, token_uuid):
    """
    View acessível publicamente no domínio principal para verificar a autenticidade de um documento.
    """
    token_obj = get_object_or_404(DocumentAccessToken, token=token_uuid)

    # Marcar como usado se o token for de uso único (com base na sua lógica 'used_at')
    if token_obj.used_at is None:
        token_obj.used_at = timezone.now()
        token_obj.save()

    # Verificar a validade do token (expiração, uso único)
    if not token_obj.is_valid():
        return HttpResponseForbidden("Este token de verificação é inválido ou já foi utilizado.")

    # Acessar o documento através do contexto do tenant correto
    # Isso garante que mesmo estando no domínio público, acessamos o DB do tenant original
    tenant = token_obj.document.student.enrollments.first().academic_year.tenant # Exemplo de como chegar ao tenant
    
    with schema_context(tenant.schema_name):
        # Recarregar o documento no contexto do tenant
        document = token_obj.document 
        
        context = {
            'token_obj': token_obj,
            'document': document,
            'student': document.student,
            'tenant_name': tenant.name, # Nome da escola que emitiu
            'verification_status': 'AUTÊNTICO' if token_obj.is_valid() else 'INVÁLIDO',
        }
        return render(request, 'documents/verification_result.html', context)