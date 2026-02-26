import os
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from pypdf import PdfReader, PdfWriter

def stamp_qr_on_pdf(original_pdf_path, qr_code_path):
    """
    Carimba o QR Code no canto inferior direito de um PDF existente.
    """
    # 1. Criar um PDF temporário em memória com apenas o QR Code
    packet = BytesIO()
    can = canvas.Canvas(packet, pagesize=A4)
    
    # Coordenadas: Canto inferior direito (x, y)
    # A4 é aprox 21cm x 29.7cm
    qr_size = 2.5 * cm
    x_pos = 17 * cm 
    y_pos = 1 * cm
    
    can.drawImage(qr_code_path, x_pos, y_pos, width=qr_size, height=qr_size)
    can.save()
    packet.seek(0)

    # 2. Ler o PDF original e o "carimbo"
    new_pdf = PdfReader(packet)
    existing_pdf = PdfReader(open(original_pdf_path, "rb"))
    output = PdfWriter()

    # 3. Mesclar o carimbo na primeira página (ou em todas)
    page = existing_pdf.pages[0]
    page.merge_page(new_pdf.pages[0])
    output.add_page(page)

    # Adicionar as páginas restantes do original sem carimbo (opcional)
    for i in range(1, len(existing_pdf.pages)):
        output.add_page(existing_pdf.pages[i])

    # 4. Retornar o PDF final em memória
    result_buffer = BytesIO()
    output.write(result_buffer)
    result_buffer.seek(0)
    return result_buffer