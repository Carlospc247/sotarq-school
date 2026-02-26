# apps/inventory/models.py
from django.db import models
from apps.core.models import BaseModel
from decimal import Decimal
from django.utils import timezone
import qrcode
from io import BytesIO
from django.core.files import File

class AssetCategory(BaseModel):
    name = models.CharField(max_length=100) # Ex: Informática, Mobiliário, Climatização
    depreciation_years = models.PositiveIntegerField(help_text="Vida útil em anos")

    def __str__(self):
        return self.name


class Asset(BaseModel):
    # Identidade e Unidade
    name = models.CharField(max_length=255)
    category = models.ForeignKey(AssetCategory, on_delete=models.PROTECT)
    unit = models.CharField(max_length=20, default='UN', verbose_name="Unidade de Medida", help_text="Ex: UN, KG, LT, CX") # Vinculado à unidade escolar

    # Dados de Compra e Fiscalidade
    purchase_date = models.DateField()
    purchase_price = models.DecimalField(max_digits=12, decimal_places=2)
    residual_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    serial_number = models.CharField(max_length=100, unique=True, blank=True, null=True)
    qr_code = models.ImageField(upload_to='inventory/qrcodes/', blank=True, null=True)

    def calculate_current_value(self):
        """Calcula o valor depreciado linearmente para o balanço patrimonial."""
        if not self.purchase_date or not self.category.depreciation_years:
            return self.purchase_price
        
        years_old = (timezone.now().date() - self.purchase_date).days / 365.25
        annual_depreciation = (self.purchase_price - self.residual_value) / self.category.depreciation_years
        
        current_value = self.purchase_price - (Decimal(years_old) * annual_depreciation)
        return max(current_value, self.residual_value)

    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs)
        if is_new:
            self.generate_qr_code()
            super().save(update_fields=['qr_code'])


