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





def generate_agt_qrcode_image(instance):
    """
    Gera o QR Code AGT v4 conforme Norma Técnica.
    """
    tenant = instance.student.user.tenant if hasattr(instance, 'student') else instance.invoice.student.user.tenant
    doc_number = instance.number if hasattr(instance, 'number') else instance.reference
    
    # URL de Consulta Pública AGT
    encoded_doc = quote(doc_number)
    url = f"https://quiosqueagt.minfin.gov.ao/facturacao-eletronica/consultar?emissor={tenant.tax_id}&documento={encoded_doc}"
    
    qr = qrcode.QRCode(version=4, error_correction=qrcode.constants.ERROR_CORRECT_M, box_size=10, border=4)
    qr.add_data(url)
    qr.make(fit=True)
    
    img_qr = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    
    # Inserir Logo AGT centralizado para autoridade visual
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'logoagt_small.png')
    if os.path.exists(logo_path):
        logo = Image.open(logo_path)
        qr_w, qr_h = img_qr.size
        logo_size = int(qr_w * 0.20)
        logo = logo.resize((logo_size, logo_size), Image.LANCZOS)
        pos = ((qr_w - logo_size) // 2, (qr_h - logo_size) // 2)
        img_qr.paste(logo, pos)
        
    return img_qr


"""

class SOTARQExporter:
   

    @staticmethod
    def generate_fiscal_document(instance, doc_type_code, is_copy=False, page_format='A4'):
        buffer = BytesIO()
        if page_format == '80mm':
            page_size = (8.0 * cm, 20.0 * cm) # Reduzido, pois não há lista de itens
            margin = 0.3 * cm
        else:
            page_size = A4
            margin = 2.0 * cm

        p = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size

        # 1. IDENTIDADE DO TENANT E CLIENTE
        tenant = getattr(instance, 'tenant', None)
        client_info = {'name': "CONSUMIDOR FINAL", 'nif': "999999999", 'id': "N/A"}
        
        if hasattr(instance, 'student') and instance.student:
            client_info['name'] = instance.student.full_name.upper()
            client_info['nif'] = getattr(instance.student, 'nif', "999999999")
            client_info['id'] = f"PROC: {instance.student.registration_number}"

        
        # Tenta pegar o número do documento fiscal associado, senão o da fatura
        #doc_number = "S/N"
        #if hasattr(instance, 'number'): doc_number = instance.number
        #elif hasattr(instance, 'numero_documento'): doc_number = instance.numero_documento
        #elif hasattr(instance, 'invoice'): doc_number = instance.invoice.number


        doc_number = getattr(instance, 'number', 'S/N')
        agt_status_label = "NORMAL" if instance.status in ['paid', 'confirmed'] else "ANULADO"

        # 2. SELEÇÃO DE LAYOUT
        if page_format == 'A4':
            SOTARQExporter._draw_a4_clean_layout(p, instance, tenant, client_info, doc_number, agt_status_label, width, height)
        else:
            SOTARQExporter._draw_80mm_clean_layout(p, instance, tenant, client_info, doc_number, agt_status_label, width, height)

        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def _draw_80mm_clean_layout(p, instance, tenant, client_info, doc_number, agt_status_label, width, height):
        y = height - 1*cm
        
        # Cabeçalho Institucional
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(width/2, y, tenant.name.upper() if tenant else "SOTARQ SYSTEM")
        y -= 0.4*cm
        p.setFont("Helvetica", 8)
        p.drawCentredString(width/2, y, f"NIF: {getattr(tenant, 'tax_id', '9999999999')}")
        
        # Info Documento
        y -= 0.8*cm
        p.line(0.5*cm, y, width-0.5*cm, y)
        y -= 0.5*cm
        p.setFont("Helvetica-Bold", 9)
        p.drawCentredString(width/2, y, f"{instance.get_doc_type_display().upper()} {doc_number}")
        y -= 0.4*cm
        p.setFont("Helvetica", 7)
        p.drawCentredString(width/2, y, f"ESTADO: {agt_status_label}")
        y -= 0.5*cm
        p.line(0.5*cm, y, width-0.5*cm, y)

        # Info Cliente
        y -= 0.5*cm
        p.setFont("Helvetica-Bold", 7)
        p.drawString(0.5*cm, y, f"CLIENTE: {client_info['name']}")
        y -= 0.35*cm
        p.setFont("Helvetica", 7)
        p.drawString(0.5*cm, y, f"NIF: {client_info['nif']} | {client_info['id']}")
        y -= 0.5*cm
        p.line(0.5*cm, y, width-0.5*cm, y)

        # Dentro de _draw_80mm_clean_layout, antes do Bloco de Engenharia Financeira:
        y -= 0.5*cm
        p.setFont("Helvetica-Bold", 7)
        p.drawString(0.5*cm, y, "DESCRIÇÃO")
        p.drawRightString(width-0.5*cm, y, "TOTAL")
        y -= 0.3*cm

        p.setFont("Helvetica", 7)
        for item in instance.items.all():
            y -= 0.4*cm
            # Trunca a descrição se for muito longa para o papel de 80mm
            desc = (item.description[:25] + '..') if len(item.description) > 25 else item.description
            p.drawString(0.5*cm, y, desc)
            p.drawRightString(width-0.5*cm, y, f"{item.amount:,.2f}")

        # --- BLOCO DE ENGENHARIA FINANCEIRA (TUDO O QUE RESTOU E IMPORTA) ---
        y -= 0.8*cm
        p.setFont("Helvetica", 8)
        
        # Subtotal
        p.drawString(0.5*cm, y, "Valor Base (Sem Imposto):")
        p.drawRightString(width-0.5*cm, y, f"{instance.subtotal:,.2f} Kz")
        
        # Desconto
        y -= 0.5*cm
        p.drawString(0.5*cm, y, "Total de Descontos:")
        p.drawRightString(width-0.5*cm, y, f"- {instance.discount_amount:,.2f} Kz")

        # IVA
        y -= 0.5*cm
        tax_pct = instance.tax_type.tax_percentage if instance.tax_type else 0
        p.drawString(0.5*cm, y, f"Imposto IVA ({tax_pct:g}%):")
        p.drawRightString(width-0.5*cm, y, f"{instance.tax_amount:,.2f} Kz")

        # TOTAL FINAL
        y -= 0.8*cm
        p.line(3*cm, y+0.5*cm, width-0.5*cm, y+0.5*cm)
        p.setFont("Helvetica-Bold", 9)
        p.drawString(0.5*cm, y, "TOTAL A PAGAR:")
        p.drawRightString(width-0.5*cm, y, f"{instance.total:,.2f} Kz")
        
        # QR Code AGT no rodapé
        y -= 2.5*cm
        try:
            qr_img = generate_agt_qrcode_image(instance)
            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            p.drawImage(ImageReader(qr_buffer), (width/2)-1.25*cm, y, width=2.5*cm, height=2.5*cm)
        except: pass


    def _draw_a4_clean_layout(p, instance, tenant, client_info, doc_number, agt_status_label, width, height):
  
        from reportlab.lib import colors
        from reportlab.platypus import Table, TableStyle
        from reportlab.lib.units import cm
        from reportlab.lib.utils import ImageReader

        # --- Constants / Rhythm ---
        MARGIN = 2.0 * cm
        content_width = width - 2 * MARGIN
        y = height - MARGIN

        # Typography sizes
        TITLE_SIZE = 22
        SECTION_HEADER_SIZE = 12
        BODY_SIZE = 10
        SMALL_SIZE = 9

        # Colors
        BRAND_LIGHT = colors.HexColor("#1976a5")  # lighter blue
        BRAND = colors.HexColor("#0b4f7a")  # dark blue brand
        LIGHT_GRAY = colors.HexColor("#f8fafc")
        STRIPE = colors.HexColor("#f2f6fb")
        MUTED = colors.HexColor("#6b6f76")
        FOOTER_DARK = colors.HexColor("#08324a")
        FOOTER_LIGHT = colors.HexColor("#0e556f")

        # Helper: draw rect with optional stroke
        def _rect(x, yb, w, h, fill_color=None, stroke=0):
            if fill_color:
                p.setFillColor(fill_color)
                p.rect(x, yb, w, h, fill=1, stroke=stroke)
                p.setFillColor(colors.black)
            else:
                p.rect(x, yb, w, h, fill=0, stroke=stroke)

        # Start fresh
        p.setFillColor(colors.white)
        p.rect(0, 0, width, height, fill=1, stroke=0)

        # 1) STRONG PREMIUM HEADER BANNER (two-tone with diagonal overlay)
        header_h = 3.8 * cm  # increased height slightly
        header_x = MARGIN
        header_y = y - header_h
        # Left lighter band
        _rect(header_x, header_y, content_width * 0.55, header_h, fill_color=BRAND_LIGHT, stroke=0)
        # Right darker band
        _rect(header_x + content_width * 0.55, header_y, content_width * 0.45, header_h, fill_color=BRAND, stroke=0)

        # Diagonal overlay on right side using a polygon path
        try:
            p.saveState()
            path = p.beginPath()
            px0 = header_x + content_width * 0.55
            path.moveTo(px0 + 0.0 * cm, header_y + header_h)
            path.lineTo(header_x + content_width, header_y + header_h)
            path.lineTo(header_x + content_width, header_y + header_h - 1.2 * cm)
            path.lineTo(px0 + 0.0 * cm, header_y + 0.6 * cm)
            path.close()
            p.setFillColor(colors.Color(0, 0, 0, alpha=0.06))
            p.drawPath(path, stroke=0, fill=1)
            p.restoreState()
        except Exception:
            pass

        # Left: Company name + NIF (white)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 16)
        left_x = MARGIN + 0.4 * cm
        p.drawString(left_x, y - 1.2 * cm, tenant.name.upper() if tenant else "SOTARQ SCHOOL")
        p.setFont("Helvetica", SMALL_SIZE)
        p.drawString(left_x, y - 1.9 * cm, f"NIF: {getattr(tenant, 'tax_id', '999999999')}")

        # Right: INVOICE title (with spacing)
        p.setFont("Helvetica-Bold", TITLE_SIZE)
        p.drawRightString(MARGIN + content_width - 0.6 * cm, y - 0.9 * cm, "INVOICE")
        # Add spacing and document number below title
        p.setFont("Helvetica", 11)
        p.drawRightString(MARGIN + content_width - 0.6 * cm, y - 1.6 * cm, f"{instance.get_doc_type_display().upper()} {doc_number}")

        y = header_y - 0.8 * cm  # space after header (use 0.8cm rhythm)

        # 2) CLIENT & DOCUMENT BLOCK (2-column) with card and subtle spacing
        block_h = 3.2 * cm
        block_y = y - block_h
        _rect(MARGIN, block_y, content_width, block_h, fill_color=LIGHT_GRAY, stroke=0)

        # Columns
        col_gap = 1.0 * cm
        col_w = (content_width - col_gap) / 2.0
        left_col_x = MARGIN + 0.6 * cm
        right_col_x = MARGIN + col_w + col_gap + 0.2 * cm

        # Left: Invoice To
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", SECTION_HEADER_SIZE)
        p.drawString(left_col_x, block_y + block_h - 0.9 * cm, "Invoice To")
        p.setFont("Helvetica-Bold", BODY_SIZE)
        p.drawString(left_col_x, block_y + block_h - 1.6 * cm, client_info['name'])
        p.setFont("Helvetica", SMALL_SIZE)
        p.setFillColor(MUTED)
        p.drawString(left_col_x, block_y + block_h - 2.2 * cm, f"NIF: {client_info['nif']}")
        p.drawString(left_col_x, block_y + block_h - 2.8 * cm, f"ID/Ref: {client_info['id']}")

        # Right: Document metadata
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", SECTION_HEADER_SIZE)
        p.drawString(right_col_x, block_y + block_h - 0.9 * cm, "Document")
        p.setFont("Helvetica", BODY_SIZE)
        p.drawString(right_col_x, block_y + block_h - 1.6 * cm, f"Number: {doc_number}")
        p.drawString(right_col_x, block_y + block_h - 2.2 * cm, getattr(instance, 'issue_date', None).strftime('%d/%m/%Y') if getattr(instance, 'issue_date', None) else 'N/A')

        # Status pill (refined placement)
        status_w = 3.4 * cm
        status_h = 0.7 * cm
        status_x = right_col_x
        status_y = block_y + 0.5 * cm
        status_color = colors.HexColor("#2a9d2a") if agt_status_label == "NORMAL" else colors.HexColor("#c0392b")
        p.setFillColor(status_color)
        p.roundRect(status_x, status_y, status_w, status_h, 0.2 * cm, fill=1, stroke=0)
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 9)
        p.drawCentredString(status_x + status_w / 2.0, status_y + 0.18 * cm, agt_status_label)
        p.setFillColor(colors.black)

        y = block_y - 0.8 * cm  # maintain 0.8cm rhythm

        # Subtle divider between client block and table
        p.setStrokeColor(colors.HexColor("#e1eef6"))
        p.setLineWidth(0.8)
        p.line(MARGIN, y + 0.4 * cm, width - MARGIN, y + 0.4 * cm)
        y = y - 0.6 * cm

        # 3) TABLE DESIGN (Refined)
        data = [["Descrição", "Qtd", "Preço Unit.", "Total"]]
        for item in instance.items.all():
            data.append([
                item.description,
                "1",
                f"{item.amount:,.2f}",
                f"{item.amount:,.2f}"
            ])

        table_left = MARGIN
        table_width = content_width
        # numeric columns narrower
        colWidths = [table_width * 0.58, table_width * 0.12, table_width * 0.15, table_width * 0.15]

        table = Table(data, colWidths=colWidths, repeatRows=1)
        # Table style: lighter header, row padding increased, header slightly larger
        tbl_style = TableStyle([
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), SMALL_SIZE),
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#e6f2fb")),  # lighter header tone
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#08324a")),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('LEFTPADDING', (0, 0), (0, -1), 8),
            ('LEFTPADDING', (1, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LINEBELOW', (0, 0), (-1, 0), 0.6, colors.HexColor("#cfeaf8")),
            ('LINEBELOW', (0, 1), (-1, -1), 0.25, colors.HexColor("#eef6fb")),
        ])
        # Row striping
        for idx in range(1, len(data)):
            bg = STRIPE if idx % 2 == 0 else colors.white
            tbl_style.add('BACKGROUND', (0, idx), (-1, idx), bg)

        # subtle vertical separators only for numeric columns
        tbl_style.add('LINEAFTER', (0, 0), (0, -1), 0, colors.white)  # no line after desc
        tbl_style.add('LINEAFTER', (1, 0), (1, -1), 0.5, colors.HexColor("#e1eef6"))
        tbl_style.add('LINEAFTER', (2, 0), (2, -1), 0.5, colors.HexColor("#e1eef6"))

        table.setStyle(tbl_style)

        # Draw table with enhanced row height by ensuring padding
        tw, th = table.wrap(table_width, y - MARGIN)
        table.drawOn(p, table_left, y - th)
        table_bottom = y - th
        y = table_bottom - 1.0 * cm

        # 4) TOTALS SECTION (Bottom-right card with pop and shadow)
        card_w = 8.4 * cm
        card_h = 4.4 * cm
        card_x = MARGIN + content_width - card_w
        card_y = y - card_h

        # Shadow simulation (slightly offset darker rectangle)
        shadow_offset = 0.08 * cm
        try:
            p.setFillColor(colors.Color(0, 0, 0, alpha=0.06))
            p.roundRect(card_x + shadow_offset, card_y - shadow_offset, card_w, card_h, 0.2 * cm, fill=1, stroke=0)
        except Exception:
            pass

        _rect(card_x, card_y, card_w, card_h, fill_color=STRIPE, stroke=0)

        p.setFillColor(colors.black)
        line_x_left = card_x + 0.6 * cm
        line_x_right = card_x + card_w - 0.6 * cm
        current_y = card_y + card_h - 0.9 * cm

        # Subtotal
        p.setFont("Helvetica", SMALL_SIZE)
        p.drawString(line_x_left, current_y, "Subtotal")
        p.drawRightString(line_x_right, current_y, f"{instance.subtotal:,.2f} Kz")
        current_y -= 0.7 * cm

        # Discount
        p.drawString(line_x_left, current_y, "Discount")
        p.drawRightString(line_x_right, current_y, f"- {instance.discount_amount:,.2f} Kz")
        current_y -= 0.7 * cm

        # IVA
        tax_pct = instance.tax_type.tax_percentage if instance.tax_type else 0
        p.drawString(line_x_left, current_y, f"IVA ({tax_pct:g}%)")
        p.drawRightString(line_x_right, current_y, f"{instance.tax_amount:,.2f} Kz")
        current_y -= 1.0 * cm

        # TOTAL (bold, larger)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(line_x_left, current_y, "TOTAL")
        p.drawRightString(line_x_right, current_y, f"{instance.total:,.2f} Kz")
        # subtle gray under total
        p.setFont("Helvetica", 8)
        p.setFillColor(MUTED)
        p.drawString(line_x_left, current_y - 0.6 * cm, "Taxes included")
        p.setFillColor(colors.black)

        y = card_y - 1.2 * cm

        # 5) FOOTER SECTION (Split into two zones with angled separation)
        footer_h = 2.8 * cm
        footer_y = MARGIN
        # Left dark zone
        left_zone_w = content_width * 0.55
        _rect(0, 0, left_zone_w, footer_h, fill_color=FOOTER_DARK, stroke=0)
        # Right lighter zone
        _rect(left_zone_w, 0, width - left_zone_w, footer_h, fill_color=FOOTER_LIGHT, stroke=0)

        # Angled separation similar to header (a triangle overlay)
        try:
            p.saveState()
            path2 = p.beginPath()
            path2.moveTo(left_zone_w - 0.6 * cm, footer_h)
            path2.lineTo(left_zone_w + 1.2 * cm, footer_h)
            path2.lineTo(left_zone_w + 0.6 * cm, 0)
            path2.lineTo(left_zone_w - 1.2 * cm, 0)
            path2.close()
            p.setFillColor(colors.Color(1, 1, 1, alpha=0.03))
            p.drawPath(path2, stroke=0, fill=1)
            p.restoreState()
        except Exception:
            pass

        # Left: payment info (white text)
        left_footer_x = MARGIN
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", SMALL_SIZE)
        p.drawString(left_footer_x, footer_y + footer_h - 1.0 * cm, "Payment Info")
        p.setFont("Helvetica", SMALL_SIZE)
        p.drawString(left_footer_x, footer_y + footer_h - 1.6 * cm, "Bank: BANK NAME | IBAN: AO00 0000 0000 0000 0000")

        # Add "Thank you for your business" bottom-left
        p.setFont("Helvetica", 9)
        p.drawString(left_footer_x, footer_y + 0.2 * cm, "Thank you for your business")

        # Right: QR Code area in lighter zone (aligned precisely)
        qr_min_size_cm = 3.0 * cm
        qr_w = qr_min_size_cm
        qr_h = qr_min_size_cm
        qr_x = left_zone_w + (width - left_zone_w) - qr_w - 0.6 * cm
        qr_y = footer_y + 0.4 * cm

        # White background card for QR inside lighter footer
        _rect(qr_x - 0.15 * cm, qr_y - 0.15 * cm, qr_w + 0.3 * cm, qr_h + 0.3 * cm, fill_color=colors.white, stroke=0)

        # QR code rendering with safe fallback (logic preserved)
        try:
            qr_img = generate_agt_qrcode_image(instance)
            if qr_img:
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                p.drawImage(ImageReader(qr_buffer), qr_x, qr_y, width=qr_w, height=qr_h, preserveAspectRatio=True, mask='auto')
            else:
                p.setFillColor(colors.black)
                p.rect(qr_x, qr_y, qr_w, qr_h, fill=0, stroke=1)
                p.setFont("Helvetica", 6)
                p.drawCentredString(qr_x + qr_w / 2, qr_y + qr_h / 2, "QR UNAVAILABLE")
        except Exception:
            try:
                p.setFillColor(colors.white)
                p.rect(qr_x, qr_y, qr_w, qr_h, fill=1, stroke=1)
                p.setFillColor(colors.black)
                p.setFont("Helvetica", 6)
                p.drawCentredString(qr_x + qr_w / 2, qr_y + qr_h / 2, "QR ERROR")
            except:
                pass

        # Small label "AGT QR" above QR in white/dark depending on background
        p.setFillColor(colors.white)
        p.setFont("Helvetica-Bold", 8)
        p.drawRightString(qr_x - 0.4 * cm, qr_y + qr_h - 0.1 * cm, "AGT QR")

        # 6) Final touches: subtle dividing line above footer and alignment guides
        p.setStrokeColor(colors.HexColor("#aacbe1"))
        p.setLineWidth(0.5)
        p.line(MARGIN, footer_y + footer_h, width - MARGIN, footer_y + footer_h)

        # Reset fillcolor to black for any further content
        p.setFillColor(colors.black)

"""


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


class SOTARQExporter:
    """
    Motor Supremo v5.0 - Production Ready.
    Design System: Indigo + Orange + AGT Compliance
    """

    @staticmethod
    def _get_tenant_colors(tenant):
        """Retorna as cores do tenant ou defaults indigo/laranja."""
        if tenant and hasattr(tenant, 'primary_color') and tenant.primary_color:
            primary = colors.HexColor(tenant.primary_color)
        else:
            primary = colors.HexColor("#4338ca")  # Indigo-700

        if tenant and hasattr(tenant, 'secondary_color') and tenant.secondary_color:
            secondary = colors.HexColor(tenant.secondary_color)
        else:
            secondary = colors.HexColor("#f97316")  # Orange-500

        return {
            'primary': primary,
            'secondary': secondary,
            'primary_dark': colors.HexColor("#3730a3"),  # Indigo-800
            'secondary_dark': colors.HexColor("#ea580c"),  # Orange-600
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
                return f"Banco: {account.bank_name} | IBAN: {account.iban} | Titular: {account.account_holder}"
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
            'website': getattr(tenant, 'website', 'N/A')
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
        status_display = instance.get_status_display() if hasattr(instance, 'get_status_display') else instance.status
        agt_status = "NORMAL" if instance.status in ['paid', 'confirmed'] else "ANULADO"

        issue_date = getattr(instance, 'issue_date', None)
        date_str = issue_date.strftime('%d/%m/%Y') if issue_date else 'N/A'

        tax_pct = instance.tax_type.tax_percentage if getattr(instance, 'tax_type', None) else 0

        return {
            'tenant': tenant,
            'client': client_info,
            'doc_number': doc_number,
            'doc_type': getattr(instance, 'get_doc_type_display', lambda: 'DOCUMENTO')().upper(),
            'status': instance.status,
            'status_display': status_display,
            'agt_status': agt_status,
            'date': date_str,
            'items': list(getattr(instance, 'items', []).all()) if hasattr(instance, 'items') else [],
            'subtotal': getattr(instance, 'subtotal', 0),
            'discount': getattr(instance, 'discount_amount', 0),
            'tax_amount': getattr(instance, 'tax_amount', 0),
            'total': getattr(instance, 'total', 0),
            'tax_percentage': tax_pct,
            'instance': instance,
        }

    @staticmethod
    def _draw_80mm_production(p, data, width, height, margin, is_copy, C):
        """Layout térmico 80mm com logo e cores do tenant."""
        y = height - 0.5 * cm

        # 1. LOGO DO TENANT
        logo_path = SOTARQExporter._get_tenant_logo(data['tenant'])
        if logo_path:
            try:
                # Logo centralizado, tamanho máximo 3cm de largura
                logo_w = 3.0 * cm
                logo_h = 1.5 * cm
                logo_x = (width - logo_w) / 2
                p.drawImage(logo_path, logo_x, y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True)
                y -= logo_h + 0.3 * cm
            except Exception:
                y -= 0.2 * cm
        else:
            y -= 0.2 * cm

        # 2. NOME DO TENANT (dinâmico)
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 10)
        tenant_name = data['tenant'].name.upper() if data['tenant'] else "SOTARQ SYSTEM"
        p.drawCentredString(width / 2, y, tenant_name)

        # 3. INFO DO TENANT (endereço, telefone)
        y -= 0.4 * cm
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 7)
        contact = SOTARQExporter._get_tenant_contact_info(data['tenant'])
        info_line = f"{contact['address'][:40]} | Tel: {contact['phone']}"
        p.drawCentredString(width / 2, y, info_line)

        y -= 0.3 * cm
        p.drawCentredString(width / 2, y, f"Site: {contact['website']}")

        # 4. NIF DO TENANT
        y -= 0.4 * cm
        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica", 8)
        nif = getattr(data['tenant'], 'tax_id', '999999999') if data['tenant'] else '999999999'
        p.drawCentredString(width / 2, y, f"NIF: {nif}")

        # Linha decorativa indigo
        y -= 0.5 * cm
        p.setStrokeColor(C['primary'])
        p.setLineWidth(1)
        p.line(margin, y, width - margin, y)

        # 5. TIPO E NÚMERO DO DOCUMENTO
        y -= 0.6 * cm
        p.setFillColor(C['secondary'])
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(width / 2, y, f"{data['doc_type']}")

        y -= 0.4 * cm
        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica-Bold", 9)
        p.drawCentredString(width / 2, y, f"Nº {data['doc_number']}")

        # 6. STATUS EXATO DO INVOICE
        y -= 0.4 * cm
        status_color = C['success'] if data['status'] == 'paid' else C['danger'] if data['status'] == 'cancelled' else C['secondary']
        p.setFillColor(status_color)
        pill_w = 3.0 * cm
        pill_x = (width - pill_w) / 2
        p.roundRect(pill_x, y - 0.1 * cm, pill_w, 0.5 * cm, 0.15 * cm, fill=1, stroke=0)
        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 8)
        p.drawCentredString(width / 2, y, data['status_display'].upper())

        # Indicador de segunda via
        if is_copy:
            y -= 0.6 * cm
            p.setFillColor(C['danger'])
            p.setFont("Helvetica-Bold", 8)
            p.drawCentredString(width / 2, y, ">>> 2ª VIA <<<")

        # Linha decorativa laranja
        y -= 0.5 * cm
        p.setStrokeColor(C['secondary'])
        p.setLineWidth(0.8)
        p.line(margin, y, width - margin, y)

        # 7. DADOS DO CLIENTE COM ENDEREÇO
        y -= 0.6 * cm
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin, y, "CLIENTE")

        y -= 0.35 * cm
        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica-Bold", 9)
        name = data['client']['name'][:32] + '..' if len(data['client']['name']) > 32 else data['client']['name']
        p.drawString(margin, y, name)

        y -= 0.3 * cm
        p.setFont("Helvetica", 7)
        p.setFillColor(C['gray_600'])
        p.drawString(margin, y, f"NIF: {data['client']['nif']}")

        y -= 0.25 * cm
        p.drawString(margin, y, data['client']['id'])

        # ENDEREÇO DO CLIENTE
        y -= 0.25 * cm
        p.drawString(margin, y, f"End: {data['client']['address'][:35]}")

        y -= 0.4 * cm
        p.setStrokeColor(C['gray_200'])
        p.setLineWidth(0.5)
        p.line(margin, y, width - margin, y)

        # 8. TABELA DE ITENS
        y -= 0.5 * cm
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin, y, "DESCRIÇÃO")
        p.drawRightString(width - margin, y, "TOTAL")

        y -= 0.2 * cm
        p.setStrokeColor(C['primary'])
        p.setLineWidth(0.6)
        p.line(margin, y, width - margin, y)

        p.setFont("Helvetica", 8)
        item_y = y - 0.35 * cm

        for idx, item in enumerate(data['items']):
            # Zebra striping
            if idx % 2 == 0:
                p.setFillColor(C['gray_50'])
                p.rect(margin, item_y - 0.08 * cm, width - 2 * margin, 0.4 * cm, fill=1, stroke=0)

            p.setFillColor(C['gray_800'])
            desc = item.description[:30] + '..' if len(item.description) > 30 else item.description
            p.drawString(margin + 0.05 * cm, item_y, desc)
            p.drawRightString(width - margin, item_y, f"{item.amount:,.2f}")
            item_y -= 0.45 * cm

        y = item_y - 0.3 * cm
        p.setStrokeColor(C['gray_200'])
        p.line(margin, y, width - margin, y)

        # 9. TOTAIS
        y -= 0.6 * cm
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 8)
        p.drawString(2.5 * cm, y, "Valor Base:")
        p.drawRightString(width - margin, y, f"{data['subtotal']:,.2f} Kz")

        if data['discount'] > 0:
            y -= 0.4 * cm
            p.setFillColor(C['danger'])
            p.drawString(2.5 * cm, y, "Desconto:")
            p.drawRightString(width - margin, y, f"- {data['discount']:,.2f} Kz")

        y -= 0.4 * cm
        p.setFillColor(C['gray_600'])
        p.drawString(2.5 * cm, y, f"IVA ({data['tax_percentage']:g}%):")
        p.drawRightString(width - margin, y, f"{data['tax_amount']:,.2f} Kz")

        # Linha antes do total
        y -= 0.5 * cm
        p.setStrokeColor(C['secondary'])
        p.setLineWidth(1.2)
        p.line(2 * cm, y, width - margin, y)

        # TOTAL DESTACADO
        y -= 0.7 * cm
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 11)
        p.drawString(margin, y, "TOTAL A PAGAR")
        p.setFillColor(C['secondary'])
        p.drawRightString(width - margin, y, f"{data['total']:,.2f} Kz")

        # 10. QR CODE COM FALLBACK VISUAL
        y -= 2.0 * cm
        qr_size = 2.5 * cm
        qr_x = (width - qr_size) / 2

        # Fundo branco para QR
        p.setFillColor(C['white'])
        p.rect(qr_x - 0.15 * cm, y - qr_size - 0.15 * cm, qr_size + 0.3 * cm, qr_size + 0.3 * cm,
               fill=1, stroke=0)
        p.setStrokeColor(C['gray_200'])
        p.rect(qr_x - 0.15 * cm, y - qr_size - 0.15 * cm, qr_size + 0.3 * cm, qr_size + 0.3 * cm,
               fill=0, stroke=1)

        qr_drawn = False
        try:
            # Tentativa de gerar QR code AGT
            from apps.fiscal.utils import generate_agt_qrcode_image
            qr_img = generate_agt_qrcode_image(data['instance'])
            if qr_img:
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                p.drawImage(ImageReader(qr_buffer), qr_x, y - qr_size,
                           width=qr_size, height=qr_size, preserveAspectRatio=True)
                qr_drawn = True
        except Exception as e:
            print(f"QR Error: {e}")

        if not qr_drawn:
            # Visual fallback se QR falhar
            p.setFillColor(C['gray_400'])
            p.setFont("Helvetica", 6)
            p.drawCentredString(width / 2, y - qr_size / 2, "[QR AGT]")
            p.drawCentredString(width / 2, y - qr_size / 2 - 0.4 * cm, "Verificação")

        # Label AGT
        y -= qr_size + 0.5 * cm
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 7)
        p.drawCentredString(width / 2, y, "AGT - Autoridade Geral Tributária")

        # 11. DADOS BANCÁRIOS DINÂMICOS
        y -= 0.6 * cm
        bank_info = SOTARQExporter._get_bank_info(data['tenant'])
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 6)
        # Quebra linha se for muito longo
        if len(bank_info) > 45:
            p.drawCentredString(width / 2, y, bank_info[:45])
            y -= 0.25 * cm
            p.drawCentredString(width / 2, y, bank_info[45:])
        else:
            p.drawCentredString(width / 2, y, bank_info)

        # 12. TEXTO DO .ENV CENTRALIZADO
        y -= 0.6 * cm
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 6)
        agt_text = SOTARQExporter._get_agt_footer_text()
        p.drawCentredString(width / 2, y, agt_text)

        # 13. MENSAGEM FISCAL OBRIGATÓRIA
        y -= 0.5 * cm
        p.setFillColor(C['gray_400'])
        p.setFont("Helvetica", 6)
        p.drawCentredString(width / 2, y, "Os bens/Serviços foram colocados à disposição")
        y -= 0.2 * cm
        p.drawCentredString(width / 2, y, "do cliente no local e data do documento.")

    @staticmethod
    def _draw_a4_production(p, data, width, height, margin, is_copy, C):
        """Layout A4 production com indigo/laranja e dados dinâmicos."""
        content_w = width - 2 * margin

        def draw_line(y_pos, color=C['gray_200'], width_line=content_w, x_start=margin, thickness=0.5):
            p.setStrokeColor(color)
            p.setLineWidth(thickness)
            p.line(x_start, y_pos, x_start + width_line, y_pos)

        # =========================================================================
        # 1. HEADER COM LOGO E CORES INDIGO/LARANJA
        # =========================================================================
        header_h = 5.0 * cm
        header_y = height - margin - header_h

        # Fundo indigo claro
        p.setFillColor(colors.HexColor("#e0e7ff"))  # Indigo-100
        p.rect(margin, header_y, content_w, header_h, fill=1, stroke=0)

        # Barra superior indigo
        p.setFillColor(C['primary'])
        p.rect(margin, height - margin - 0.4 * cm, content_w, 0.4 * cm, fill=1, stroke=0)

        # Barra inferior laranja (destaque)
        p.setFillColor(C['secondary'])
        p.rect(margin, header_y, content_w, 0.3 * cm, fill=1, stroke=0)

        left_x = margin + 0.8 * cm
        top_y = height - margin - 0.8 * cm

        # LOGO DO TENANT (esquerda)
        logo_path = SOTARQExporter._get_tenant_logo(data['tenant'])
        if logo_path:
            try:
                logo_w = 2.5 * cm
                logo_h = 2.0 * cm
                p.drawImage(logo_path, left_x, top_y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True)
                text_start_y = top_y - logo_h - 0.3 * cm
            except Exception:
                text_start_y = top_y - 0.5 * cm
        else:
            text_start_y = top_y - 0.5 * cm

        # NOME DO TENANT
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 18)
        tenant_name = data['tenant'].name.upper() if data['tenant'] else "SOTARQ SYSTEM"
        p.drawString(left_x, text_start_y, tenant_name)

        # INFO DO TENANT (endereço, telefone, site)
        text_start_y -= 0.6 * cm
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 9)
        contact = SOTARQExporter._get_tenant_contact_info(data['tenant'])
        p.drawString(left_x, text_start_y, f"{contact['address']}")

        text_start_y -= 0.4 * cm
        p.drawString(left_x, text_start_y, f"Tel: {contact['phone']} | {contact['website']}")

        text_start_y -= 0.4 * cm
        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica-Bold", 9)
        nif = getattr(data['tenant'], 'tax_id', '999999999') if data['tenant'] else '999999999'
        p.drawString(left_x, text_start_y, f"NIF: {nif}")

        # TIPO DE DOCUMENTO (direita, laranja)
        right_x = margin + content_w - 0.8 * cm
        doc_y = height - margin - 1.2 * cm

        p.setFillColor(C['secondary'])
        p.setFont("Helvetica-Bold", 28)
        p.drawRightString(right_x, doc_y, data['doc_type'])

        p.setFillColor(C['primary_dark'])
        p.setFont("Helvetica-Bold", 14)
        p.drawRightString(right_x, doc_y - 0.9 * cm, f"Nº {data['doc_number']}")

        # STATUS EXATO DO INVOICE (pill colorido)
        status_colors = {
            'paid': C['success'],
            'pending': C['secondary'],
            'cancelled': C['danger'],
            'overdue': C['danger']
        }
        status_color = status_colors.get(data['status'], C['gray_400'])

        pill_w = 3.5 * cm
        pill_h = 0.9 * cm
        pill_x = right_x - pill_w
        pill_y = doc_y - 2.0 * cm

        p.setFillColor(status_color)
        p.roundRect(pill_x, pill_y, pill_w, pill_h, 0.25 * cm, fill=1, stroke=0)
        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(right_x - pill_w / 2, pill_y + 0.3 * cm, data['status_display'].upper())

        # Data e 2ª via
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 10)
        p.drawRightString(right_x, pill_y - 0.5 * cm, f"Data: {data['date']}")

        if is_copy:
            p.setFillColor(C['danger'])
            p.setFont("Helvetica-Bold", 12)
            p.drawRightString(right_x, pill_y - 1.0 * cm, "2ª VIA")

        current_y = header_y - 1.0 * cm

        # =========================================================================
        # 2. DADOS DO CLIENTE COM ENDEREÇO
        # =========================================================================
        client_h = 3.2 * cm

        # Fundo cinza claro com borda indigo à esquerda
        p.setFillColor(C['gray_50'])
        p.rect(margin, current_y - client_h, content_w, client_h, fill=1, stroke=0)

        p.setFillColor(C['primary'])
        p.rect(margin, current_y - client_h, 0.2 * cm, client_h, fill=1, stroke=0)

        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 11)
        p.drawString(left_x, current_y - 0.8 * cm, "CLIENTE / CUSTOMER")

        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica-Bold", 12)
        p.drawString(left_x, current_y - 1.5 * cm, data['client']['name'])

        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 10)
        p.drawString(left_x, current_y - 2.2 * cm, f"NIF: {data['client']['nif']}  |  {data['client']['id']}")

        # ENDEREÇO DO CLIENTE
        p.drawString(left_x, current_y - 2.8 * cm, f"Endereço: {data['client']['address']}")

        current_y -= client_h + 1.0 * cm

        # =========================================================================
        # 3. TABELA DE ITENS - DESIGN INDIGO/LARANJA
        # =========================================================================
        table_data = [["Descrição", "Qtd", "Preço Unit.", "Desconto", "Total"]]

        for item in data['items']:
            table_data.append([
                item.description,
                "1",
                f"{item.amount:,.2f}",
                "0,00",
                f"{item.amount:,.2f}"
            ])

        if not data['items']:
            table_data.append([
                f"Pagamento - {data['doc_type']} {data['doc_number']}",
                "1",
                f"{data['total']:,.2f}",
                "0,00",
                f"{data['total']:,.2f}"
            ])

        col_widths = [
            content_w * 0.45,
            content_w * 0.10,
            content_w * 0.15,
            content_w * 0.15,
            content_w * 0.15,
        ]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        style = TableStyle([
            # Cabeçalho indigo
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TEXTCOLOR', (0, 0), (-1, 0), C['white']),
            ('BACKGROUND', (0, 0), (-1, 0), C['primary']),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('LEFTPADDING', (0, 0), (0, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),

            # Corpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), C['gray_800']),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),

            # Linhas
            ('LINEBELOW', (0, 0), (-1, 0), 2, C['secondary']),  # Linha laranja após header
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, C['gray_200']),
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, C['primary']),
        ])

        # Zebra striping
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style.add('BACKGROUND', (0, i), (-1, i), C['gray_50'])

        table.setStyle(style)

        tw, th = table.wrapOn(p, content_w, current_y - margin)
        table.drawOn(p, margin, current_y - th)

        table_bottom = current_y - th
        current_y = table_bottom - 1.0 * cm

        # =========================================================================
        # 4. TOTAIS - Card com destaque laranja
        # =========================================================================
        totals_w = 8.5 * cm
        totals_h = 4.5 * cm
        totals_x = margin + content_w - totals_w
        totals_y = current_y - totals_h

        # Fundo cinza claro
        p.setFillColor(C['gray_50'])
        p.rect(totals_x, totals_y, totals_w, totals_h, fill=1, stroke=0)

        # Barra superior laranja
        p.setFillColor(C['secondary'])
        p.rect(totals_x, totals_y + totals_h - 0.25 * cm, totals_w, 0.25 * cm, fill=1, stroke=0)

        line_x_left = totals_x + 0.8 * cm
        line_x_right = totals_x + totals_w - 0.8 * cm
        line_y = totals_y + totals_h - 0.9 * cm

        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 10)

        p.drawString(line_x_left, line_y, "Subtotal")
        p.drawRightString(line_x_right, line_y, f"{data['subtotal']:,.2f} Kz")
        line_y -= 0.8 * cm

        if data['discount'] > 0:
            p.setFillColor(C['danger'])
            p.drawString(line_x_left, line_y, "Desconto")
            p.drawRightString(line_x_right, line_y, f"- {data['discount']:,.2f} Kz")
            p.setFillColor(C['gray_600'])
            line_y -= 0.8 * cm

        p.drawString(line_x_left, line_y, f"IVA ({data['tax_percentage']:g}%)")
        p.drawRightString(line_x_right, line_y, f"{data['tax_amount']:,.2f} Kz")
        line_y -= 1.0 * cm

        # Linha antes do total
        draw_line(line_y + 0.4 * cm, color=C['secondary'], width_line=totals_w - 1.6 * cm,
                 x_start=totals_x + 0.8 * cm, thickness=1.5)

        # TOTAL em indigo
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 16)
        p.drawString(line_x_left, line_y, "TOTAL")
        p.drawRightString(line_x_right, line_y, f"{data['total']:,.2f} Kz")

        line_y -= 0.7 * cm
        p.setFillColor(C['gray_400'])
        p.setFont("Helvetica", 8)
        p.drawString(line_x_left, line_y, "Taxas incluídas")

        current_y = totals_y - 1.5 * cm


        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 10)
        p.drawString(info_x, info_y, "Dados para Pagamento")

        # Dados bancários dinâmicos
        p.setFont("Helvetica", 9)
        info_y -= 0.6 * cm
        bank_info = SOTARQExporter._get_bank_info(data['tenant'])
        # Quebra em duas linhas se necessário
        if len(bank_info) > 60:
            p.drawString(info_x, info_y, bank_info[:60])
            info_y -= 0.5 * cm
            p.drawString(info_x, info_y, bank_info[60:])
        else:
            p.drawString(info_x, info_y, bank_info)


        # =========================================================================
        # 5. RODAPÉ - Dados dinâmicos do .env e banco
        # =========================================================================
        footer_h = 4.0 * cm
        footer_y = margin

        # Fundo indigo escuro
        p.setFillColor(C['primary_dark'])
        p.rect(margin, footer_y, content_w, footer_h, fill=1, stroke=0)

        # Info à esquerda (branco)
        info_x = margin + 0.8 * cm
        info_y = footer_y + footer_h - 1.0 * cm

        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 10)
        p.drawString(info_x, info_y, "Dados para Pagamento")

        # Dados bancários dinâmicos
        p.setFont("Helvetica", 9)
        info_y -= 0.6 * cm
        bank_info = SOTARQExporter._get_bank_info(data['tenant'])
        # Quebra em duas linhas se necessário
        if len(bank_info) > 60:
            p.drawString(info_x, info_y, bank_info[:60])
            info_y -= 0.5 * cm
            p.drawString(info_x, info_y, bank_info[60:])
        else:
            p.drawString(info_x, info_y, bank_info)

        # Texto do .env centralizado no rodapé
        p.setFont("Helvetica-Bold", 8)
        agt_text = SOTARQExporter._get_agt_footer_text()
        p.drawCentredString(margin + content_w / 2, footer_y + 0.8 * cm, agt_text)

        # Mensagem fiscal obrigatória
        p.setFont("Helvetica", 8)
        p.drawString(info_x, footer_y + 0.4 * cm, "Os bens/Serviços foram colocados à disposição do cliente no local e data do documento.")

        # QR Code à direita
        qr_size = 3.0 * cm
        qr_x = margin + content_w - qr_size - 0.8 * cm
        qr_y = footer_y + 0.5 * cm

        # Fundo branco para QR
        p.setFillColor(C['white'])
        p.rect(qr_x - 0.2 * cm, qr_y - 0.2 * cm, qr_size + 0.4 * cm, qr_size + 0.4 * cm,
               fill=1, stroke=0)
        p.setStrokeColor(C['gray_200'])
        p.rect(qr_x - 0.2 * cm, qr_y - 0.2 * cm, qr_size + 0.4 * cm, qr_size + 0.4 * cm,
               fill=0, stroke=1)

        qr_drawn = False
        try:
            #from apps.fiscal.utils import generate_agt_qrcode_image
            qr_img = generate_agt_qrcode_image(data['instance'])
            if qr_img:
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                p.drawImage(ImageReader(qr_buffer), qr_x, qr_y,
                           width=qr_size, height=qr_size, preserveAspectRatio=True)
                qr_drawn = True
        except Exception as e:
            print(f"QR Error A4: {e}")

        if not qr_drawn:
            p.setFillColor(C['gray_400'])
            p.setFont("Helvetica", 7)
            p.drawCentredString(qr_x + qr_size/2, qr_y + qr_size/2, "[QR AGT]")
            p.drawCentredString(qr_x + qr_size/2, qr_y + qr_size/2 - 0.4 * cm, "Indisponível")

        # Label AGT ao lado do QR
        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 9)
        p.drawRightString(qr_x - 0.5 * cm, qr_y + qr_size - 0.3 * cm, "AGT")
        p.setFont("Helvetica", 8)
        p.drawRightString(qr_x - 0.5 * cm, qr_y + qr_size - 0.8 * cm, "QR Code")        


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
