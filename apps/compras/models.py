# apps/compras/models.py
from django.db import models
from django.conf import settings
from apps.core.models import BaseModel
from decimal import Decimal
import random

# 1. Categoria de Produto (Ex: "Cantina", "Uniformes", "Livros")
class ProductCategory(BaseModel):
    name = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Product Categories"

    def __str__(self):
        return self.name

# 2. Fornecedor
class Supplier(BaseModel):
    name = models.CharField(max_length=200)
    nif = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    address = models.TextField(blank=True)
    
    def __str__(self):
        return self.name

# 3. Ficha de Produto (Stock)
class Product(BaseModel):
    TYPE_CHOICES = (
        ('P', 'Produto Físico'),
        ('S', 'Serviço'),
    )
    
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT)
    name = models.CharField(max_length=200)
    code = models.CharField(max_length=50, unique=True, help_text="Código de Barras ou SKU")
    product_type = models.CharField(max_length=1, choices=TYPE_CHOICES, default='P')
    
    # Gestão de Stock e Preços
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Custo Médio")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Preço de Venda ao Aluno")
    
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    min_stock_alert = models.DecimalField(max_digits=10, decimal_places=2, default=5, help_text="Alertar se baixar disto")
    
    is_saleable = models.BooleanField(default=True, help_text="Vende-se no POS?")

    def __str__(self):
        return f"{self.code} - {self.name}"
    
    
    @property
    def profit_margin(self):
        """Calcula a margem de lucro bruta."""
        if self.sale_price and self.cost_price:
            margin = ((self.sale_price - self.cost_price) / self.sale_price) * 100
            return round(margin, 2)
        return 0

    def update_stock_and_cost(self, new_quantity, new_unit_price):
        """
        Lógica de Custo Médio Ponderado (Enterprise Standard).
        Fórmula: (Stock Antigo * Custo Antigo + Novo Stock * Novo Custo) / Stock Total
        """
        total_quantity = self.stock_quantity + new_quantity
        if total_quantity > 0:
            # Novo custo médio
            self.cost_price = ((self.stock_quantity * self.cost_price) + 
                               (new_quantity * new_unit_price)) / total_quantity
            self.stock_quantity = total_quantity
            self.save()

# 4. Compra (Entrada de Stock)
class Purchase(BaseModel):
    STATUS_CHOICES = (
        ('draft', 'Rascunho'),
        ('confirmed', 'Confirmado (Stock Atualizado)'),
        ('cancelled', 'Anulado'),
    )
    
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT)
    date = models.DateField()
    invoice_ref = models.CharField(max_length=50, blank=True, help_text="Ref. da Fatura do Fornecedor")
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    registered_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def confirm_stock(self):
        """Atualiza o stock e o preço de custo médio"""
        if self.status != 'draft': return
        
        for item in self.items.all():
            prod = item.product
            if prod.product_type == 'P':
                # Atualiza quantidade
                prod.stock_quantity += item.quantity
                # Atualiza custo (simples: assume o último custo. Para avançado: usar média ponderada)
                prod.cost_price = item.unit_price
                prod.save()
        
        self.status = 'confirmed'
        self.save()

    def __str__(self):
        return f"Compra #{self.id} - {self.supplier.name}"

# 5. Itens da Compra
class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=12, decimal_places=2)

    def save(self, *args, **kwargs):
        self.total_price = self.quantity * self.unit_price
        super().save(*args, **kwargs)
        # Recalcula total da compra
        self.purchase.total_amount = sum(i.total_price for i in self.purchase.items.all())
        self.purchase.save()

class SchoolStoreSale(BaseModel):
    PAYMENT_METHODS = (
        ('WALLET', 'Carteira Digital'),
        ('CASH', 'Dinheiro / Cash'),
        ('MULTICAIXA', 'Referência Multicaixa / TPA'),
    )

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    is_paid = models.BooleanField(default=False)
    seller = models.ForeignKey('core.User', on_delete=models.PROTECT)

class SchoolStoreSaleItem(models.Model):
    sale = models.ForeignKey(SchoolStoreSale, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('compras.Product', on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)


class ProductVariant(BaseModel):
    product = models.ForeignKey('compras.Product', on_delete=models.CASCADE, related_name='variants')
    size = models.CharField(max_length=10, help_text="Ex: S, M, L, XL, 38, 40")
    color = models.CharField(max_length=50, blank=True, null=True)
    sku_variant = models.CharField(max_length=100, unique=True, help_text="SKU Específico da Variante")
    
    stock_quantity = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_override = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, help_text="Definir se o preço for diferente do produto pai")

    @property
    def current_price(self):
        return self.price_override if self.price_override else self.product.sale_price

    def __str__(self):
        return f"{self.product.name} - {self.size} ({self.color or 'N/A'})"

class Reservation(BaseModel):
    class Status(models.TextChoices):
        PENDING = 'PENDING', 'Aguardando Levantamento'
        COMPLETED = 'COMPLETED', 'Entregue'
        CANCELLED = 'CANCELLED', 'Cancelada/Expirada'

    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    variant = models.ForeignKey(ProductVariant, on_delete=models.PROTECT)
    quantity = models.PositiveIntegerField(default=1)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)
    expires_at = models.DateTimeField(help_text="Data limite para levantamento")
    pickup_pin = models.CharField(max_length=4, blank=True)

    def generate_pin(self):
        """Gera um PIN de 4 dígitos único para esta reserva."""
        self.pickup_pin = f"{random.randint(1000, 9999)}"
        self.save(update_fields=['pickup_pin'])

    # No save(), se for novo, gera o PIN
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.generate_pin()



class StockWaste(BaseModel):
    REASON_CHOICES = (
        ('DAMAGED', 'Danificado/Quebrado'),
        ('EXPIRED', 'Prazo de Validade Expirado'),
        ('THEFT', 'Furto/Roubo Identificado'),
        ('INTERNAL', 'Consumo Interno Autorizado'),
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='wastes')
    variant = models.ForeignKey(ProductVariant, on_delete=models.SET_NULL, null=True, blank=True)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=20, choices=REASON_CHOICES)
    
    # Evidência Forense
    photo_evidence = models.ImageField(upload_to='stock/wastes/%Y/%m/', help_text="Foto real do item danificado")
    description = models.TextField(verbose_name="Relatório Detalhado")
    
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    def save(self, *args, **kwargs):
        # Rigor SOTARQ: Baixa automática de stock ao registar quebra
        if not self.pk:
            target = self.variant if self.variant else self.product
            target.stock_quantity -= self.quantity
            target.save()
        super().save(*args, **kwargs)
    


