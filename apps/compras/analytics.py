# apps/compras/analytics.py
from django.db.models import Sum, F
from django.utils import timezone
from datetime import timedelta

class InventoryIntelligence:
    @staticmethod
    def calculate_stock_out_prediction(product):
        """
        Rigor SOTARQ: Predição de Ruptura baseada em VMD (Velocidade Média Diária).
        """
        last_30_days = timezone.now() - timedelta(days=30)
        
        # Filtra saídas reais (Vendas na Loja e Consumo Interno)
        total_sold = product.movements.filter(
            movement_type='OUT', 
            created_at__gte=last_30_days
        ).aggregate(Sum('quantity'))['quantity__sum'] or 0

        if total_sold <= 0:
            return None 

        vmd = total_sold / 30
        days_of_cover = int(product.stock_quantity / vmd)

        return {
            'vmd': round(vmd, 2),
            'days_of_cover': days_of_cover,
            'predicted_date': timezone.now().date() + timedelta(days=days_of_cover),
            'is_critical': days_of_cover <= 7 # Alerta vermelho se durar menos de uma semana
        }

