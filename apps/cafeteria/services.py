from django.db import transaction, models
from django.utils import timezone
from datetime import timedelta
from decimal import Decimal
from .models import Wallet, Transaction, Product, StockMovement, ProductRestriction

class WalletService:
    @staticmethod
    @transaction.atomic
    def process_purchase(student, product_id):
        product = Product.objects.get(id=product_id)
        wallet = student.wallet
        today = timezone.now().date()
        
        # 1. VALIDAÇÃO DE BLOQUEIO SELETIVO (Rigor Parental)
        restriction = ProductRestriction.objects.filter(student=student, product=product).first()
        if restriction:
            msg = f"VENDA BLOQUEADA: {product.name} não permitido."
            if restriction.substitute_product:
                msg += f" SUGESTÃO: Oferecer {restriction.substitute_product.name}."
            return False, msg

        # 2. CALCULAR GASTO DIÁRIO
        today_spent = Transaction.objects.filter(
            wallet=wallet,
            transaction_type='PURCHASE',
            created_at__date=today
        ).aggregate(total=models.Sum('amount'))['total'] or Decimal('0.00')

        # 3. VALIDAÇÕES DE SALDO E LIMITE
        if product.price > wallet.balance:
            return False, "Saldo insuficiente na carteira digital."
        
        if (today_spent + product.price) > wallet.daily_limit:
            return False, f"Limite diário excedido. Restante: {wallet.daily_limit - today_spent} Kz."

        # 4. EXECUÇÃO
        wallet.balance -= product.price
        wallet.save()
        
        Transaction.objects.create(
            wallet=wallet,
            amount=product.price,
            transaction_type='PURCHASE',
            description=product.name
        )
        return True, "Venda realizada com sucesso."

class CafeteriaInventoryService:
    @staticmethod
    def get_total_cost():
        """
        SOLUÇÃO DO ERRO: Calcula o valor total do inventário (Custo).
        Rigor SOTARQ: Soma (Stock Atual * Preço de Custo).
        """
        # Nota: Verifique se o campo no seu modelo é 'cost_price' ou 'purchase_price'
        result = Product.objects.filter(is_active=True).aggregate(
            total=models.Sum(models.F('current_stock') * models.F('cost_price'))
        )
        return result['total'] or Decimal('0.00')

    @staticmethod
    @transaction.atomic
    def add_stock(product_id, quantity, user, reason="Compra de Fornecedor"):
        product = Product.objects.get(id=product_id)
        product.current_stock += quantity
        product.save()
        
        StockMovement.objects.create(
            product=product,
            quantity=quantity,
            movement_type='IN',
            reason=reason,
            performed_by=user
        )

    @staticmethod
    def check_stock_alerts():
        """Alerta de ruptura de stock."""
        return Product.objects.filter(current_stock__lte=models.F('min_stock_level'), is_active=True)

class NutritionalService:
    @staticmethod
    def get_weekly_summary(student):
        last_week = timezone.now() - timedelta(days=7)
        transactions = Transaction.objects.filter(
            wallet__student=student,
            transaction_type='PURCHASE',
            created_at__gte=last_week
        )
        total_spent = sum(t.amount for t in transactions)
        summary = transactions.values('description').annotate(total=models.Count('id')).order_by('-total')
        
        return {
            'total_spent': total_spent,
            'items': summary,
            'count': transactions.count()
        }