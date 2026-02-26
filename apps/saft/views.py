import xml.etree.ElementTree as ET
from django.shortcuts import render
from django.conf import settings
from django.http import HttpResponse
from django.contrib.auth.decorators import user_passes_test
from django.utils import timezone

from .generator import SAFTBuilder
from .models import SAFTSettings
from apps.finance.models import Invoice

@user_passes_test(lambda u: u.is_staff)
def export_saft_xml(request):
    """
    Gera e exporta o ficheiro SAFT-AO mensal conforme norma 1.01_01.
    Apenas staff autorizado pode gerar este ficheiro para submissão à AGT.
    """
    # 1. Filtro por período (Default: mês/ano atual)
    month = request.GET.get('month', timezone.now().month)
    year = request.GET.get('year', timezone.now().year)
    
    invoices = Invoice.objects.filter(
        issue_date__month=month,
        issue_date__year=year,
        status='confirmed'
    ).select_related('student').prefetch_related('items')

    # 2. Inicializar o Builder (Lógica de montagem do XML)
    builder = SAFTBuilder(tenant=request.tenant)
    
    # 3. Construir as secções obrigatórias do AuditFile
    builder.build_header(year, month) 
    builder.build_master_files()
    builder.build_sales_invoices(invoices)
    
    # 4. Gerar o binário do XML com encoding UTF-8
    xml_data = ET.tostring(builder.root, encoding='UTF-8', xml_declaration=True)
    
    # 5. Resposta HTTP para download forçado
    filename = f"SAFT_AO_{request.tenant.schema_name}_{year}_{month}.xml"
    response = HttpResponse(xml_data, content_type='application/xml')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response

@user_passes_test(lambda u: u.is_staff)
def saft_audit_dashboard(request):
    """
    Painel de Conformidade Fiscal.
    Permite ao staff monitorizar a saúde do faturamento sem expor chaves privadas.
    """
    # Buscamos as configurações de certificação (Versão do Software e Nº de Certificado)
    fiscal_settings = SAFTSettings.objects.first()
    
    # Lista faturas recentes para conferência de Hash (Apenas rasto técnico)
    recent_invoices = Invoice.objects.filter(
        status='confirmed'
    ).order_by('-created_at')[:20]
    
    return render(request, 'saft/audit_dashboard.html', {
        'settings': fiscal_settings,
        'recent_invoices': recent_invoices
    })
