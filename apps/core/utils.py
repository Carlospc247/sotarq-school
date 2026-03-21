# apps/core/utils.py
import datetime
import logging
from django.db import models
from io import BytesIO
from django.template.loader import get_template
from xhtml2pdf import pisa

logger = logging.getLogger(__name__)


"""
def generate_document_number(instance_or_model, prefix):
    from django.db import connection
    tenant = connection.tenant
    tenant_slug = "".join(filter(str.isalnum, tenant.name)).upper()[:5]
    year = datetime.datetime.now().year
    
    model_class = instance_or_model if isinstance(instance_or_model, type) else instance_or_model.__class__
    search_pattern = f"{prefix} {tenant_slug}{year}/"

    # RIGOR SOTARQ: Detecção dinâmica do campo de numeração
    target_field = 'numero_documento' if hasattr(model_class, 'numero_documento') else 'number'
    
    filter_kwargs = {f"{target_field}__startswith": search_pattern}
    last_doc = model_class.objects.filter(**filter_kwargs).order_by('id').last()

    if not last_doc:
        new_sequence = 1
    else:
        # Extração segura da sequência numérica final
        try:
            val = getattr(last_doc, target_field)
            new_sequence = int(val.split('/')[-1]) + 1
        except (ValueError, IndexError):
            new_sequence = model_class.objects.count() + 1

    return f"{search_pattern}{new_sequence:03d}"

"""

def generate_document_number(instance_or_model, prefix):
    import datetime
    from django.db import connection
    
    tenant = connection.tenant
    # Limpeza: apenas caracteres alfanuméricos em maiúsculas
    raw_name = "".join(filter(str.isalnum, tenant.name)).upper()
    
    # NOVA LÓGICA DE UNICIDADE SOTARQ:
    # 2 primeiras + 3 últimas + 2 do centro (total 7 caracteres)
    if len(raw_name) >= 7:
        mid = len(raw_name) // 2
        tenant_slug = raw_name[:2] + raw_name[-3:] + raw_name[mid-1:mid+1]
    else:
        # Fallback caso o nome seja muito curto
        tenant_slug = raw_name.ljust(7, 'X')

    year = datetime.datetime.now().year
    
    model_class = instance_or_model if isinstance(instance_or_model, type) else instance_or_model.__class__
    search_pattern = f"{prefix} {tenant_slug}{year}/"

    # RIGOR SOTARQ: Detecção dinâmica do campo de numeração
    target_field = 'numero_documento' if hasattr(model_class, 'numero_documento') else 'number'
    
    filter_kwargs = {f"{target_field}__startswith": search_pattern}
    last_doc = model_class.objects.filter(**filter_kwargs).order_by('id').last()

    if not last_doc:
        new_sequence = 1
    else:
        # Extração segura da sequência numérica final
        try:
            val = getattr(last_doc, target_field)
            new_sequence = int(val.split('/')[-1]) + 1
        except (ValueError, IndexError):
            new_sequence = model_class.objects.count() + 1

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