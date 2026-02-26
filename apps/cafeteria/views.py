# apps/cafeteria/views.py
from datetime import timezone
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db import transaction
from apps.finance.models import CashSession
from apps.fiscal.models import TaxaIVAAGT
from .models import Product, Wallet, ProductRestriction
from .services import WalletService, CafeteriaInventoryService
from apps.students.models import Student
from django.db.models import Sum, F
from .models import Product, ExternalClient


@login_required
def pos_checkout(request):
    """
    Interface de Venda da Cantina (PDV).
    O funcionário faz o scan do produto e identifica o aluno.
    """
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        product_id = request.POST.get('product_id')
        
        student = get_object_or_404(Student, id=student_id)
        
        # Executa o Motor de Venda (Valida saldo, limite e restrições)
        success, message = WalletService.process_purchase(student, product_id)
        
        if success:
            messages.success(request, message)
        else:
            messages.error(request, message)
            
        return redirect('cafeteria:pos_checkout')

    products = Product.objects.filter(is_active=True, current_stock__gt=0)
    return render(request, 'cafeteria/pos_checkout.html', {'products': products})

@login_required
def update_daily_limit(request):
    """
    Actualiza o limite diário de gastos (Usado pelo Encarregado).
    """
    if request.method == 'POST':
        wallet_id = request.POST.get('wallet_id')
        new_limit = request.POST.get('daily_limit')
        
        wallet = get_object_or_404(Wallet, id=wallet_id, student__guardians__guardian__user=request.user)
        wallet.daily_limit = new_limit
        wallet.save()
        
        messages.success(request, "Limite diário actualizado com sucesso.")
    return redirect('portal:dashboard')

@login_required
def toggle_product_restriction(request):
    """
    Endpoint HTMX/AJAX para bloquear ou desbloquear um produto.
    """
    product_id = request.POST.get('product_id')
    student_id = request.POST.get('student_id')
    
    restriction, created = ProductRestriction.objects.get_or_create(
        student_id=student_id,
        product_id=product_id
    )
    
    if not created:
        restriction.delete()
        status = "unblocked"
    else:
        status = "blocked"
        
    return JsonResponse({'status': status})

# Endpoint de busca rápida de alunos

@login_required
def search_student(request):
    """Busca rápida por nome ou número de matrícula para o PDV."""
    query = request.GET.get('q', '')
    students = Student.objects.filter(full_name__icontains=query)[:5]
    results = [{'id': s.id, 'name': s.full_name} for s in students]
    return JsonResponse(results, safe=False)


# apps/cafeteria/views.py
from decimal import Decimal

@login_required
@transaction.atomic
def pos_checkout(request):
    """Interface de Venda com Aprovisionamento de IVA e Descontos."""
    session = CashSession.objects.filter(user=request.user, status='open').first()
    if not session:
        messages.error(request, "🛡️ CAIXA FECHADO: Abra uma sessão antes de vender.")
        return redirect('cafeteria:cash_dashboard')

    if request.method == 'POST':
        discount = Decimal(request.POST.get('discount_value', '0'))
        tax_id = request.POST.get('tax_id')
        
        # Rigor SOTARQ: Validação de Permissão para Descontos
        if discount > 0 and not request.user.current_role in ['ADMIN', 'DIRECTOR']:
            messages.error(request, "ACESSO NEGADO: Apenas Administradores podem autorizar descontos.")
            return redirect('cafeteria:pos_checkout')

        # Lógica de emissão de Documento Fiscal (VD ou FR conforme AGT)
        # ... processamento de itens ...
        
    return render(request, 'cafeteria/pos_checkout.html', {
        'session': session,
        'taxes': TaxaIVAAGT.objects.filter(ativo=True),
        'products': Product.objects.filter(is_active=True, current_stock__gt=0)
    })


@login_required
def inventory_list(request):
    """
    Rigor SOTARQ: Gestão de Stock e Valorização.
    Filtra produtos ativos do Tenant e calcula valor total de prateleira.
    """
    products = Product.objects.filter(
        is_active=True
    ).order_by('category', 'name')
    
    # Cálculo de Capital Imobilizado (Preço Custo * Quantidade)
    total_stock_value = sum(p.current_stock * p.cost_price for p in products)
    
    context = {
        'products': products,
        'total_stock_value': total_stock_value,
        'critical_count': products.filter(current_stock__lte=F('min_stock_level')).count()
    }
    return render(request, 'cafeteria/inventory_list.html', context)



from apps.students.models import Student

@login_required
def client_manager(request):
    """
    Motor de Sincronização de Clientes.
    Unifica a base académica com a base de staff/visitantes.
    """
    # Alunos ativos do Tenant (Clientes Automáticos)
    students = Student.objects.filter(
        user__tenant=request.user.tenant, 
        is_active=True
    ).select_related('wallet')

    # Clientes Externos (Staff e Visitantes)
    external_clients = ExternalClient.objects.all().order_by('name')

    context = {
        'students': students,
        'external_clients': external_clients,
    }
    return render(request, 'cafeteria/client_manager.html', context)


@login_required
def sessions_history(request):
    """
    Rigor de Auditoria: Histórico de Abertura e Fecho.
    Exibe divergências financeiras e logs de fechamento.
    """
    # Apenas Admin e Diretor vêem o histórico de todos. Operadores vêm o seu.
    if request.user.current_role in ['ADMIN', 'DIRECTOR']:
        sessions = CashSession.objects.all()
    else:
        sessions = CashSession.objects.filter(user=request.user)

    sessions = sessions.order_by('-opened_at')

    # KPI: Soma de todas as faltas de caixa no mês atual
    total_discrepancies = sessions.filter(
        status='closed', 
        closed_at__month=timezone.now().month
    ).aggregate(total=Sum('difference'))['total'] or 0

    context = {
        'sessions': sessions,
        'total_discrepancies': total_discrepancies,
    }
    return render(request, 'cafeteria/sessions_history.html', context)



