# Fulfillment (Entrega de Reservas Online)
# apps/compras/views_fulfillment.py
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.contrib import messages
from .models import Reservation
from reportlab.pdfgen import canvas
from django.db import transaction
from io import BytesIO

@staff_member_required
def fulfillment_scan(request, reservation_id):
    """
    Interface que abre após o scan do QR Code da Reserva.
    Exibe os detalhes para o funcionário conferir antes de entregar.
    """
    reservation = get_object_or_404(Reservation, id=reservation_id)
    return render(request, 'compras/fulfillment_confirm.html', {'reservation': reservation})


@staff_member_required
@transaction.atomic
def confirm_pickup(request, reservation_id):
    reservation = get_object_or_404(Reservation, id=reservation_id, status='PENDING')
    
    if request.method == 'POST':
        user_pin = request.POST.get('pickup_pin')
        
        # Rigor SOTARQ: Validação binária de segurança
        if user_pin != reservation.pickup_pin:
            messages.error(request, "🛡️ SEGURANÇA: PIN INVÁLIDO. Acesso ao item bloqueado.")
            return redirect('compras:fulfillment_scan', reservation_id=reservation_id)
        
        reservation.status = 'COMPLETED'
        reservation.save()
        
        # Disparo SOTARQ MESSENGER (WhatsApp automático ao Encarregado)
        self._notify_guardian_pickup(reservation)
        
        messages.success(request, "Entrega validada com sucesso.")
        return redirect('compras:generate_receipt', reservation_id=reservation.id)

def generate_delivery_receipt(request, reservation_id):
    """
    Gera o PDF do Recibo de Entrega para arquivo ou entrega ao pai.
    """
    res = get_object_or_404(Reservation, id=reservation_id)
    buffer = BytesIO()
    p = canvas.Canvas(buffer)
    
    # Design do Recibo (Simples e Profissional)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(100, 800, f"RECIBO DE ENTREGA DE ARTIGOS #{res.id}")
    p.setFont("Helvetica", 12)
    p.drawString(100, 780, f"Instituição: {request.tenant.name}")
    p.drawString(100, 750, f"Estudante: {res.student.full_name}")
    p.drawString(100, 730, f"Artigo: {res.variant.product.name}")
    p.drawString(100, 710, f"Variante/Tamanho: {res.variant.size}")
    p.drawString(100, 690, f"Data de Entrega: {res.modified_at.strftime('%d/%m/%Y %H:%M')}")
    
    p.line(100, 650, 500, 650)
    p.drawString(100, 635, "Assinatura do Recebedor")
    
    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recibo_entrega_{res.id}.pdf"'
    return response


