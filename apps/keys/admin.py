from django.contrib import admin
from django.utils.html import format_html
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.contrib import messages
from .models import CentralKeyVault
from apps.core.admin_mixins import SaaSOnlyAdminMixin

# Imports para PDF
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors

@admin.register(CentralKeyVault)
class CentralKeyVaultAdmin(SaaSOnlyAdminMixin, admin.ModelAdmin):
    list_display = ('get_tenant_name', 'data_geracao', 'status_seguranca', 'painel_de_acoes')
    readonly_fields = ('data_geracao', 'ver_chave_publica', 'ver_chave_privada')
    search_fields = ('tenant__name', 'tenant__schema_name')
    actions = ['gerar_chaves_em_massa']

    # --- Customização da Lista ---
    def get_tenant_name(self, obj):
        return f"{obj.tenant.name} ({obj.tenant.schema_name})"
    get_tenant_name.short_description = "Escola / Tenant"

    def status_seguranca(self, obj):
        if obj.chave_privada_pem and obj.chave_publica_pem:
            return format_html('<span style="color: green; font-weight:bold;">✔ ATIVO</span>')
        return format_html('<span style="color: red; font-weight:bold;">✘ PENDENTE</span>')
    status_seguranca.short_description = "Status"

    # --- O Painel de Controle Inteligente ---
    def painel_de_acoes(self, obj):
        # CASO 1: NÃO TEM CHAVES -> MOSTRA BOTÃO DE GERAR
        if not obj.chave_publica_pem:
            url_gerar = reverse('admin:keys_gerar_unica', args=[obj.id])
            return format_html(
                f'<a class="button" href="{url_gerar}" style="background-color:#2563EB; color:white; font-weight:bold; padding:5px 10px; border-radius:4px;">⚙️ GERAR AGORA</a>'
            )
        
        # CASO 2: JÁ TEM CHAVES -> MOSTRA FERRAMENTAS
        url_pdf = reverse('admin:keys_download_cert', args=[obj.id])
        url_txt = reverse('admin:keys_download_txt', args=[obj.id])

        # Tratamento de strings para o JavaScript
        pub_key_safe = obj.chave_publica_pem.replace('\n', '\\n').replace('\r', '')
        priv_key_safe = obj.chave_privada_pem.replace('\n', '\\n').replace('\r', '')

        html = f"""
        <div style="display: flex; gap: 5px;">
            <button type="button" 
                onclick="navigator.clipboard.writeText('{pub_key_safe}').then(() => alert('✅ Chave PÚBLICA copiada!'));" 
                style="cursor:pointer; background:#e0e7ff; border:1px solid #4f46e5; color:#4f46e5; font-weight:bold; padding:4px 8px; border-radius:4px;" 
                title="Copiar Chave Pública">
                🔑 PUB
            </button>

            <button type="button" 
                onclick="navigator.clipboard.writeText('{priv_key_safe}').then(() => alert('⚠️ Chave PRIVADA copiada! Mantenha em segredo.'));" 
                style="cursor:pointer; background:#fee2e2; border:1px solid #dc2626; color:#dc2626; font-weight:bold; padding:4px 8px; border-radius:4px;" 
                title="Copiar Chave Privada">
                🔒 PRIV
            </button>

            <a href="{url_pdf}" target="_blank" style="background:#10b981; color:white; padding:4px 8px; text-decoration:none; border-radius:4px; display:flex; align-items:center;" title="Baixar Certificado AGT">
                📄 PDF
            </a>
            <a href="{url_txt}" target="_blank" style="background:#6b7280; color:white; padding:4px 8px; text-decoration:none; border-radius:4px; display:flex; align-items:center;" title="Baixar TXT">
                📝 TXT
            </a>
        </div>
        """
        return format_html(html)
    painel_de_acoes.short_description = "Ações Rápidas"

    # --- Configuração de URLs e Views ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:object_id>/gerar-unica/', self.view_gerar_unica, name='keys_gerar_unica'), # NOVA ROTA
            path('<int:object_id>/download-cert-agt/', self.download_cert_agt, name='keys_download_cert'),
            path('<int:object_id>/download-txt/', self.download_txt, name='keys_download_txt'),
        ]
        return custom_urls + urls

    # --- Nova View para Gerar Chave Individualmente ---
    def view_gerar_unica(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj:
            obj.gerar_par_rsa()
            self.message_user(request, f"✅ Chaves RSA geradas com sucesso para {obj.tenant.name}!", level=messages.SUCCESS)
        return HttpResponseRedirect("../") # Volta para a lista

    # --- Detalhes (Readonly) ---
    def ver_chave_publica(self, obj):
        return format_html(f'<textarea rows="10" cols="80" readonly>{obj.chave_publica_pem}</textarea>')
    
    def ver_chave_privada(self, obj):
        return format_html(f'<textarea rows="10" cols="80" readonly>{obj.chave_privada_pem}</textarea>')

    # --- Ações em Massa (Dropdown) ---
    @admin.action(description='🔐 Gerar Par de Chaves RSA para selecionados')
    def gerar_chaves_em_massa(self, request, queryset):
        count = 0
        for vault in queryset:
            vault.gerar_par_rsa()
            count += 1
        self.message_user(request, f"{count} pares de chaves gerados com sucesso.")

    # --- Downloads (PDF e TXT) ---
    def download_txt(self, request, object_id):
        obj = self.get_object(request, object_id)
        if not obj: return HttpResponse("Erro", status=404)
        content = f"=== SOTARQ SCHOOL ===\nTenant: {obj.tenant.name}\n\n[PUB]\n{obj.chave_publica_pem}\n\n[PRIV]\n{obj.chave_privada_pem}"
        response = HttpResponse(content, content_type='text/plain')
        response['Content-Disposition'] = f'attachment; filename="Keys_{obj.tenant.schema_name}.txt"'
        return response

    def download_cert_agt(self, request, object_id):
        # (Mantém o mesmo código do PDF que te passei antes, está perfeito)
        obj = self.get_object(request, object_id)
        if not obj: return HttpResponse("Erro", status=404)
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Certificado_{obj.tenant.schema_name}.pdf"'
        p = canvas.Canvas(response, pagesize=A4)
        # ... (Copia o conteúdo da função download_cert_agt anterior) ...
        p.drawString(100, 700, f"Certificado de Chave Pública: {obj.tenant.name}")
        p.drawString(100, 680, "Verificado por Sotarq SaaS")
        p.showPage()
        p.save()
        return response