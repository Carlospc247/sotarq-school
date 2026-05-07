# apps/fiscal/models.py
import logging
from decimal import Decimal
from django.db import models
from django.utils import timezone  # <--- ESTE É O ÚNICO QUE DEVE TER .now(
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from apps.core.models import BaseModel
from .signing import FiscalSigner
from django.utils.translation import gettext_lazy as _



logger = logging.getLogger(__name__)

# 1. Configuração Fiscal
class FiscalConfig(BaseModel):
    saft_generation_day = models.PositiveIntegerField(default=15, validators=[MinValueValidator(1), MaxValueValidator(28)])
    auto_submit_agt = models.BooleanField(default=False)
    email_notification = models.EmailField(blank=True)

    def __str__(self):
        return f"Config Fiscal (Dia {self.saft_generation_day})"

# 2. Taxas de IVA (Tabela Fixa AGT)
class TaxaIVAAGT(BaseModel):
    TAX_TYPE = [('IVA', 'IVA'), ('IS', 'Isenção'), ('NS', 'Não Sujeição')]
    TAX_CODE = [('NOR', 'Normal'), ('INT', 'Intercalar'), ('RED', 'Reduzida'), ('ISE', 'Isento'), ('NSU', 'Não Sujeito')]
    
    nome = models.CharField(max_length=100)
    tax_type = models.CharField(max_length=3, choices=TAX_TYPE)
    tax_code = models.CharField(max_length=3, choices=TAX_CODE)
    tax_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    exemption_reason = models.CharField(max_length=10, blank=True, null=True) # Ex: M02
    ativo = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Taxa de IVA (AGT)"

    def __str__(self):
        return f"{self.tax_code} - {self.tax_percentage}%"

# 3. Cofre de Chaves da ESCOLA (Assinatura de Documentos)
class AssinaturaDigital(BaseModel):
    descricao = models.CharField(max_length=100, default="Chaves AGT 2026")
    
    # Chave Privada da Escola (Encriptada/Segura) - Usada para assinar a Fatura
    chave_privada_pem = models.TextField(help_text="Chave privada RSA para assinatura de faturas.")
    chave_publica_pem = models.TextField(help_text="Chave pública para validação.")
    
    ativa = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Cofre Digital da Escola"

    def get_private_key(self):
        return self.chave_privada_pem.encode('utf-8')

# 4. Série Fiscal
class SerieFiscal(BaseModel):
    """Controla as séries aprovadas pela AGT (Ex: FT 2026)"""
    codigo = models.CharField(max_length=50)
    ano = models.IntegerField()
    codigo_validacao_agt = models.CharField(max_length=50, blank=True)
    tipo_documento = models.CharField(max_length=10) # FT, FR, etc
    ultimo_numero = models.PositiveIntegerField(default=0)
    status = models.CharField(max_length=20, default='PENDING') # PENDING, ATIVA

    def __str__(self):
        return f"{self.codigo} ({self.ano})"
    
    class Meta:
        # Garante que não existam dois registros com o mesmo TIPO, ANO e TENANT
        constraints = [
            models.UniqueConstraint(
                fields=['tipo_documento', 'ano', 'tenant'], 
                name='unique_serie_tipo_ano_tenant'
            )
        ]
        verbose_name = "Série Fiscal"
        verbose_name_plural = "Séries Fiscais"


class DocType(models.TextChoices):
        FT = 'FT', _('Fatura')
        FR = 'FR', _('Fatura-Recibo')
        FP = 'FP', _('Fatura Proforma')
        NC = 'NC', _('Nota de Crédito')
        RC = 'RC', _('Recibo')


# 5. Documento Fiscal (A Fatura Real)
class DocumentoFiscal(BaseModel):
   
    
    class Status(models.TextChoices):
        DRAFT = 'draft', _('Rascunho')
        CONFIRMED = 'confirmed', _('Confirmado')
        CANCELLED = 'cancelled', _('Anulado')

    # Configuração de Campos com Rigor AGT
    tipo_documento = models.CharField(
        max_length=3, 
        choices=DocType.choices, 
        default=DocType.FT
    )
    status = models.CharField(
        max_length=20, 
        choices=Status.choices, 
        default=Status.DRAFT
    )
    
    # No Model DocumentoFiscal
    serie = models.ForeignKey(SerieFiscal, on_delete=models.PROTECT, related_name='documentos')
    serie_codigo = models.CharField(max_length=50, editable=False)


    numero = models.PositiveIntegerField()
    numero_documento = models.CharField(max_length=50, unique=True, editable=False) # Ex: FT NEWAY2026/001
    
    # AGT Control & Compliance
    atcud = models.CharField(max_length=70, blank=True)
    agt_request_id = models.CharField(max_length=50, blank=True)
    agt_status = models.CharField(max_length=20, default='PENDING') # PENDING, VALID, ERROR
    agt_log = models.TextField(blank=True)

    # Dados Comerciais (Vínculo com o Aluno)
    cliente = models.ForeignKey(
        'students.Student', 
        on_delete=models.PROTECT, 
        null=True, 
        related_name='documentos_fiscais'
    )
    entidade_nome = models.CharField(max_length=200)
    entidade_nif = models.CharField(max_length=20, default='9999999999')
    data_emissao = models.DateField()
    
    # Valores Monetários (Rigor Decimal)
    valor_base = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_iva = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    valor_total = models.DecimalField(max_digits=15, decimal_places=2)
    
    # Segurança de Cadeia SHA1 (Decreto 292/18)
    hash_documento = models.CharField(max_length=256, blank=True)
    hash_anterior = models.CharField(max_length=256, blank=True)
    saft_hash = models.CharField(max_length=256, blank=True)
    
    periodo_tributacao = models.CharField(max_length=7) # YYYY-MM
    usuario_criacao = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    # Campo para o OriginatingON do SAF-T
    documento_origem = models.CharField(max_length=60, blank=True, null=True, help_text="Referência ao documento que originou este (Ex: FT SERIE/1)")


    def save(self, *args, **kwargs):
        # 1. RIGOR DE CACHE
        if not self.serie_codigo:
            self.serie_codigo = self.serie.codigo

        # 2. RIGOR SOTARQ: FR confirmada no ato
        if self.tipo_documento == DocType.FR:
            self.status = self.Status.CONFIRMED

        # 3. Lógica de Referência para Recibos
        if self.tipo_documento == 'RC' and not self.documento_origem:
            try:
                from apps.finance.models import Receipt
                receipt_comercial = Receipt.objects.filter(numero=self.numero_documento).first()
                if receipt_comercial and receipt_comercial.payment.invoice.fiscal_doc:
                    self.documento_origem = receipt_comercial.payment.invoice.fiscal_doc.numero_documento
            except Exception as e:
                print(f"Aviso SOTARQ: Erro no rastreio do RC: {e}")

        # 4. GERAÇÃO DE NÚMERO E HASH
        if not self.numero_documento and self.numero:
            self.numero_documento = f"{self.tipo_documento} {self.serie_codigo}/{self.numero}"

        if self.status == self.Status.CONFIRMED and not self.hash_documento:
            self._generate_sha1_hash()
        
        # 5. COMPLIANCE ATCUD
        if not self.atcud and self.serie.codigo_validacao_agt:
            self.atcud = f"{self.serie.codigo_validacao_agt}-{self.numero}"
            
        super().save(*args, **kwargs)

    # RECUO DE EXATAMENTE 4 ESPAÇOS PARA O MÉTODO
    def _generate_sha1_hash(self):
        """Implementação da Assinatura em Cadeia SOTARQ usando a FK."""
        last_doc = DocumentoFiscal.objects.filter(
            serie=self.serie,
            tipo_documento=self.tipo_documento,
            status=self.Status.CONFIRMED
        ).exclude(id=self.id).order_by('-numero').first()

        self.hash_anterior = last_doc.hash_documento if last_doc else ""
        
        # O RIGOR ESTÁ AQUI: Alinhamento preciso
        signer = FiscalSigner()
        self.hash_documento = signer.sign(
            invoice_date=self.data_emissao,
            system_entry_date=self.created_at or timezone.now(),
            doc_number=self.numero_documento,
            gross_total=float(self.valor_total),
            previous_hash=self.hash_anterior
        )
        self.saft_hash = self.hash_documento

    class Meta:
        ordering = ['-data_emissao', '-numero']
        indexes = [
            models.Index(fields=['atcud']), 
            models.Index(fields=['hash_documento']),
            models.Index(fields=['periodo_tributacao']),
        ]

    def __str__(self):
        return self.numero_documento


# 6. Linhas do Documento
class DocumentoFiscalLinha(models.Model):
    documento = models.ForeignKey(DocumentoFiscal, related_name='linhas', on_delete=models.CASCADE)
    descricao = models.CharField(max_length=200)
    quantidade = models.DecimalField(max_digits=10, decimal_places=2)
    preco_unitario = models.DecimalField(max_digits=12, decimal_places=2)
    taxa_iva = models.ForeignKey(TaxaIVAAGT, on_delete=models.PROTECT)
    valor_total_linha = models.DecimalField(max_digits=12, decimal_places=2)
    valor_iva_linha = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    numero_linha = models.PositiveIntegerField()

# 7. Registo de Exportação SAFT
class SAFTExport(BaseModel):
    periodo_tributacao = models.CharField(max_length=7)
    nome_arquivo = models.CharField(max_length=255)
    arquivo = models.FileField(upload_to='saft_xml/%Y/%m/')
    status = models.CharField(max_length=20, default='pending')
    log_erros = models.TextField(blank=True)

    sent_to_email = models.TextField(null=True, blank=True, help_text="Emails dos contabilistas que receberam")
    sent_at = models.DateTimeField(null=True, blank=True)
    dispatch_log = models.TextField(blank=True, help_text="Log técnico da transação SMTP")

    class Meta:
        verbose_name = "Exportação SAF-T"
        verbose_name_plural = "Exportações SAF-T"


class DocumentoCanceladoAudit(BaseModel):
    """
    Rigor SOTARQ: Rastreamento forense de anulações fiscais.
    """
    documento = models.OneToOneField('DocumentoFiscal', on_delete=models.CASCADE, related_name='anulacao_audit')
    operador = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    justificativa = models.TextField(verbose_name="Motivo Legal da Anulação")
    ip_address = models.GenericIPAddressField(verbose_name="Endereço IP do Terminal")
    user_agent = models.TextField(verbose_name="Dados do Navegador/Dispositivo")
    valor_estornado = models.DecimalField(max_digits=15, decimal_places=2)
    
    def __str__(self):
        return f"Anulação {self.documento.numero_documento} - {self.operador.username}"

class LogIntegracaoAGT(BaseModel):
    """
    Rigor SOTARQ: Caixa-preta de comunicação com a AGT.
    Armazena XMLs enviados e respostas para auditoria legal.
    """
    documento = models.ForeignKey('DocumentoFiscal', on_delete=models.CASCADE, null=True, blank=True, related_name='logs_agt')
    endpoint = models.URLField(help_text="URL da API da AGT acessada")
    xml_sent = models.TextField(verbose_name="XML Enviado", blank=True)
    response_received = models.TextField(verbose_name="Resposta da AGT", blank=True)
    status_code = models.IntegerField(null=True, blank=True) # Ex: 200, 403, 500
    sucesso = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "Log de Integração AGT"
        ordering = ['-created_at']

    def __str__(self):
        status = "SUCESSO" if self.sucesso else "FALHA"
        return f"Log AGT [{status}] - {self.created_at}"

