# apps/fiscal/views.py
import random
import string

from django.http import HttpResponse, Http404
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test

from apps.academic.views import is_manager_check
from .models import AssinaturaDigital, DocType, SAFTExport, FiscalConfig, SerieFiscal, TaxaIVAAGT
from .forms import FiscalConfigForm, TaxaIVAAGTForm
from django.contrib.admin.views.decorators import staff_member_required
from .models import DocumentoFiscal
from django.db.models import F
from django.conf import settings
from django.db import IntegrityError
from django.db.models import Q
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import SAFTExport
from .tasks import task_generate_xml
from django.utils import timezone
from apps.core.utils import render_to_pdf
from .models import DocumentoCanceladoAudit
from django.db import transaction
from django.core.exceptions import PermissionDenied



def admin_role_required(view_func):
    """
    RIGOR SOTARQ: Garante acesso apenas ao ADMIN da Escola (Role.Type.ADMIN).
    Também permite Superusers para evitar bloqueios em ambiente de desenvolvimento.
    """
    def _wrapped_view(request, *args, **kwargs):
        # 1. Bypass para Superuser (O seu usuário master sempre entra)
        if request.user.is_superuser:
            return view_func(request, *args, **kwargs)
        
        # 2. Verificação de Role Dinâmica do Tenant
        # Tentamos acessar request.user.role.code de forma segura
        role = getattr(request.user, 'role', None)
        
        if role and hasattr(role, 'code'):
            # Compara com o TextChoices da sua classe Role
            from apps.core.models import Role # Certifique-se de importar corretamente
            if role.code == Role.Type.ADMIN:
                return view_func(request, *args, **kwargs)
        
        # 3. Log de Auditoria para Segurança
        logger.warning(
            f"[SECURITY_ALERT] Tentativa de acesso negada à área Fiscal. "
            f"User: {request.user.email} | Role: {role.code if role else 'N/A'} | "
            f"Tenant: {request.tenant.schema_name}"
        )
        
        raise PermissionDenied("Apenas o Administrador da Escola pode gerir Séries e ATCUD.")
    
    return _wrapped_view


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
#@user_passes_test(lambda u: u.is_staff) só para is_staff=True
@user_passes_test(is_manager_check)
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


import os
import logging
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from .models import SAFTExport

logger = logging.getLogger(__name__)

@login_required
@require_POST
def delete_saft(request, pk):
    """
    Elimina um registo SAF-T com rigor SOTARQ.
    Segurança: O queryset é limitado ao schema atual do Tenant pelo django-tenants.
    """
    # 1. Recupera o objeto ou retorna 404 (Já isolado pelo schema_name do tenant atual)
    saft = get_object_or_404(SAFTExport, pk=pk)
    
    periodo = saft.periodo_tributacao
    nome_arquivo = saft.nome_arquivo

    try:
        # 2. Remoção Física do Ficheiro (Storage)
        # É vital remover do disco para evitar custos desnecessários de armazenamento
        if saft.arquivo:
            if os.path.isfile(saft.arquivo.path):
                os.remove(saft.arquivo.path)
                logger.info(f"Ficheiro físico {nome_arquivo} removido com sucesso.")

        # 3. Remoção do Registo na Base de Dados
        saft.delete()
        
        messages.success(request, f"Registo SAF-T [{periodo}] eliminado com sucesso.")
        logger.info(f"Usuário {request.user.id} eliminou o registo SAF-T {pk} do tenant {request.tenant.schema_name}")

    except Exception as e:
        messages.error(request, f"Erro ao eliminar o registo: {str(e)}")
        logger.error(f"Falha crítica na exclusão do SAF-T {pk}: {str(e)}")

    return redirect('fiscal:saft_index') # Ou o nome da sua view principal de listagem


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

##############################################
# WEBSERVICE
##############################################
from django.http import JsonResponse
from .services import AGTWebService, gerar_chaves_rsa_tenant

def api_agt_status(request):
    """Endpoint chamado pelo AJAX no Dashboard."""
    service = AGTWebService()
    return JsonResponse({'online': service.check_status()})



@login_required
@user_passes_test(is_manager_check)
def taxa_iva_list(request):
    """Lista as taxas configuradas no sistema"""
    taxas = TaxaIVAAGT.objects.all().order_by('-ativo', 'tax_percentage')
    return render(request, 'fiscal/taxa_iva_list.html', {'taxas': taxas})


@login_required
@user_passes_test(is_manager_check)
def taxa_iva_create(request):
    if request.method == 'POST':
        form = TaxaIVAAGTForm(request.POST)
        if form.is_valid():
            taxa = form.save()
            messages.success(request, f"Taxa {taxa.nome} registrada.")
            return redirect('fiscal:taxa_iva_list')
        
        # Se falhar, renderizamos a LISTA novamente com o form inválido
        # Isso ativará o openModal: true no template
        taxas = TaxaIVAAGT.objects.all().order_by('-ativo', 'nome')
        messages.error(request, "Falha na validação fiscal. Verifique os campos.")
        return render(request, 'fiscal/taxa_iva_list.html', {
            'taxas': taxas,
            'form': form
        })
    return redirect('fiscal:taxa_iva_list')


@login_required
@user_passes_test(is_manager_check)
def gestao_chaves_rsa(request):
    """
    PAINEL SOTARQ: Gestão de Identidade Digital da Escola.
    Permite gerar novas chaves e visualizar o status da assinatura.
    """
    # Busca a assinatura ativa para o Tenant atual
    #assinatura = AssinaturaDigital.objects.filter(tenant=request.tenant, ativa=True).first()
    assinatura = AssinaturaDigital.objects.filter(ativa=True).first()
    
    # Histórico de chaves (Auditoria)
    #historico = AssinaturaDigital.objects.filter(tenant=request.tenant).order_by('-created_at')
    historico = AssinaturaDigital.objects.filter().order_by('-created_at')

    return render(request, 'fiscal/gestao_chaves.html', {
        'assinatura': assinatura,
        'historico': historico,
    })

"""
@login_required
@user_passes_test(is_manager_check)
def gerar_nova_chave_action(request):
    
    #Gatilho para gerar par RSA 1024-bit.
   
    if request.method == "POST":
        try:
            # Chama o serviço que criamos anteriormente
            nova_chave = gerar_chaves_rsa_tenant(request.tenant)
            messages.success(request, f"Nova Chave RSA gerada com sucesso em {nova_chave.created_at.strftime('%d/%m/%Y %H:%M')}.")
        except Exception as e:
            messages.error(request, f"Erro crítico ao gerar chaves: {str(e)}")
    
    return redirect('fiscal:gestao_chaves_rsa')

"""





"""
@login_required
@user_passes_test(is_manager_check)
def baixar_chave_publica(request, pk):

    #Exporta a chave pública em formato .pem para entrega à AGT/Auditoria.
    
    assinatura = get_object_or_404(AssinaturaDigital, pk=pk, tenant=request.tenant)
    
    conteudo = assinatura.chave_publica_pem
    filename = f"PUBLIC_KEY_{request.tenant.nif}_{assinatura.created_at.strftime('%Y%m%d')}.pem"
    
    response = HttpResponse(conteudo, content_type='application/x-pem-file')
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    # Rigor: Registrar no log quem baixou a chave
    logger.info(f"Chave pública baixada pelo usuário {request.user} para o tenant {request.tenant.schema_name}")
    
    return response

"""



@login_required
@admin_role_required # Segurança Máxima SOTARQ
def gerar_nova_chave_action(request):
    """
    Gatilho para gerar par RSA 1024-bit seguindo o rigor do schema atual.
    """
    if request.method == "POST":
        try:
            # Não passamos mais o objeto tenant, o schema já está setado no middleware
            nova_chave = gerar_chaves_rsa_tenant()
            messages.success(request, f"Nova Chave RSA gerada com sucesso em {nova_chave.created_at.strftime('%d/%m/%Y %H:%M')}.")
        except Exception as e:
            messages.error(request, f"Erro crítico ao gerar chaves: {str(e)}")
    
    return redirect('fiscal:gestao_chaves_rsa')


@login_required
@user_passes_test(admin_role_required) # Segurança Máxima SOTARQ
def baixar_chave_publica(request, pk):
    """
    Exporta a chave pública em TXT (exigência AGT) ou PEM.
    O isolamento por schema do django-tenants garante a segurança.
    """
    assinatura = get_object_or_404(AssinaturaDigital, pk=pk)
    
    # Determina o formato (padrão txt conforme solicitado)
    formato = request.GET.get('format', 'txt').lower()
    conteudo = assinatura.chave_publica_pem
    
    if formato == 'pem':
        content_type = 'application/x-pem-file'
        extension = 'pem'
    else:
        content_type = 'text/plain'
        extension = 'txt'

    # Nome do arquivo usando o schema_name do tenant atual
    filename = f"CHAVE_PUBLICA_{request.tenant.schema_name.upper()}_{assinatura.created_at.strftime('%Y%m%d')}.{extension}"
    
    response = HttpResponse(conteudo, content_type=content_type)
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    logger.info(f"Chave pública exportada em .{extension} por {request.user} no schema {request.tenant.schema_name}")
    
    return response


@login_required
@user_passes_test(admin_role_required)
def gestao_series_fiscal(request):
    """
    Interface Unificada SOTARQ para Séries Fiscais.
    """
    # Filtro de Tenant obrigatório para evitar 404 e vazamento de dados
    series = SerieFiscal.objects.order_by('-ano', 'tipo_documento')
    
    if request.method == "POST":
        # Captura o ID da série vindo do Modal ou do Form
        serie_id = request.POST.get("serie_id")
        
        # Blindagem contra NoneType (o erro do strip que resolvemos)
        novo_codigo = request.POST.get("codigo_agt", "").strip().upper()
        
        if not serie_id:
            messages.error(request, "ERRO: ID da série não identificado.")
            return redirect('fiscal:gestao_series')

        # O Rigor exige buscar a série DENTRO do tenant atual
        serie = get_object_or_404(SerieFiscal, id=serie_id)
        
        serie.codigo_validacao_agt = novo_codigo
        serie.status = 'ATIVA' if novo_codigo else 'PENDING'
        serie.save()
        
        # Sincronização de ATCUD
        docs = DocumentoFiscal.objects.filter(serie=serie, atcud="")
        count = 0
        for doc in docs:
            doc.save() # O save() do model gera o ATCUD
            count += 1
            
        messages.success(request, f"Série {serie.codigo} atualizada! {count} documentos processados.")
        return redirect('fiscal:gestao_series')

    return render(request, 'fiscal/gestao_series.html', {'series': series})



@login_required
@user_passes_test(admin_role_required)
def gerar_series_fiscal(request):
    """
    Controlador Central SOTARQ: Gere, Insira ou Vincule Séries Fiscais.
    """
    ano_atual = timezone.now().year
    series = SerieFiscal.objects.order_by('-ano', 'tipo_documento')

    if request.method == 'POST':
        # --- CASO 1: Inserção Manual (Série fornecida pela AGT) ---
        if 'inserir_manual' in request.POST:
            tipo = request.POST.get('tipo_documento')
            codigo = request.POST.get('codigo_manual', '').strip().upper()
            validacao = request.POST.get('codigo_validacao', '').strip().upper()

            # Validação de Rigor: Já existe este tipo para este ano?
            if SerieFiscal.objects.filter(tipo_documento=tipo, ano=ano_atual).exists():
                messages.error(request, f"VIOLAÇÃO DE REGRAS: Já existe uma série {tipo} para o ano {ano_atual}.")
                return redirect('fiscal:gestao_series')

            try:
                SerieFiscal.objects.create(
                    codigo=codigo,
                    ano=ano_atual,
                    tipo_documento=tipo,
                    codigo_validacao_agt=validacao,
                    status='ATIVA' if validacao else 'PENDING'
                )
                messages.success(request, f"Série manual {codigo} registrada com sucesso.")
            except IntegrityError:
                messages.error(request, "Erro de integridade: Código já existente.")

        # --- CASO 2: Geração Automática (Algoritmo SOTARQ) ---
        elif 'gerar_automatico' in request.POST:
            tipos = [DocType.FT, DocType.FR, DocType.NC, DocType.RC]
            nome_escola = request.tenant.name.replace(" ", "").upper()
            prefixo = (nome_escola[:6] if len(nome_escola) >= 6 else nome_escola.ljust(6, 'X'))
            criadas = 0

            try:
                with transaction.atomic():
                    for tipo in tipos:
                        # Pula se já existir para evitar erro de UniqueConstraint
                        if SerieFiscal.objects.filter(tipo_documento=tipo, ano=ano_atual).exists():
                            continue

                        # Algoritmo de Código: TIPO + 3NUM + ESCOLA + 3CHAR + ANO
                        while True:
                            r_num = ''.join(random.choices(string.digits, k=3))
                            r_char = ''.join(random.choices(string.ascii_uppercase, k=3))
                            novo_codigo = f"{tipo}{r_num}{prefixo}{r_char}{ano_atual}"
                            
                            if not SerieFiscal.objects.filter(codigo=novo_codigo).exists():
                                break

                        SerieFiscal.objects.create(
                            codigo=novo_codigo,
                            ano=ano_atual,
                            tipo_documento=tipo,
                            status='PENDING'
                        )
                        criadas += 1
                
                if criadas > 0:
                    messages.info(request, f"{criadas} séries geradas sob o padrão SOTARQ.")
                else:
                    messages.warning(request, "Nenhuma série nova foi gerada (Já existem séries para todos os tipos este ano).")
            
            except Exception as e:
                messages.error(request, f"Falha na geração atómica: {str(e)}")

        # --- CASO 3: Vincular Código (Via Modal) ---
        elif 'vincular_codigo' in request.POST:
            serie_id = request.POST.get('serie_id')
            codigo_agt = request.POST.get('codigo_agt', '').strip().upper()
            
            serie = get_object_or_404(SerieFiscal, id=serie_id)
            serie.codigo_validacao_agt = codigo_agt
            serie.status = 'ATIVA'
            serie.save()
            messages.success(request, f"Série {serie.codigo} validada com sucesso.")

        return redirect('fiscal:gestao_series')

    return render(request, 'fiscal/gestao_series.html', {
        'series': series,
        'ano_atual': ano_atual,
        'now': timezone.now()
    })




@login_required
@user_passes_test(admin_role_required)
def historico_series_fiscal(request):
    """
    Exibe o histórico completo de séries geradas e seu estado de conformidade.
    """
    # Ordenamos por ano decrescente e depois por tipo
    historico = SerieFiscal.objects.all().order_by('-ano', 'tipo_documento')
    
    # Métricas rápidas para o cabeçalho do relatório
    total_ativas = historico.filter(status='ATIVA').count()
    pendentes = historico.filter(status='PENDING').count()

    context = {
        'historico': historico,
        'total_ativas': total_ativas,
        'pendentes': pendentes,
        'ano_atual': timezone.now().year
    }
    
    return render(request, 'fiscal/historico_series.html', context)
