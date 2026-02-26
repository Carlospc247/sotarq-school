from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.pagesizes import landscape
import qrcode
from io import BytesIO
from django.core.files.storage import default_storage

def generate_library_card_pdf(student):
    """
    Gera um PDF de Cartão de Leitor (Tamanho ID-1: 8.5x5.5cm)
    """
    buffer = BytesIO()
    # Dimensões do cartão de crédito em pontos (1cm = 28.35 points)
    width, height = 8.5 * cm, 5.5 * cm
    
    p = canvas.Canvas(buffer, pagesize=(width, height))

    # --- Design do Fundo ---
    p.setFillColorRGB(0.05, 0.2, 0.4) # Azul SOTARQ
    p.rect(0, 4.3 * cm, width, 1.2 * cm, fill=1, stroke=0)
    
    p.setFillColorRGB(1, 1, 1)
    p.setFont("Helvetica-Bold", 10)
    p.drawString(0.5 * cm, 4.8 * cm, "SOTARQ SCHOOL - BIBLIOTECA")
    
    # --- QR Code ---
    qr_data = student.process_number # Ou o ID do aluno
    qr = qrcode.make(qr_data)
    qr_buffer = BytesIO()
    qr.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    
    # Desenhar QR Code no cartão
    p.drawInlineImage(qr_buffer, 5.8 * cm, 0.5 * cm, width=2.2 * cm, height=2.2 * cm)

    # --- Dados do Aluno ---
    p.setFillColorRGB(0, 0, 0)
    p.setFont("Helvetica-Bold", 9)
    p.drawString(0.5 * cm, 3.2 * cm, student.full_name.upper())
    
    p.setFont("Helvetica", 8)
    p.drawString(0.5 * cm, 2.7 * cm, f"Processo: {student.process_number}")
    p.drawString(0.5 * cm, 2.3 * cm, f"Turma: {student.current_class or 'N/A'}")
    
    p.setFont("Helvetica-Oblique", 7)
    p.drawString(0.5 * cm, 0.5 * cm, "Este cartão é pessoal e intransmissível.")

    p.showPage()
    p.save()
    
    buffer.seek(0)
    return buffer