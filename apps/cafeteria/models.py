# apps/cafeteria/models.py
from django.conf import settings
from django.db import models
from apps.core.models import BaseModel
from decimal import Decimal

# 1. ESCOLHAS NO TOPO (Para evitar NameError)
class HealthGrade(models.TextChoices):
    GREEN = 'GREEN', 'Saudável (Consumo Livre)'
    YELLOW = 'YELLOW', 'Moderado'
    RED = 'RED', 'Restrito (Açúcares/Gorduras)'

class TransactionType(models.TextChoices):
    RELOAD = 'RELOAD', 'Carregamento'
    PURCHASE = 'PURCHASE', 'Compra'
    REFUND = 'REFUND', 'Reembolso'

class MovementType(models.TextChoices):
    IN = 'IN', 'Entrada (Compra/Reposição)'
    OUT = 'OUT', 'Saída (Venda)'
    ADJUST = 'ADJUST', 'Ajuste (Quebra/Validade)'

# 2. MODELOS
class Wallet(BaseModel):
    student = models.OneToOneField('students.Student', on_delete=models.CASCADE, related_name='wallet')
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    daily_limit = models.DecimalField(max_digits=10, decimal_places=2, default=2000.00) 
    
    def __str__(self):
        return f"Carteira: {self.student.full_name} | Saldo: {self.balance} Kz"

class Transaction(BaseModel):
    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE, related_name='transactions')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    transaction_type = models.CharField(max_length=10, choices=TransactionType.choices)
    description = models.CharField(max_length=255)

    class Meta:
        ordering = ['-created_at']

class Product(BaseModel):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.CharField(max_length=50, choices=HealthGrade.choices, default=HealthGrade.GREEN)
    current_stock = models.PositiveIntegerField(default=0, verbose_name="Stock Actual")
    min_stock_level = models.PositiveIntegerField(default=10, verbose_name="Stock Mínimo")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2)
    sku = models.CharField(max_length=50, unique=True)
    is_active = models.BooleanField(default=True)

    @property
    def needs_restock(self):
        return self.current_stock <= self.min_stock_level

    def __str__(self):
        return f"{self.name} ({self.current_stock} un)"

class StockMovement(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='movements')
    quantity = models.IntegerField()
    movement_type = models.CharField(max_length=10, choices=MovementType.choices)
    reason = models.CharField(max_length=255, blank=True)
    performed_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)

class ProductRestriction(BaseModel):
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='product_restrictions')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    substitute_product = models.ForeignKey(
        Product, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, 
        related_name='suggested_as_substitute'
    )
    reason = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = ('student', 'product')

# apps/cafeteria/models.py
from django.db import models
from apps.core.models import BaseModel
from decimal import Decimal

class ExternalClient(BaseModel):
    """Rigor SOTARQ: Cadastro para Professores, Funcionários e Visitantes."""
    TYPE_CHOICES = [('STAFF', 'Funcionário/Professor'), ('VISITOR', 'Visitante/Outro')]
    name = models.CharField(max_length=255)
    tax_id = models.CharField(max_length=20, default='9999999999', verbose_name="NIF")
    client_type = models.CharField(max_length=10, choices=TYPE_CHOICES)
    phone = models.CharField(max_length=20, blank=True)
    balance = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)

    def __str__(self):
        return f"{self.name} ({self.get_client_type_display()})"

class CafeteriaSale(BaseModel):
    """O Documento Comercial da Venda."""
    PAYMENT_METHODS = [('WALLET', 'Carteira'), ('CASH', 'Cash'), ('MULTICAIXA', 'TPA')]
    
    # Suporte Híbrido: Aluno ou Externo
    student = models.ForeignKey('students.Student', on_delete=models.SET_NULL, null=True, blank=True)
    external_client = models.ForeignKey(ExternalClient, on_delete=models.SET_NULL, null=True, blank=True)
    
    session = models.ForeignKey('finance.CashSession', on_delete=models.PROTECT, related_name='sales')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS)
    
    # Rigor Fiscal AGT
    subtotal = models.DecimalField(max_digits=15, decimal_places=2)
    tax_rate = models.ForeignKey('fiscal.TaxaIVAAGT', on_delete=models.PROTECT)
    tax_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    
    # Rigor de Autorização
    discount_amount = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    authorized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    
    total_final = models.DecimalField(max_digits=15, decimal_places=2)
    fiscal_doc = models.OneToOneField('fiscal.DocumentoFiscal', on_delete=models.SET_NULL, null=True, blank=True)


