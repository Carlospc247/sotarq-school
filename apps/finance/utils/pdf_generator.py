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






class SOTARQExporter:
    """
    Motor Supremo v2.5 - Dual Format (A4 & 80mm).
    Rigor: Conformidade AGT + Design Adaptativo.
    """

    @staticmethod
    def generate_fiscal_document(instance, doc_type_code, is_copy=False, page_format='A4'):
        buffer = BytesIO()
        
        # Definição de Dimensões
        if page_format == '80mm':
            # 80mm de largura (aprox 226 pts), altura dinâmica (usamos um padrão longo e o p.showPage corta)
            page_size = (8.0 * cm, 30.0 * cm) 
            margin = 0.3 * cm
        else:
            page_size = A4
            margin = 2.0 * cm

        p = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size

        # 1. Metadados e Mapeamento de Status XSD (Rigor AGT)
        tenant = instance.student.user.tenant if hasattr(instance, 'student') else instance.invoice.student.user.tenant
        student = instance.student if hasattr(instance, 'student') else instance.invoice.student
        doc_number = instance.number if hasattr(instance, 'number') else instance.numero_documento
        
        # Mapeamento exigido pelo XSD (N=Normal, A=Anulado)
        # Note: No PDF legal deve aparecer o nome por extenso, mas o rastro digital segue o código.
        agt_status_label = "NORMAL" if instance.status == 'confirmed' else "ANULADO"

        # --- 2. LÓGICA DE DESIGN POR FORMATO ---
        if page_format == 'A4':
            SOTARQExporter._draw_a4_layout(p, instance, tenant, student, doc_number, agt_status_label, is_copy, width, height)
        else:
            SOTARQExporter._draw_80mm_layout(p, instance, tenant, student, doc_number, agt_status_label, is_copy, width, height)

        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def _draw_a4_layout(p, instance, tenant, student, doc_number, agt_status_label, is_copy, width, height):
        # [Sua lógica de marca d'água e layout A4 que você enviou acima entra aqui...]
        # Garanti que o agt_status_label apareça no cabeçalho
        p.setFont("Helvetica-Bold", 10)
        p.drawString(2*cm, height-7.0*cm, f"ESTADO: {agt_status_label}")
        # ... restante do código A4 ...

    @staticmethod
    def _draw_80mm_layout(p, instance, tenant, student, doc_number, agt_status_label, is_copy, width, height):
        """Layout térmico otimizado para rolos de 80mm."""
        y = height - 1*cm
        
        # Logo Centralizado (Pequeno)
        if tenant.logo:
            try:
                p.drawImage(tenant.logo.path, (width/2)-1*cm, y, width=2*cm, preserveAspectRatio=True, mask='auto')
                y -= 1.5*cm
            except: pass

        p.setFont("Helvetica-Bold", 10)
        p.drawCentredString(width/2, y, tenant.name.upper())
        y -= 0.4*cm
        p.setFont("Helvetica", 8)
        p.drawCentredString(width/2, y, f"NIF: {getattr(tenant, 'tax_id', '9999999999')}")
        y -= 0.8*cm

        # Info Documento
        p.line(0.5*cm, y, width-0.5*cm, y)
        y -= 0.4*cm
        p.setFont("Helvetica-Bold", 9)
        p.drawCentredString(width/2, y, instance.get_doc_type_display().upper()) # Usando isto, o documentos suporta todos os tipos de documentos que estão em apps/fiscal/models.py class DocumentoFiscal |||| VER NOTAS.md
        y -= 0.4*cm
        p.drawCentredString(width/2, y, doc_number)
        y -= 0.4*cm
        p.setFont("Helvetica", 7)
        p.drawCentredString(width/2, y, f"ESTADO: {agt_status_label}")
        y -= 0.4*cm
        p.line(0.5*cm, y, width-0.5*cm, y)
        y -= 0.6*cm

        # Itens (Simplificado)
        p.setFont("Helvetica-Bold", 7)
        p.drawString(0.5*cm, y, "DESCRIÇÃO")
        p.drawRightString(width-0.5*cm, y, "TOTAL")
        y -= 0.3*cm

        p.setFont("Helvetica", 7)
        if hasattr(instance, 'items'):
            for item in instance.items.all():
                y -= 0.4*cm
                p.drawString(0.5*cm, y, item.description[:30])
                p.drawRightString(width-0.5*cm, y, f"{item.amount:,.2f}")
        
        # Totais e QR Code
        y -= 1*cm
        p.setFont("Helvetica-Bold", 9)
        p.drawRightString(width-0.5*cm, y, f"TOTAL: {instance.valor_total:,.2f} Kz")
        
        y -= 2.5*cm
        qr_img = generate_agt_qrcode_image(instance)
        qr_buffer = BytesIO()
        qr_img.save(qr_buffer, format='PNG')
        p.drawImage(ImageReader(qr_buffer), (width/2)-1.25*cm, y, width=2.5*cm, height=2.5*cm)




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


