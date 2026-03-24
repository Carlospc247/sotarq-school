# apps/finance/utils/pdf_generators.py
import os
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

import qrcode
from urllib.parse import quote
from PIL import Image
from apps.fiscal.signing import FiscalSigner
from apps.core.utils import generate_document_number
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle


import os
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image
from urllib.parse import quote

from apps.finance.models import BankAccount, Invoice
from apps.fiscal.signing import FiscalSigner
from apps.core.utils import generate_document_number

import os
from io import BytesIO
from django.core.files.base import ContentFile
from django.conf import settings
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
import qrcode
from PIL import Image
from urllib.parse import quote

from apps.finance.models import BankAccount
from apps.fiscal.signing import FiscalSigner
from apps.core.utils import generate_document_number

import os
from django.conf import settings
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from reportlab.lib.utils import ImageReader
from io import BytesIO

# Import dos models necessários
from apps.finance.models import BankAccount
from apps.customers.models import Client



"""
def generate_agt_qrcode_image(instance):

    tenant = instance.student.user.tenant if hasattr(instance, 'student') else instance.invoice.student.user.tenant
    doc_number = instance.number if hasattr(instance, 'number') else instance.reference
    
    # URL de Consulta Pública AGT
    encoded_doc = quote(doc_number)
    url = f"https://quiosqueagt.minfin.gov.ao/facturacao-eletronica/consultar?emissor={tenant.nif}&documento={encoded_doc}"
    
    qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    
    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # Inserir Logo AGT centralizado para autoridade visual
    #from django.contrib.staticfiles import finders

    #logo_path = finders.find('img/logo_agt.png')
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'logo_agt.png')
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        qr_w, qr_h = img_qr.size
        logo_size = int(qr_w * 0.20)
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
        img_qr.paste(logo, pos)
        
    return img_qr

"""

import os
from PIL import Image
import qrcode
from django.conf import settings
from urllib.parse import quote
"""
def generate_agt_qrcode_image(instance):
    
    tenant = instance.student.user.tenant if hasattr(instance, 'student') else instance.invoice.student.user.tenant
    doc_number = instance.number if hasattr(instance, 'number') else instance.reference
    
    # URL de Consulta Pública AGT (Substituição de espaços por %20 via quote)
    encoded_doc = quote(doc_number)
    nif_emissor = tenant.nif
    url = f"https://quiosqueagt.minfin.gov.ao/facturacao-eletronica/consultar?emissor={nif_emissor}&documento={encoded_doc}"
    
    # Rigor Técnico: Versão 4, Erro M, Border reduzido para ganhar espaço
    qr = qrcode.QRCode(
        version=4, 
        error_correction=qrcode.constants.ERROR_CORRECT_M, 
        box_size=10, 
        border=0  # Reduzido de 4 para 2 para diminuir a borda branca excessiva
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Gerar imagem base e converter para RGBA para suportar transparência do logo
    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    
    # Redimensionamento forçado para o padrão AGT (350x350 px)
    img_qr = img_qr.resize((350, 350), Image.LANCZOS)
    
    # Caminho do Logo
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'logo_agt.png')
    
    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        
        qr_w, qr_h = img_qr.size
        
        # Norma AGT: Logo deve ocupar MENOS de 20%. Usaremos 18% para segurança técnica.
        logo_size = int(qr_w * 0.18) 
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        
        # Cálculo de centralização
        pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
        
        # Colagem usando o próprio logo como máscara (preserva transparência do PNG)
        img_qr.paste(logo, pos, mask=logo)
        
    return img_qr.convert('RGB') # Retorna em RGB para compatibilidade com ReportLab

"""
import os
import qrcode
from PIL import Image
from django.conf import settings
from urllib.parse import quote




def generate_agt_qrcode_image(instance):
    """
    Gera o QR Code AGT v4 rigorosamente conforme Norma Técnica.
    Focado em: 350x350px, Versão 4, Erro M, Logo Centralizado.
    """
    # 1. Obtenção do Tenant/Escola (Mantendo sua lógica de busca)
    try:
        if hasattr(instance, 'student'):
            tenant = instance.student.user.tenant
        elif hasattr(instance, 'invoice') and hasattr(instance.invoice, 'student'):
            tenant = instance.invoice.student.user.tenant
        else:
            tenant = getattr(instance, 'tenant', None)
    except AttributeError:
        tenant = None

    nif_emissor = tenant.nif if tenant else "000000000"
    doc_number = getattr(instance, 'number', getattr(instance, 'reference', 'S/N'))
    
    # 2. URL de Consulta Pública (Escaping de espaços conforme AGT)
    encoded_doc = quote(doc_number)
    url = f"https://quiosqueagt.minfin.gov.ao/facturacao-eletronica/consultar?emissor={nif_emissor}&documento={encoded_doc}"
    
    # 3. Geração do QR Code Base
    qr = qrcode.QRCode(
        version=4, 
        error_correction=qrcode.constants.ERROR_CORRECT_M, 
        box_size=10, 
        border=2 # Borda mínima para não "colar" nos elementos do PDF
    )
    qr.add_data(url)
    qr.make(fit=True)
    
    # Converter para RGBA para manipulação de camadas
    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGBA')
    img_qr = img_qr.resize((350, 350), Image.LANCZOS)
    
    # 4. Inserção do Logo com Verificação de Caminho Dupla
    # Tentamos STATIC_ROOT e, se falhar (em dev), tentamos o caminho manual
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'logo_agt.png')
    
    # Se o arquivo não existe, o logo não aparece. Vamos garantir que o Python o encontre.
    if not os.path.exists(logo_path):
        # Fallback para pastas de desenvolvimento se necessário
        logo_path = os.path.join(settings.BASE_DIR, 'static', 'img', 'logo_agt.png')

    if os.path.exists(logo_path):
        logo = Image.open(logo_path).convert("RGBA")
        
        qr_w, qr_h = img_qr.size
        
        # AGT: < 20%. 18% é o "ponto doce" para leitura.
        logo_size = int(qr_w * 0.20) 
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        
        # Centralização exata
        pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
        
        # CRIAR UM FUNDO BRANCO PARA O LOGO (Isso garante que ele apareça sobre os módulos pretos)
        # Se o logo for transparente, os pontos do QR Code passam por "dentro" dele e dificultam a leitura
        logo_bg = Image.new('RGBA', (logo_size, logo_size), (255, 255, 255, 255))
        img_qr.paste(logo_bg, pos, mask=logo_bg) # Coloca um quadrado branco por baixo
        img_qr.paste(logo, pos, mask=logo)       # Coloca o logo por cima
        
    return img_qr.convert('RGB')



class SOTARQExporter:
    """
    Motor Supremo v5.0 - Production Ready.
    Design System: Indigo + Orange + AGT Compliance
    """

    @staticmethod
    def _get_tenant_colors(tenant=None):
        """Retorna paleta fixa (Ignora cores do tenant)."""
        return {
            'primary': colors.HexColor("#4338ca"),       # Indigo-700
            'secondary': colors.HexColor("#f97316"),     # Orange-500
            'primary_dark': colors.HexColor("#3730a3"),  # Indigo-800
            'secondary_dark': colors.HexColor("#ea580c"),# Orange-600
            'black': colors.HexColor("#000000"),
            'white': colors.HexColor("#ffffff"),
            'gray_50': colors.HexColor("#f9fafb"),
            'gray_100': colors.HexColor("#f3f4f6"),
            'gray_200': colors.HexColor("#e5e7eb"),
            'gray_400': colors.HexColor("#9ca3af"),
            'gray_600': colors.HexColor("#4b5563"),
            'gray_800': colors.HexColor("#1f2937"),
            'success': colors.HexColor("#10b981"),
            'danger': colors.HexColor("#ef4444"),
        }
    
    
    @staticmethod
    def _get_agt_footer_text():
        """Retorna texto do rodapé AGT baseado no .env"""
        software_id = getattr(settings, 'AGT_ID_SISTEMA', 'SOTARQ-SCHOOL')
        cert_number = getattr(settings, 'AGT_CERTIFICATE_NUMBER', '000/AGT/2026')
        return f"{software_id} - Processado por Programa validado número {cert_number}"

    @staticmethod
    def _get_bank_info(tenant):
        """Retorna informações bancárias ativas do tenant."""
        try:
            # Busca a primeira conta bancária ativa
            account = BankAccount.objects.filter(is_active=True).first()
            if account:
                # AJUSTADO: Usando account_number em vez de account_holder
                #return f"Banco: {account.bank_name} | Conta: {account.account_number} | IBAN: {account.iban}"
                return f"{account.bank_name} | {account.account_number} | {account.iban}"
        except Exception:
            pass
        return "Dados bancários não configurados"

    @staticmethod
    def _get_tenant_logo(tenant):
        """Retorna path do logo ou None."""
        if tenant and hasattr(tenant, 'logo') and tenant.logo:
            try:
                return tenant.logo.path
            except Exception:
                pass
        return None

    @staticmethod
    def _get_tenant_contact_info(tenant):
        """Retorna informações de contato do tenant."""
        info = {
            'address': getattr(tenant, 'address', 'Endereço não configurado'),
            'phone': getattr(tenant, 'phone', 'N/A'),
            'email': getattr(tenant, 'email', 'N/A'),
            'website': getattr(tenant, 'website', 'N/A'),
            'nif': getattr(tenant, 'nif', 'N/A')
        }
        return info

    @staticmethod
    def generate_fiscal_document(instance, doc_type_code, is_copy=False, page_format='A4'):
        """
        Gera documento fiscal unificado com design enterprise.
        """
        buffer = BytesIO()

        if page_format == '80mm':
            page_size = (8.0 * cm, 28.0 * cm)  # Aumentado para caber logo e info extra
            margin = 0.4 * cm
        else:
            page_size = A4
            margin = 2.0 * cm

        p = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size

        data = SOTARQExporter._extract_document_data(instance)
        C = SOTARQExporter._get_tenant_colors(data['tenant'])

        if page_format == 'A4':
            SOTARQExporter._draw_a4_production(p, data, width, height, margin, is_copy, C)
        else:
            SOTARQExporter._draw_80mm_production(p, data, width, height, margin, is_copy, C)

        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def _extract_document_data(instance):
        """Extrai e normaliza dados do documento."""
        tenant = getattr(instance, 'tenant', None)

        # Se não tiver tenant direto, tenta pegar via student
        if not tenant and hasattr(instance, 'student') and instance.student:
            if hasattr(instance.student, 'user') and instance.student.user:
                tenant = getattr(instance.student.user, 'tenant', None)

        # Cliente/Aluno
        client_info = {
            'name': "CONSUMIDOR FINAL",
            'nif': "999999999",
            'id': "N/A",
            'address': "N/A"
        }

        if hasattr(instance, 'student') and instance.student:
            student = instance.student
            client_info.update({
                'name': student.full_name.upper(),
                'nif': getattr(student, 'nif', "999999999"),
                'id': f"PROC: {student.registration_number}",
                'address': getattr(student, 'address', 'N/A')
            })

        # Número do documento
        doc_number = getattr(instance, 'number',
                           getattr(instance, 'numero_documento',
                                  getattr(instance, 'invoice', {}).get('number', 'S/N')))

        # Status exato do Invoice
        #status_display = instance.get_status_display() if hasattr(instance, 'get_status_display') else instance.status
        #agt_status = "NORMAL" if instance.status in ['paid', 'confirmed'] else "ANULADO"

        issue_date = getattr(instance, 'issue_date', None)
        date_str = issue_date.strftime('%d/%m/%Y') if issue_date else 'N/A'

        tax_pct = instance.tax_type.tax_percentage if getattr(instance, 'tax_type', None) else 0

        return {
            'tenant': tenant,
            'client': client_info,
            'doc_number': doc_number,
            'doc_type': getattr(instance, 'get_doc_type_display', lambda: 'DOCUMENTO')().upper(), # get_doc_type_display vai chamar o DocType (código) e transformar FT em Fatura em Maiúscula
            'date': date_str,
            'items': list(getattr(instance, 'items', []).all()) if hasattr(instance, 'items') else [],
            'subtotal': getattr(instance, 'subtotal', 0),
            'discount': getattr(instance, 'discount_amount', 0),
            'tax_amount': getattr(instance, 'tax_amount', 0),
            'total': getattr(instance, 'total', 0),
            'tax_percentage': tax_pct,
            'instance': instance,
        }

    def _draw_80mm_production(p, data, width, height, margin, is_copy, C):
        """
        Layout térmico 80mm — limpo, legível e profissional.
        Mantém todos os campos (logo, nome tenant, cliente, items, totais, QR, banco, AGT).
        """
        y = height - 0.5 * cm

        # Logo (central) — menor, com margem
        logo_path = SOTARQExporter._get_tenant_logo(data['tenant'])
        if logo_path:
            try:
                logo_w = 3.0 * cm
                logo_h = 1.4 * cm
                logo_x = (width - logo_w) / 2
                p.drawImage(logo_path, logo_x, y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True)
                y -= logo_h + 0.2 * cm
            except Exception:
                y -= 0.2 * cm
        else:
            y -= 0.2 * cm

        # Nome do tenant — primário, legível
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 9)
        tenant_name = data['tenant'].name.upper() if data['tenant'] else "SOTARQ SYSTEM"
        p.drawCentredString(width / 2, y, tenant_name)

        # Contact + NIF
        y -= 0.35 * cm
        p.setFont("Helvetica", 7)
        p.setFillColor(C['gray_600'])
        contact = SOTARQExporter._get_tenant_contact_info(data['tenant'])
        p.drawCentredString(width / 2, y, f"{contact['address']} | Tel: {contact['phone']}")

        y -= 0.28 * cm
        p.setFont("Helvetica", 7)
        nif = getattr(data['tenant'], 'nif', '999999999') if data['tenant'] else '999999999'
        p.drawCentredString(width / 2, y, f"NIF: {nif}")

        # Divider
        y -= 0.4 * cm
        p.setStrokeColor(C['gray_200'])
        p.setLineWidth(0.6)
        p.line(margin, y, width - margin, y)

        # Doc type e número centralizados
        y -= 0.5 * cm
        p.setFillColor(C['primary_dark'])
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(width / 2, y, data['doc_type'])
        y -= 0.35 * cm
        p.setFont("Helvetica-Bold", 9)
        p.setFillColor(C['gray_800'])
        p.drawCentredString(width / 2, y, f"Nº {data['doc_number']}")

        # Data e 2ª via se houver
        y -= 0.5 * cm
        p.setFont("Helvetica", 7)
        p.setFillColor(C['gray_600'])
        p.drawCentredString(width / 2, y, f"Data: {data['date']}")
        if is_copy:
            y -= 0.35 * cm
            p.setFillColor(C['danger'])
            p.setFont("Helvetica-Bold", 8)
            p.drawCentredString(width / 2, y, "2ª VIA")

        # Cliente
        y -= 0.5 * cm
        p.setFillColor(C['black'])
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin, y, "CLIENTE:")
        p.setFont("Helvetica", 8)
        p.setFillColor(C['gray_800'])
        p.drawString(margin + 2.0 * cm, y, data['client']['name'])

        y -= 0.32 * cm
        p.setFont("Helvetica", 7)
        p.setFillColor(C['gray_600'])
        p.drawString(margin, y, f"NIF: {data['client']['nif']}  |  {data['client']['id']}")

        y -= 0.28 * cm
        p.drawString(margin, y, f"End.: {data['client']['address'][:40]}")

        # Divider
        y -= 0.35 * cm
        p.setStrokeColor(C['gray_200'])
        p.line(margin, y, width - margin, y)

        # Itens — cabeçalho simples
        y -= 0.4 * cm
        p.setFont("Helvetica-Bold", 8)
        p.setFillColor(C['primary'])
        p.drawString(margin, y, "DESCRIÇÃO")
        p.drawRightString(width - margin, y, "TOTAL")
        y -= 0.2 * cm
        p.setStrokeColor(C['gray_200'])
        p.line(margin, y, width - margin, y)

        # Lista de itens com zebra leve
        p.setFont("Helvetica", 8)
        item_y = y - 0.35 * cm
        for idx, item in enumerate(data['items']):
            if idx % 2 == 0:
                p.setFillColor(C['gray_50'])
                p.rect(margin, item_y - 0.08 * cm, width - 2 * margin, 0.42 * cm, fill=1, stroke=0)
            p.setFillColor(C['gray_800'])
            desc = item.description[:32] + '..' if len(item.description) > 32 else item.description
            p.drawString(margin + 0.05 * cm, item_y, desc)
            p.drawRightString(width - margin, item_y, f"{item.amount:,.2f} Kz")
            item_y -= 0.46 * cm

        # Totais
        y = item_y - 0.25 * cm
        p.setStrokeColor(C['gray_200'])
        p.line(margin, y, width - margin, y)
        y -= 0.4 * cm
        p.setFont("Helvetica", 8)
        p.setFillColor(C['gray_600'])
        p.drawString(margin + 1.0 * cm, y, "Valor Base:")
        p.drawRightString(width - margin, y, f"{data['subtotal']:,.2f} Kz")
        if data['discount'] > 0:
            y -= 0.35 * cm
            p.setFillColor(C['danger'])
            p.drawString(margin + 1.0 * cm, y, "Desconto:")
            p.drawRightString(width - margin, y, f"- {data['discount']:,.2f} Kz")
        y -= 0.35 * cm
        p.setFillColor(C['gray_600'])
        p.drawString(margin + 1.0 * cm, y, f"IVA ({data['tax_percentage']:g}%):")
        p.drawRightString(width - margin, y, f"{data['tax_amount']:,.2f} Kz")

        # Linha secundária e total destacado
        y -= 0.5 * cm
        p.setStrokeColor(C['secondary'])
        p.setLineWidth(1.0)
        p.line(margin + 1.0 * cm, y, width - margin, y)
        y -= 0.6 * cm
        p.setFont("Helvetica-Bold", 10)
        p.setFillColor(C['primary'])
        p.drawString(margin, y, "TOTAL A PAGAR")
        p.setFillColor(C['secondary'])
        p.drawRightString(width - margin, y, f"{data['total']:,.2f} Kz")

        # QR
        y -= 1.8 * cm
        qr_size = 2.6 * cm
        qr_x = (width - qr_size) / 2
        p.setFillColor(C['white'])
        p.rect(qr_x - 0.12 * cm, y - qr_size - 0.12 * cm, qr_size + 0.24 * cm, qr_size + 0.24 * cm, fill=1, stroke=0)
        p.setStrokeColor(C['gray_200'])
        p.rect(qr_x - 0.12 * cm, y - qr_size - 0.12 * cm, qr_size + 0.24 * cm, qr_size + 0.24 * cm, fill=0, stroke=1)

        qr_drawn = False
        try:
            qr_img = generate_agt_qrcode_image(data['instance'])
            if qr_img:
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                p.drawImage(ImageReader(qr_buffer), qr_x, y - qr_size, width=qr_size, height=qr_size, preserveAspectRatio=True)
                qr_drawn = True
        except Exception:
            pass

        if not qr_drawn:
            p.setFillColor(C['gray_400'])
            p.setFont("Helvetica", 7)
            p.drawCentredString(width / 2, y - qr_size / 2, "[QR AGT]")

        # AGT label
        y -= qr_size + 0.35 * cm
        p.setFont("Helvetica", 6)
        p.setFillColor(C['gray_600'])
        p.drawCentredString(width / 2, y, SOTARQExporter._get_agt_footer_text())

        # Bank info e mensagem fiscal
        y -= 0.45 * cm
        p.setFont("Helvetica", 6)
        p.setFillColor(C['gray_600'])
        bank_info = SOTARQExporter._get_bank_info(data['tenant'])
        if len(bank_info) > 45:
            p.drawCentredString(width / 2, y, bank_info[:45])
            y -= 0.25 * cm
            p.drawCentredString(width / 2, y, bank_info[45:])
        else:
            p.drawCentredString(width / 2, y, bank_info)

        y -= 0.35 * cm
        p.setFont("Helvetica", 6)
        p.setFillColor(C['gray_400'])
        p.drawCentredString(width / 2, y, "Os bens/Serviços foram colocados à disposição do cliente no local e data do documento.")

    def _draw_a4_production(p, data, width, height, margin, is_copy, C):
        """
        Layout A4 — simplificado, espaçado, corporativo (SaaS/enterprise).
        Mantém todos os campos: logo, tenant info, cliente, tabela de itens, totais, QR, banco, AGT.
        """
        content_w = width - 2 * margin

        def draw_line(y_pos, color=C['gray_200'], thickness=0.6):
            p.setStrokeColor(color)
            p.setLineWidth(thickness)
            p.line(margin, y_pos, margin + content_w, y_pos)

        # HEADER — card branco com barra indigo à esquerda para identidade
        header_h = 4.6 * cm
        header_y = height - margin - header_h

        # Card branco com sombra sutil (sombra simulada por linha)
        p.setFillColor(C['white'])
        p.rect(margin, header_y, content_w, header_h, fill=1, stroke=0)
        p.setStrokeColor(C['gray_200'])
        p.setLineWidth(0.6)
        p.line(margin, header_y + header_h, margin + content_w, header_y + header_h)

        # Barra lateral indigo
        p.setFillColor(C['primary'])
        p.rect(margin, header_y, 0.28 * cm, header_h, fill=1, stroke=0)

        # Logo + tenant info (esquerda)
        left_x = margin + 0.6 * cm
        top_y = header_y + header_h - 0.6 * cm
        logo_path = SOTARQExporter._get_tenant_logo(data['tenant'])
        if logo_path:
            try:
                logo_w = 2.6 * cm
                logo_h = 1.8 * cm
                p.drawImage(logo_path, left_x, top_y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True)
                text_y = top_y - logo_h - 0.15 * cm
            except Exception:
                text_y = top_y - 0.2 * cm
        else:
            text_y = top_y - 0.2 * cm

        # --- CABEÇALHO SOTARQ SCHOOL AJUSTADO ---
        # Definimos o ponto de partida relativo ao topo da página
        text_y = top_y - 0.2 * cm 

        # 1. Nome da Instituição (Destaque Principal)
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 14)
        tenant_name = data['tenant'].name.upper() if data['tenant'] else "SOTARQ SYSTEM"
        p.drawString(left_x + 2.9 * cm, text_y, tenant_name)

        # 2. Respiro entre Título e Contatos (0.7cm é o "Golden Gap")
        text_y -= 0.7 * cm 

        # 3. Endereço (Cor Secundária e Fonte Menor)
        contact = SOTARQExporter._get_tenant_contact_info(data['tenant'])
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 8) 
        p.drawString(left_x + 2.9 * cm, text_y, contact['address'])

        # 4. Telefone e Web (Linha dedicada para não sobrecarregar o endereço)
        text_y -= 0.45 * cm
        p.drawString(left_x + 2.9 * cm, text_y, f"Tel: {contact['phone']} | {contact['website']}")
        p.drawString(left_x + 2.9 * cm, text_y, f"NIF: {contact['nif']} | Email: {contact['email']}")

        # 5. Margem de segurança para o próximo bloco (Ex: Dados do Aluno)
        text_y -= 0.8 * cm


        # Doc Type e Number (direita)
        p.setFillColor(C['secondary'])
        p.setFont("Helvetica-Bold", 28)
        p.drawRightString(margin + content_w - 0.6 * cm, header_y + header_h - 1.0 * cm, data['doc_type'])

        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica-Bold", 12)
        p.drawRightString(margin + content_w - 0.6 * cm, header_y + header_h - 2.0 * cm, f"Nº {data['doc_number']}")

        # Data e status linha abaixo
        p.setFont("Helvetica", 10)
        p.setFillColor(C['gray_600'])
        p.drawRightString(margin + content_w - 0.6 * cm, header_y + header_h - 2.9 * cm, f"Data: {data['date']}")
        if is_copy:
            p.setFillColor(C['danger'])
            p.setFont("Helvetica-Bold", 11)
            p.drawRightString(margin + content_w - 0.6 * cm, header_y + header_h - 3.7 * cm, "2ª VIA")

        current_y = header_y - 0.8 * cm

        # CLIENT CARD
        client_h = 2.8 * cm
        p.setFillColor(C['gray_50'])
        p.rect(margin, current_y - client_h, content_w, client_h, fill=1, stroke=0)
        p.setFillColor(C['primary'])
        p.rect(margin, current_y - client_h, 0.2 * cm, client_h, fill=1, stroke=0)

        p.setFillColor(C['black'])
        p.setFont("Helvetica-Bold", 11)
        p.drawString(left_x, current_y - 0.8 * cm, "Dados do cliente")

        p.setFont("Helvetica-Bold", 12)
        p.setFillColor(C['gray_800'])
        p.drawString(left_x, current_y - 1.6 * cm, data['client']['name'])

        p.setFont("Helvetica", 10)
        p.setFillColor(C['gray_600'])
        p.drawString(left_x, current_y - 2.2 * cm, f"NIF: {data['client']['nif']}  |  {data['client']['id']}")
        p.drawString(left_x, current_y - 2.8 * cm, f"Endereço: {data['client']['address']}")

        current_y = current_y - client_h - 0.8 * cm

        # TABELA DE ITENS (estética enterprise)
        table_data = [["Descrição", "Qtd", "Preço Unit.", "Desconto", "Total"]]
        for item in data['items']:
            table_data.append([        item.description,        "1",        f"{item.amount:,.2f}",        "0,00",        f"{item.amount:,.2f}"    ])
        if not data['items']:
            table_data.append([        f"Pagamento - {data['doc_type']} {data['doc_number']}",        "1",        f"{data['total']:,.2f}",        "0,00",        f"{data['total']:,.2f}"    ])

        col_widths = [content_w * 0.48, content_w * 0.10, content_w * 0.13, content_w * 0.14, content_w * 0.15]
        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        style = TableStyle([    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),    ('FONTSIZE', (0, 0), (-1, 0), 10),    ('TEXTCOLOR', (0, 0), (-1, 0), C['white']),
            ('BACKGROUND', (0, 0), (-1, 0), C['primary']),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('TOPPADDING', (0, 0), (-1, 0), 10),

            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), C['gray_800']),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
            ('TOPPADDING', (0, 1), (-1, -1), 8),

            ('LINEBELOW', (0, 0), (-1, 0), 1.8, C['secondary']),
            ('LINEBELOW', (0, 1), (-1, -2), 0.4, C['gray_200']),
            ('LINEBELOW', (0, -1), (-1, -1), 1.2, C['primary']),
        ])

        # zebra leve
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style.add('BACKGROUND', (0, i), (-1, i), C['gray_50'])

        table.setStyle(style)
        tw, th = table.wrapOn(p, content_w, current_y - margin)
        table.drawOn(p, margin, current_y - th)
        table_bottom = current_y - th
        current_y = table_bottom - 1.2 * cm

        # TOTAIS — card destacado à direita
        totals_w = 9.0 * cm
        totals_h = 4.6 * cm
        totals_x = margin + content_w - totals_w
        totals_y = current_y - totals_h

        p.setFillColor(C['gray_50'])
        p.rect(totals_x, totals_y, totals_w, totals_h, fill=1, stroke=0)
        p.setFillColor(C['secondary'])
        p.rect(totals_x, totals_y + totals_h - 0.28 * cm, totals_w, 0.28 * cm, fill=1, stroke=0)

        lx = totals_x + 0.8 * cm
        rx = totals_x + totals_w - 0.8 * cm
        ly = totals_y + totals_h - 1.1 * cm
        p.setFont("Helvetica", 10)
        p.setFillColor(C['gray_600'])
        p.drawString(lx, ly, "Subtotal")
        p.drawRightString(rx, ly, f"{data['subtotal']:,.2f} Kz")
        ly -= 0.8 * cm
        if data['discount'] > 0:
            p.setFillColor(C['danger'])
            p.drawString(lx, ly, "Desconto")
            p.drawRightString(rx, ly, f"- {data['discount']:,.2f} Kz")
            ly -= 0.8 * cm
            p.setFillColor(C['gray_600'])
        p.drawString(lx, ly, f"IVA ({data['tax_percentage']:g}%)")
        p.drawRightString(rx, ly, f"{data['tax_amount']:,.2f} Kz")
        ly -= 1.0 * cm

        # linha e total
        p.setStrokeColor(C['secondary'])
        p.setLineWidth(1.2)
        p.line(totals_x + 0.8 * cm, ly + 0.6 * cm, totals_x + totals_w - 0.8 * cm, ly + 0.6 * cm)
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 16)
        p.drawString(lx, ly, "TOTAL")
        p.drawRightString(rx, ly, f"{data['total']:,.2f} Kz")

        current_y = totals_y - 1.4 * cm

        # FOOTER — barra escura com QR e info bancária
        footer_h = 4.0 * cm
        footer_y = margin
        p.setFillColor(C['primary_dark'])
        p.rect(margin, footer_y, content_w, footer_h, fill=1, stroke=0)

        # Dados pagamento (esquerda)
        info_x = margin + 0.9 * cm
        info_y = footer_y + footer_h - 0.8 * cm
        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 10)
        p.drawString(info_x, info_y, "Dados para Pagamento")
        p.setFont("Helvetica", 9)
        info_y -= 0.6 * cm
        bank_info = SOTARQExporter._get_bank_info(data['tenant'])
        if len(bank_info) > 60:
            p.drawString(info_x, info_y, bank_info[:60])
            info_y -= 0.5 * cm
            p.drawString(info_x, info_y, bank_info[60:])
        else:
            p.drawString(info_x, info_y, bank_info)

        # AGT text
        p.setFont("Helvetica-Bold", 8)
        p.drawString(info_x, footer_y + 0.7 * cm, SOTARQExporter._get_agt_footer_text())
        p.setFont("Helvetica", 8)
        p.drawString(info_x, footer_y + 0.35 * cm, "Os bens/Serviços foram colocados à disposição do cliente no local e data do documento.")

        # QR no canto direito
        qr_size = 3.0 * cm
        qr_x = margin + content_w - qr_size - 0.9 * cm
        qr_y = footer_y + 0.5 * cm
        p.setFillColor(C['white'])
        p.rect(qr_x - 0.2 * cm, qr_y - 0.2 * cm, qr_size + 0.4 * cm, qr_size + 0.4 * cm, fill=1, stroke=0)
        p.setStrokeColor(C['gray_200'])
        p.rect(qr_x - 0.2 * cm, qr_y - 0.2 * cm, qr_size + 0.4 * cm, qr_size + 0.4 * cm, fill=0, stroke=1)

        qr_drawn = False
        try:
            qr_img = generate_agt_qrcode_image(data['instance'])
            if qr_img:
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                p.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_size, height=qr_size, preserveAspectRatio=True)
                qr_drawn = True
        except Exception:
            pass
        if not qr_drawn:
            p.setFillColor(C['gray_400'])
            p.setFont("Helvetica", 7)
            p.drawCentredString(qr_x + qr_size / 2, qr_y + qr_size / 2, "[QR AGT]")


def generate_debt_agreement_pdf(agreement):
    """
    Gera o PDF do Contrato de Confissão e Parcelamento de Dívida.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    # Estilos Customizados
    title_style = ParagraphStyle('Title', parent=styles['Heading1'], alignment=1, spaceAfter=20)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], alignment=4, leading=14, spaceAfter=12)

    elements = []

    # 1. TÍTULO
    elements.append(Paragraph(f"CONTRATO DE CONFISSÃO E PARCELAMENTO DE DÍVIDA Nº {agreement.id}", title_style))
    elements.append(Spacer(1, 12))

    # 2. IDENTIFICAÇÃO DAS PARTES
    text_partes = (
        f"<b>CREDORA:</b> {agreement.student.user.tenant.name}, com sede em Malanje, Angola.<br/><br/>"
        f"<b>DEVEDOR(A):</b> Encarregado(a) de Educação do aluno(a) <b>{agreement.student.full_name}</b>, "
        f"inscrito sob o processo nº {agreement.student.registration_number}."
    )
    elements.append(Paragraph(text_partes, body_style))

    # 3. CLÁUSULA PRIMEIRA - DO OBJETO
    elements.append(Paragraph("<b>CLÁUSULA PRIMEIRA:</b> O DEVEDOR reconhece e confessa ser devedor da quantia de:", body_style))
    elements.append(Paragraph(f"<font size=14><b>{agreement.total_debt_original:,.2f} Kz</b></font>", title_style))

    # 4. CLÁUSULA SEGUNDA - DO PARCELAMENTO
    text_parcelas = (
        f"A dívida acima mencionada será liquidada em <b>{agreement.installments_count} prestações mensais</b>. "
        "O não pagamento de qualquer prestação implicará o vencimento antecipado das demais e a aplicação de multas contratuais."
    )
    elements.append(Paragraph(f"<b>CLÁUSULA SEGUNDA:</b> {text_parcelas}", body_style))

    # 5. TABELA DE PRESTAÇÕES
    data = [["Prestação", "Vencimento", "Valor"]]
    installments = Invoice.objects.filter(description__contains=f"Acordo #{agreement.id}").order_by('due_date')
    for inst in installments:
        data.append([inst.description.split()[1], inst.due_date.strftime('%d/%m/%Y'), f"{inst.total:,.2f} Kz"])

    t = Table(data, colWidths=[4*cm, 5*cm, 5*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.slateblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 24))

    # 6. ASSINATURA DIGITAL (Audit Trail)
    elements.append(Paragraph("<b>CLÁUSULA TERCEIRA:</b> Este contrato é firmado por meios eletrónicos através de autenticação por usuário e senha, possuindo validade jurídica plena.", body_style))
    elements.append(Spacer(1, 40))
    
    # Rodapé de Assinatura
    p_assinatura = (
        "________________________________________________<br/>"
        f"<b>{agreement.student.user.tenant.name}</b> (Assinado Digitalmente)<br/><br/>"
        "________________________________________________<br/>"
        f"<b>DEVEDOR: {agreement.student.full_name}</b>"
    )
    elements.append(Paragraph(p_assinatura, body_style))

    doc.build(elements)
    pdf = buffer.getvalue()
    buffer.close()
    return pdf
