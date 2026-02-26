from django.contrib import admin
from django.http import HttpResponse
from django.urls import path
from django.utils.html import format_html
from django.contrib import messages
from .models import SAFTExport, DocumentoFiscal, AssinaturaDigital

# ==========================================================
# 1. Admin de Chaves Digitais (Onde baixamos as chaves)
# ==========================================================
@admin.register(AssinaturaDigital)
class AssinaturaDigitalAdmin(admin.ModelAdmin):
    list_display = ('descricao', 'ativa', 'created_at', 'acoes_download')
    readonly_fields = ('chave_publica_pem', 'created_at')
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/download-txt/', self.download_txt_view, name='fiscal_download_txt'),
            path('<int:object_id>/download-pdf/', self.download_pdf_view, name='fiscal_download_pdf'),
        ]
        return custom_urls + urls

    # Botões na listagem
    def acoes_download(self, obj):
        return format_html(
            '<a class="button" href="{}">TXT (AGT)</a>&nbsp;'
            '<a class="button" href="{}" style="background-color:#ba2121">PDF (Doc)</a>',
            f"{obj.id}/download-txt/",
            f"{obj.id}/download-pdf/"
        )
    acoes_download.short_description = "Baixar Chave Pública"

    # View: Download TXT
    def download_txt_view(self, request, object_id):
        obj = self.get_object(request, object_id)
        response = HttpResponse(obj.chave_publica_pem, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="Chave_Publica_AGT_{object_id}.txt"'
        return response

    # View: Download PDF
    def download_pdf_view(self, request, object_id):
        try:
            from reportlab.pdfgen import canvas
            from reportlab.lib.pagesizes import A4
            from reportlab.lib import colors
        except ImportError:
            self.message_user(request, "Biblioteca 'reportlab' não instalada.", level=messages.ERROR)
            return HttpResponse("Erro: Reportlab não instalado")

        obj = self.get_object(request, object_id)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Chave_Publica_{object_id}.pdf"'

        p = canvas.Canvas(response, pagesize=A4)
        p.setTitle(f"Chave Pública - {obj.descricao}")
        
        # Cabeçalho
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 800, "Certificação de Software - Chave Pública")
        p.setFont("Helvetica", 10)
        p.drawString(50, 780, f"Gerado em: {obj.data_geracao}")
        p.drawString(50, 765, "Entregue este documento ou o conteúdo abaixo à AGT.")
        
        # Caixa de Código
        p.setStrokeColor(colors.black)
        p.rect(40, 300, 520, 450, fill=0)
        
        # Imprimir a chave (quebrar linhas)
        text = p.beginText(50, 730)
        text.setFont("Courier", 9)
        for line in obj.chave_publica_pem.split('\n'):
            text.textLine(line)
        p.drawText(text)
        
        p.showPage()
        p.save()
        return response

    # Ação: Gerar Chaves Automaticamente
    actions = ['gerar_chaves_action']
    
    @admin.action(description='🔐 Gerar/Regenerar Par de Chaves RSA para selecionados')
    def gerar_chaves_action(self, request, queryset):
        for assinatura in queryset:
            assinatura.gerar_novas_chaves()
        self.message_user(request, "Novas chaves geradas e guardadas no banco de dados com sucesso.")

# ==========================================================
# 2. Admin de Exportações SAFT (Existente)
# ==========================================================
@admin.register(SAFTExport)
class SAFTExportAdmin(admin.ModelAdmin):
    list_display = ('periodo_tributacao', 'status', 'created_at', 'download_link')
    list_filter = ('status', 'periodo_tributacao')
    
    def download_link(self, obj):
        if obj.arquivo:
            return format_html('<a href="{}" download>Baixar XML</a>', obj.arquivo.url)
        return "Indisponível"
    download_link.short_description = "Arquivo"

# ==========================================================
# 3. Admin de Documentos Fiscais (Existente + Melhorado)
# ==========================================================
@admin.register(DocumentoFiscal)
class DocumentoFiscalAdmin(admin.ModelAdmin):
    list_display = ('numero_documento', 'tipo_documento', 'data_emissao', 'valor_total', 'status_icon')
    search_fields = ('numero_documento', 'atcud', 'entidade_nome')
    list_filter = ('tipo_documento', 'status', 'data_emissao')
    readonly_fields = ('hash_documento', 'hash_anterior', 'atcud')
    
    def status_icon(self, obj):
        if obj.status == 'confirmed':
            return "✅ Confirmado"
        elif obj.status == 'cancelled':
            return "❌ Anulado"
        return "📝 Rascunho"
    status_icon.short_description = "Estado"

    def has_change_permission(self, request, obj=None):
        return False
    
    def has_add_permission(self, request):
        return False