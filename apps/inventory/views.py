# apps/inventory/views.py
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Asset
from .services import AssetManager
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required




@login_required
def asset_qr_detail(request, asset_id):
    """View acessada ao ler o QR Code físico no ativo."""
    asset = get_object_or_404(Asset, id=asset_id)
    return render(request, 'inventory/asset_detail.html', {'asset': asset})

@login_required
def inventory_dashboard(request):
    """Painel financeiro do património escolar."""
    valuation = AssetManager.get_patrimony_valuation()
    assets = Asset.objects.all().order_by('-purchase_date')
    
    context = {
        'valuation': valuation,
        'assets': assets,
    }
    return render(request, 'inventory/dashboard.html', context)


@login_required
def asset_qr_detail(request, asset_id):
    """
    Interface de auditoria rápida via QR Code.
    """
    asset = get_object_or_404(Asset, id=asset_id)
    
    # Calculamos os valores na hora para garantir precisão
    current_value = asset.calculate_current_value()
    total_depreciated = asset.purchase_price - current_value
    
    context = {
        'asset': asset,
        'current_value': current_value,
        'total_depreciated': total_depreciated,
    }
    return render(request, 'inventory/asset_qr_detail.html', context)

