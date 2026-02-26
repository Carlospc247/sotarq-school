# apps/fiscal/views.py
from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

from apps.academic.views import is_manager_check
from .models import SAFTExport, FiscalConfig
from .forms import FiscalConfigForm
from django.contrib.admin.views.decorators import staff_member_required
from .models import DocumentoFiscal
from django.db.models import F
from django.conf import settings
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import SAFTExport
from .tasks import task_generate_xml
from django.utils import timezone
from apps.core.utils import render_to_pdf # Usando o utilitário que corrigimos antes
from .models import DocumentoCanceladoAudit
from django.db import transaction





@login_required
def saft_list(request):
    """Lista todos os SAFTs gerados para a escola baixar"""
    safts = SAFTExport.objects.all().order_by('-created_at')
    config, _ = FiscalConfig.objects.get_or_create(id=1)
    
    return render(request, 'fiscal/saft_list.html', {
        'safts': safts,
        'config': config
    })

@login_required
def download_saft(request, pk):
    saft = get_object_or_404(SAFTExport, pk=pk)
    if saft.arquivo:
        response = HttpResponse(saft.arquivo, content_type='application/xml')
        response['Content-Disposition'] = f'attachment; filename="{saft.nome_arquivo}"'
        return response
    raise Http404("Arquivo não encontrado")

@login_required
def update_config(request):
    """Permite ao Diretor mudar o dia de geração (ex: dia 10 em vez de 15)"""
    config, _ = FiscalConfig.objects.get_or_create(id=1)
    if request.method == 'POST':
        form = FiscalConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            # Log de Auditoria aqui seria ideal
            return redirect('fiscal:saft_list')
    return redirect('fiscal:saft_list')



@login_required
@user_passes_test(lambda u: u.is_staff)
def fiscal_audit_log(request):
    """
    PAINEL DE CONTROLO FISCAL: Integridade RSA + Monitorização AGT Webservice.
    """
    query = request.GET.get('q', '')
    # Busca os últimos 50 documentos para auditoria em tempo real
    documentos = DocumentoFiscal.objects.filter(status='confirmed').order_by('-created_at')[:50]

    if query:
        documentos = documentos.filter(Q(numero_documento__icontains=query) | Q(entidade_nome__icontains=query))

    # Lógica de Cadeia de Custódia (Blockchain-like)
    integrity_status = True
    for i in range(len(documentos) - 1):
        # Rigor: O hash_anterior do documento N deve ser identico ao hash_documento do N+1 (sequencial)
        if documentos[i].hash_anterior and documentos[i].hash_anterior != documentos[i+1].hash_documento:
            integrity_status = False
            break

    context = {
        'documentos': documentos,
        'integrity_status': integrity_status,
        'stats': {
            'total': DocumentoFiscal.objects.count(),
            'validados': DocumentoFiscal.objects.filter(agt_status='VALID').count(),
            'rejeitados': DocumentoFiscal.objects.filter(agt_status='ERROR').count(),
            'pendentes': DocumentoFiscal.objects.filter(agt_status='PENDING').count(),
        },
        'software_version': settings.AGT_SOFTWARE_VERSION,
        'certificate': settings.AGT_CERTIFICATE_NUMBER,
    }
    return render(request, 'fiscal/audit_log.html', context)



@login_required
@user_passes_test(is_manager_check)
def saft_generate_trigger(request):
    """
    Gatilho de Exportação Mensal SOTARQ.
    Cria o registro de exportação e enfileira a geração do XML.
    """
    # Definimos o período como o mês anterior (padrão de submissão da AGT)
    hoje = timezone.now()
    primeiro_dia_mes = hoje.replace(day=1)
    ultimo_dia_mes_passado = primeiro_dia_mes - timezone.timedelta(days=1)
    periodo = ultimo_dia_mes_passado.strftime("%Y-%m")
    
    # Evita duplicidade para o mesmo período
    if SAFTExport.objects.filter(periodo_tributacao=periodo, status='generated').exists():
        messages.warning(request, f"O SAF-T de {periodo} já foi gerado e está disponível para download.")
        return redirect('fiscal:saft_list')

    # Cria o registro inicial
    saft_record = SAFTExport.objects.create(
        periodo_tributacao=periodo,
        nome_arquivo=f"SAFT_AO_{request.tenant.schema_name}_{periodo}.xml",
        status='pending'
    )

    # Dispara a Task (Passando o ID e o Schema para o Celery)
    task_generate_xml.delay(saft_record.id, request.tenant.schema_name)

    messages.success(request, f"Processamento iniciado para o período {periodo}. Atualize a página em instantes.")
    return redirect('fiscal:saft_list')


@login_required
def imprimir_documento_fiscal(request, doc_id):
    """
    Motor de Impressão Fiscal SOTARQ.
    Gera o PDF oficial com Hash SHA1 e menção de Software Certificado.
    """
    # Rigor de Tenant: Garante que apenas a escola dona do documento pode imprimir
    documento = get_object_or_404(
        DocumentoFiscal.objects.select_related('cliente', 'usuario_criacao'), 
        id=doc_id
    )
    
    # Busca as linhas (itens) da fatura
    linhas = documento.linhas.all()
    
    # 4 caracteres do Hash (Exigência legal para rodapé)
    hash_control = documento.hash_documento[:4] if documento.hash_documento else "****"

    context = {
        'doc': documento,
        'linhas': linhas,
        'hash_control': hash_control,
        'school': request.tenant,
        'software_version': settings.AGT_SOFTWARE_VERSION,
        'cert_number': settings.AGT_CERTIFICATE_NUMBER,
    }

    # Gera o binário do PDF
    pdf = render_to_pdf('fiscal/pdf/fatura_template.html', context)
    
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        filename = f"{documento.numero_documento}.pdf".replace("/", "_")
        response['Content-Disposition'] = f'inline; filename="{filename}"'
        return response
    
    messages.error(request, "Erro ao gerar o PDF do documento.")
    return redirect('fiscal:fiscal_audit_log')




@login_required
@user_passes_test(is_manager_check)
def anular_documento_fiscal(request, doc_id):
    """
    Rigor SOTARQ: Motor de Anulação Certificada.
    Garante que cada anulação tenha uma justificativa legal e rastro de IP.
    """
    documento = get_object_or_404(DocumentoFiscal, id=doc_id, status='confirmed')

    if request.method == 'POST':
        motivo = request.POST.get('justificativa')
        if not motivo or len(motivo) < 10:
            messages.error(request, "Justificativa obrigatória (mínimo 10 caracteres).")
            return redirect(request.path)

        try:
            with transaction.atomic():
                # 1. Cria o rastro de auditoria forense
                DocumentoCanceladoAudit.objects.create(
                    documento=documento,
                    operador=request.user,
                    justificativa=motivo,
                    ip_address=request.META.get('REMOTE_ADDR'),
                    user_agent=request.META.get('HTTP_USER_AGENT', 'Desconhecido'),
                    valor_estornado=documento.valor_total
                )

                # 2. Altera o status do documento (Invalida para o SAF-T)
                documento.status = DocumentoFiscal.Status.CANCELLED
                documento.save()

                messages.success(request, f"Documento {documento.numero_documento} anulado com sucesso.")
        except Exception as e:
            messages.error(request, f"Erro crítico na anulação: {str(e)}")
        
        return redirect('fiscal:fiscal_audit_log')

    return render(request, 'fiscal/confirm_cancel.html', {'doc': documento})

