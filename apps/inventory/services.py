# apps/inventory/services.py
from .models import Asset

class AssetManager:
    @staticmethod
    def get_patrimony_valuation():
        assets = Asset.objects.all()
        total_purchase = sum(a.purchase_price for a in assets)
        total_current = sum(a.calculate_current_value() for a in assets)
        
        return {
            'purchase_value': total_purchase,
            'current_value': total_current,
            'total_depreciation': total_purchase - total_current
        }

