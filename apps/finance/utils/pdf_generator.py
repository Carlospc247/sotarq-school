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
            page_size = (8.0 * cm, 35.0 * cm) # Aumentado para acomodar detalhes
            margin = 0.3 * cm
        else:
            page_size = A4
            margin = 2.0 * cm

        p = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size

        # 1. RECUPERAÇÃO DO TENANT
        tenant = getattr(instance, 'tenant', None)
        if not tenant:
            if hasattr(instance, 'student') and instance.student:
                tenant = instance.student.user.tenant
            elif hasattr(instance, 'invoice') and instance.invoice:
                tenant = instance.invoice.tenant

        # 2. IDENTIDADE DO CLIENTE
        client_info = {'name': "CONSUMIDOR FINAL", 'nif': "999999999", 'id': "N/A"}
        if hasattr(instance, 'student') and instance.student:
            client_info['name'] = instance.student.full_name.upper()
            client_info['nif'] = getattr(instance.student, 'nif', "999999999")
            client_info['id'] = f"PROC: {instance.student.registration_number}"
        elif hasattr(instance, 'external_client_name') and instance.external_client_name:
            client_info['name'] = instance.external_client_name.upper()
            client_info['nif'] = getattr(instance, 'external_client_nif', "999999999")

        doc_number = getattr(instance, 'number', 'S/N')
        agt_status_label = "NORMAL" if instance.status in ['paid', 'confirmed', 'pending'] else "ANULADO"

        # 3. CHAMADA DE LAYOUT
        if page_format == 'A4':
            SOTARQExporter._draw_a4_layout(p, instance, tenant, client_info, doc_number, agt_status_label, is_copy, width, height)
        else:
            SOTARQExporter._draw_80mm_layout(p, instance, tenant, client_info, doc_number, agt_status_label, is_copy, width, height)

        p.showPage()
        p.save()
        return buffer.getvalue()

    

    @staticmethod
    def _draw_80mm_layout(p, instance, tenant, client_info, doc_number, agt_status_label, is_copy, width, height):
        Layout térmico otimizado com Bloco de Cliente Dinâmico.
        y = height - 1*cm
        
        # Logo do Tenant
        if tenant and tenant.logo:
            try:
                p.drawImage(tenant.logo.path, (width/2)-1*cm, y, width=2*cm, preserveAspectRatio=True, mask='auto')
                y -= 1.3*cm
            except: pass

        # Cabeçalho da Instituição
        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(width/2, y, tenant.name.upper() if tenant else "SOTARQ SYSTEM")
        y -= 0.4*cm
        p.setFont("Helvetica", 8)
        p.drawCentredString(width/2, y, f"NIF: {getattr(tenant, 'tax_id', '9999999999')}")
        y -= 0.8*cm

        # Info do Documento
        y -= 0.5*cm
        p.line(0.5*cm, y, width-0.5*cm, y)
        y -= 0.5*cm

        # --- BLOCO DE TOTAIS RIGOROSO (80mm) ---
        p.setFont("Helvetica", 8)
        
        # 1. SUBTOTAL (Soma bruta)
        p.drawString(width-4.5*cm, y, "SUBTOTAL (Sem Imposto):")
        p.drawRightString(width-0.5*cm, y, f"{instance.subtotal:,.2f}")
        
        # 2. DESCONTO (Só mostra se for > 0)
        if instance.discount_amount > 0:
            y -= 0.4*cm
            p.drawString(width-4.5*cm, y, f"DESCONTO ({'%' if instance.discount_is_pct else 'Vlr'}):")
            p.drawRightString(width-0.5*cm, y, f"- {instance.discount_amount:,.2f}")

        # 3. IVA (Total de Imposto)
        y -= 0.4*cm
        tax_pct = instance.tax_type.tax_percentage if instance.tax_type else 0
        p.drawString(width-4.5*cm, y, f"TOTAL IVA ({tax_pct:g}%):")
        p.drawRightString(width-0.5*cm, y, f"{instance.tax_amount:,.2f}")

        # 4. TOTAL FINAL (Líquido a Pagar)
        y -= 0.6*cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(width-4.5*cm, y, "TOTAL A PAGAR:")
        p.drawRightString(width-0.5*cm, y, f"{instance.total:,.2f} Kz")
        
        # QR Code AGT (Obrigatório)
        y -= 2.5*cm
        try:
            qr_img = generate_agt_qrcode_image(instance)
            qr_buffer = BytesIO()
            qr_img.save(qr_buffer, format='PNG')
            p.drawImage(ImageReader(qr_buffer), (width/2)-1.25*cm, y, width=2.5*cm, height=2.5*cm)
        except Exception as e:
            p.setFont("Helvetica-Oblique", 6)
            p.drawCentredString(width/2, y, "[Erro ao gerar QR Code Fiscal]")

    @staticmethod
    def _draw_a4_layout(p, instance, tenant, client_info, doc_number, agt_status_label, is_copy, width, height):
        Layout A4 de Alto Nível com Tabela de Totais.
        # Cabeçalho Institucional A4 (Omitido por brevidade, mantendo seu padrão)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(2*cm, height-7.5*cm, f"CLIENTE: {client_info['name']}")
        
        # --- TABELA DE TOTAIS NO A4 (Posicionada ao final da página ou após itens) ---
        # No A4, para ser "lindo", usamos um retângulo de destaque para o Total
        total_y_start = 6*cm # Exemplo de posição no rodapé do A4
        
        p.setStrokeColor(colors.lightgrey)
        p.line(12*cm, total_y_start + 2.2*cm, width-2*cm, total_y_start + 2.2*cm)
        
        p.setFont("Helvetica", 10)
        # Alinhamento de labels à esquerda da coluna de valores
        label_x = 13*cm
        value_x = width - 2*cm

        # Linha Subtotal
        p.drawString(label_x, total_y_start + 1.5*cm, "Total Ilíquido (Subtotal):")
        p.drawRightString(value_x, total_y_start + 1.5*cm, f"{instance.subtotal:,.2f} Kz")

        # Linha Desconto
        p.drawString(label_x, total_y_start + 1.0*cm, f"Total de Descontos:")
        p.drawRightString(value_x, total_y_start + 1.0*cm, f"- {instance.discount_amount:,.2f} Kz")

        # Linha IVA
        tax_pct = instance.tax_type.tax_percentage if instance.tax_type else 0
        p.drawString(label_x, total_y_start + 0.5*cm, f"Imposto (IVA {tax_pct:g}%):")
        p.drawRightString(value_x, total_y_start + 0.5*cm, f"{instance.tax_amount:,.2f} Kz")

        # Destaque do Total Final
        p.setFillColor(colors.whitesmoke)
        p.rect(12.5*cm, total_y_start - 0.7*cm, 6.5*cm, 0.8*cm, fill=1, stroke=0)
        p.setFillColor(colors.black)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(13*cm, total_y_start - 0.4*cm, "TOTAL A PAGAR:")
        p.drawRightString(value_x, total_y_start - 0.4*cm, f"{instance.total:,.2f} Kz")


"""



class SOTARQExporter:
    """
    Motor Supremo v3.2 - Clean Fiscal Edition.
    Rigor: Faturamento Direto (Sem Itens/Produtos) + Transparência AGT.
    """

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
        """Layout Térmico com Listagem Simples."""
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

    @staticmethod
    def _draw_a4_clean_layout(p, instance, tenant, client_info, doc_number, agt_status_label, width, height):
        """Layout A4 com Tabela de Itens Detalhada."""
        # 1. Cabeçalho e Info Cliente (Mantido)
        p.setFont("Helvetica-Bold", 14)
        p.drawString(2*cm, height-3*cm, tenant.name.upper() if tenant else "SOTARQ SCHOOL")
        
        p.setFont("Helvetica", 10)
        p.drawString(2*cm, height-3.5*cm, f"NIF: {getattr(tenant, 'tax_id', '999999999')}")
        
        p.setFont("Helvetica-Bold", 11)
        p.drawString(2*cm, height-5*cm, f"DOCUMENTO: {instance.get_doc_type_display().upper()} {doc_number}")
        p.setFont("Helvetica", 10)
        p.drawString(2*cm, height-5.6*cm, f"CLIENTE: {client_info['name']} | NIF: {client_info['nif']}")

        # 2. TABELA DE ITENS (O Coração da Fatura)
        data = [["Descrição", "Qtd", "Preço Unit.", "Total"]]
        for item in instance.items.all():
            data.append([
                item.description, 
                "1", 
                f"{item.amount:,.2f}", 
                f"{item.amount:,.2f}"
            ])

        table = Table(data, colWidths=[9*cm, 2*cm, 4*cm, 3.5*cm])
        table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ALIGN', (1,0), (-1,-1), 'RIGHT'),
            ('LINEBELOW', (0,0), (-1,0), 1, colors.black),
            ('TEXTCOLOR', (0,0), (-1,0), colors.black),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        
        tw, th, = table.wrapOn(p, width-4*cm, height)
        table.drawOn(p, 2*cm, height-10*cm)

        # 3. Bloco de Totais (Posição Dinâmica abaixo da tabela)
        total_y = height - 10*cm - th - 1*cm
        p.line(12*cm, total_y + 0.8*cm, width-2*cm, total_y + 0.8*cm)
        
        p.setFont("Helvetica", 10)
        p.drawString(12*cm, total_y, "Subtotal:")
        p.drawRightString(width-2*cm, total_y, f"{instance.subtotal:,.2f} Kz")
        
        p.drawString(12*cm, total_y - 0.5*cm, f"IVA ({instance.tax_type.tax_percentage if instance.tax_type else 0:g}%):")
        p.drawRightString(width-2*cm, total_y - 0.5*cm, f"{instance.tax_amount:,.2f} Kz")

        p.setFont("Helvetica-Bold", 12)
        p.drawString(12*cm, total_y - 1.2*cm, "TOTAL:")
        p.drawRightString(width-2*cm, total_y - 1.2*cm, f"{instance.total:,.2f} Kz")



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


