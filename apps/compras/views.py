# apps/compras/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.contrib import messages
from .models import Product, Purchase
from .forms import PurchaseForm, PurchaseItemFormSet
from apps.core.utils import get_client_ip
from .forms import StockWasteForm



@login_required
def stock_dashboard(request):
    """Painel geral do armazém com alertas visuais"""
    # Usamos select_related para carregar a categoria numa única query
    products = Product.objects.select_related('category').all().order_by('category', 'name')
    
    # KPIs Rápidos para o Diretor
    total_value = sum(p.stock_quantity * p.cost_price for p in products)
    critical_items = products.filter(stock_quantity__lte=models.F('min_stock_alert')).count()

    context = {
        'products': products,
        'total_value': total_value,
        'critical_items': critical_items,
    }
    return render(request, 'compras/dashboard.html', context)


@login_required
def create_purchase(request):
    """Registar nova entrada de mercadoria"""
    if request.method == 'POST':
        form = PurchaseForm(request.POST)
        formset = PurchaseItemFormSet(request.POST)
        
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                purchase = form.save(commit=False)
                purchase.registered_by = request.user
                purchase.status = 'draft' # Entra sempre como rascunho primeiro
                purchase.save()
                
                items = formset.save(commit=False)
                for item in items:
                    item.purchase = purchase
                    item.save()
                
                # Opcional: Confirmar stock imediatamente ou deixar para um botão "Aprovar"
                # Aqui vamos confirmar direto para agilizar o teste
                purchase.confirm_stock()
                
                messages.success(request, f"Compra {purchase.invoice_ref} registada e stock atualizado!")
                return redirect('stock_dashboard')
    else:
        form = PurchaseForm()
        formset = PurchaseItemFormSet()

    return render(request, 'compras/purchase_form.html', {
        'form': form,
        'formset': formset
    })




@login_required
@transaction.atomic
def register_waste(request):
    """
    Interface de Auditoria de Quebras via Django Forms.
    Rigor: Validação de ficheiro e integridade de stock.
    """
    if request.method == 'POST':
        form = StockWasteForm(request.POST, request.FILES)
        if form.is_valid():
            waste = form.save(commit=False)
            waste.operator = request.user
            waste.ip_address = get_client_ip(request)
            
            # Verificação de stock antes de salvar
            if waste.product.stock_quantity < waste.quantity:
                messages.error(request, f"Erro: Stock insuficiente para baixar {waste.quantity} unidades.")
                return render(request, 'compras/waste_form.html', {'form': form})
            
            waste.save() # O método save do modelo já cuida da baixa de stock
            messages.warning(request, "Quebra registada e evidência arquivada com sucesso.")
            return redirect('compras:stock_dashboard')
    else:
        form = StockWasteForm()
    
    return render(request, 'compras/waste_form.html', {'form': form})


