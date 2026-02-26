import datetime
import logging
from django.db import models
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)

def generate_document_number(instance_or_model, prefix):
    """
    Gera: [SIGLA] [5_LETRAS_TENANT][ANO]/[SEQUENCIA]
    Ex: FR NEWAY2026/001
    """
    from django.db import connection
    tenant = connection.tenant
    
    tenant_slug = "".join(filter(str.isalnum, tenant.name)).upper()[:5]
    year = datetime.datetime.now().year
    
    model_class = instance_or_model if isinstance(instance_or_model, type) else instance_or_model.__class__
    
    search_pattern = f"{prefix} {tenant_slug}{year}/"
    
    last_doc = model_class.objects.filter(
        numero_documento__startswith=search_pattern 
    ).order_by('numero').last()

    if not last_doc:
        new_sequence = 1
    else:
        new_sequence = last_doc.numero + 1

    return f"{search_pattern}{new_sequence:03d}"

def render_to_pdf(template_src, context_dict={}):
    template = get_template(template_src)
    html  = template.render(context_dict)
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    if not pdf.err:
        return result.getvalue()
    return None

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

# --- A PEÇA QUE FALTA PARA O SOTARQ SCHOOL ---
def get_geo_info(ip_address):
    """
    Rigor SOTARQ: Resolve informações geográficas para auditoria.
    Atualmente em modo placeholder para evitar quebra de sistema.
    """
    # Verificação de IPs internos (Localhost ou rede local)
    internal_ips = ['127.0.0.1', 'localhost', '::1']
    if ip_address in internal_ips or ip_address.startswith('192.168.'):
        return {
            'city': 'Malanje',
            'country': 'AO',
            'region': 'Malanje',
            'status': 'internal'
        }
    
    # Placeholder para IPs externos até integração com MaxMind/GeoIP2
    return {
        'city': 'Luanda',
        'country': 'AO',
        'region': 'Luanda',
        'status': 'placeholder'
    }