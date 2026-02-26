# apps/accounts/views.py
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from .models import FinancialAccount, AccountSetting
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect
from django.contrib import messages
from .models import FinancialAccount
from apps.audit.models import AuditLog
from django.contrib.contenttypes.models import ContentType



@login_required
@user_passes_test(lambda u: u.is_staff) # Apenas funcionários autorizados
def account_list(request):
    """Exibe o saldo de todas as contas do livro razão."""
    accounts = FinancialAccount.objects.all().order_by('code')
    total_balance = sum(acc.balance for acc in accounts)
    
    return render(request, 'accounts/ledger_list.html', {
        'accounts': accounts,
        'total_balance': total_balance
    })

@login_required
@user_passes_test(lambda u: u.is_superuser) # Configurações críticas apenas para o Admin
def settings_dashboard(request):
    """Interface para ligar/desligar funcionalidades da escola."""
    settings = AccountSetting.objects.all()
    return render(request, 'accounts/settings_dashboard.html', {'settings': settings})



@transaction.atomic
def transfer_funds(request):
    if request.method == 'POST':
        from_id = request.POST.get('from_account')
        to_id = request.POST.get('to_account')
        amount = Decimal(request.POST.get('amount', 0))

        if from_id == to_id:
            messages.error(request, "A conta de origem e destino não podem ser iguais.")
            return redirect('accounts:ledger_list')

        # Bloqueia as linhas no banco de dados para evitar "Race Conditions"
        source = get_object_or_404(FinancialAccount.objects.select_for_update(), id=from_id)
        destination = get_object_or_404(FinancialAccount.objects.select_for_update(), id=to_id)

        if source.balance < amount:
            messages.error(request, f"Saldo insuficiente na conta {source.name}.")
        else:
            # 1. Movimentação de Valores
            source.balance -= amount
            destination.balance += amount
            source.save()
            destination.save()

            # 2. Registro Manual na Auditoria (Contexto Rico)
            AuditLog.objects.create(
                user=request.user,
                action='TRANSFER',
                content_type=ContentType.objects.get_for_model(source),
                object_id=source.id,
                details={
                    'from': source.name,
                    'to': destination.name,
                    'amount': str(amount),
                    'currency': 'AOA'
                }
            )
            messages.success(request, f"Transferência de {amount} Kz concluída com sucesso!")

    return redirect('accounts:ledger_list')





@login_required
@user_passes_test(lambda u: u.is_superuser)
def update_setting(request):
    """Atualiza dinamicamente as configurações de sistema do Tenant."""
    if request.method == 'POST':
        key = request.POST.get('key')
        value = request.POST.get('value')
        
        setting = get_object_or_404(AccountSetting, key=key)
        setting.value = value
        setting.save()
        
        messages.success(request, f"Configuração '{key}' atualizada com sucesso.")
    return redirect('accounts:settings_dashboard')


