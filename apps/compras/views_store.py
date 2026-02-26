# apps/compras/views_story.py
from django.db import transaction
from apps.cafeteria.services import WalletService
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A6 # Recibos de loja costumam ser menores
from io import BytesIO

from apps.students.models import Student
from .models import Product, SchoolStoreSale, SchoolStoreSaleItem


@transaction.atomic
def process_store_sale(request):
    if request.method == 'POST':
        data = request.POST
        student = Student.objects.get(id=data['student_id'])
        payment_method = data['payment_method']
        
        # 1. Criar a Venda
        sale = SchoolStoreSale.objects.create(
            student=student,
            payment_method=payment_method,
            seller=request.user
        )

        total_sale = 0
        # 2. Processar Itens e Baixa de Stock
        for item_data in data.getlist('items'):
            product = Product.objects.get(id=item_data['id'])
            qty = int(item_data['qty'])
            
            SchoolStoreSaleItem.objects.create(
                sale=sale, product=product, quantity=qty, unit_price=product.sale_price
            )
            
            # Baixa de Stock Real-time
            product.stock_quantity -= qty
            product.save()
            total_sale += product.sale_price * qty

        sale.total_amount = total_sale

        # 3. Lógica de Pagamento Flexível
        if payment_method == 'WALLET':
            success, msg = WalletService.process_purchase(
                student, total_sale, f"Compra Loja Escolar: {sale.id}"
            )
            if not success:
                transaction.set_rollback(True) # Cancela venda se wallet falhar
                return JsonResponse({'error': msg}, status=400)
            sale.is_paid = True
        else:
            # Pagamento externo (Cash/TPA)
            sale.is_paid = True # Assume-se pago no acto da entrega física
        
        sale.save()
        return redirect('compras:receipt', sale_id=sale.id)


@login_required
def receipt_view(request, sale_id):
    """
    Gera o PDF do Recibo de Venda da Loja Escolar.
    Otimizado para impressoras térmicas ou A6.
    """
    sale = get_object_or_404(SchoolStoreSale, id=sale_id)
    buffer = BytesIO()
    
    # Criar o PDF no tamanho A6 (ideal para recibos de balcão)
    p = canvas.Canvas(buffer, pagesize=A6)
    width, height = A6

    # Cabeçalho
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width/2, height - 30, f"{request.tenant.name}")
    p.setFont("Helvetica", 8)
    p.drawCentredString(width/2, height - 45, "RECIBO DE VENDA - LOJA ESCOLAR")
    p.line(20, height - 55, width - 20, height - 55)

    # Info da Venda
    p.setFont("Helvetica-Bold", 9)
    p.drawString(20, height - 75, f"Venda: #{sale.id}")
    p.setFont("Helvetica", 9)
    p.drawString(20, height - 88, f"Data: {sale.created_at.strftime('%d/%m/%Y %H:%M')}")
    p.drawString(20, height - 101, f"Estudante: {sale.student.full_name}")
    p.drawString(20, height - 114, f"Pagamento: {sale.get_payment_method_display()}")

    p.line(20, height - 125, width - 20, height - 125)

    # Cabeçalho da Tabela de Itens
    p.setFont("Helvetica-Bold", 8)
    p.drawString(20, height - 140, "ARTIGO")
    p.drawRightString(width - 60, height - 140, "QTD")
    p.drawRightString(width - 20, height - 140, "SUBTOTAL")

    # Itens
    y = height - 155
    p.setFont("Helvetica", 8)
    for item in sale.items.all():
        p.drawString(20, y, f"{item.product.name[:20]}")
        p.drawRightString(width - 60, y, f"{item.quantity}")
        p.drawRightString(width - 20, y, f"{item.unit_price * item.quantity:,.2f}")
        y -= 12
        if y < 50: # Evitar sair da página
            p.showPage()
            y = height - 30

    # Total
    p.line(20, y - 5, width - 20, y - 5)
    p.setFont("Helvetica-Bold", 11)
    p.drawString(20, y - 20, "TOTAL")
    p.drawRightString(width - 20, y - 20, f"{sale.total_amount:,.2f} Kz")

    # Rodapé
    p.setFont("Helvetica-Oblique", 7)
    p.drawCentredString(width/2, 30, "Obrigado pela sua preferência.")
    p.drawCentredString(width/2, 20, f"Processado por: {sale.seller.username}")

    p.showPage()
    p.save()

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="recibo_loja_{sale.id}.pdf"'
    return response

