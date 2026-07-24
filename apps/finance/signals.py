# apps/finance/signals.py

from django.utils import timezone
from apps.core.utils import generate_document_number
from apps.documents.models import Document, DocumentType
from django.db import transaction
from django.dispatch import receiver
from .models import Invoice, Payment
from apps.core.models import Notification
from django.contrib.auth import get_user_model
from .models import Payment, DebtAgreement
from apps.fiscal.models import DocumentoFiscal, DocumentoFiscalLinha
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_save, post_save, pre_delete
from .models import Receipt, CashFlow
from django.core.files.base import ContentFile
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)





def sync_to_documents(invoice_instance):
    doc_type_obj, _ = DocumentType.objects.get_or_create(name=invoice_instance.get_doc_type_display())
    Document.objects.create(
        student=invoice_instance.student,
        document_type=doc_type_obj,
        # O ficheiro será gerado por uma task de PDF mais tarde
        file=None 
    )


User = get_user_model()

@receiver(post_save, sender=Payment)
def notify_secretariat_on_payment(sender, instance, created, **kwargs):
    if created and instance.proof_file:
        # Busca todos os utilizadores staff (secretaria/tesouraria)
        staff_users = User.objects.filter(is_staff=True)
        
        for user in staff_users:
            Notification.objects.create(
                user=user,
                title="Novo Comprovativo Recebido",
                message=f"O aluno {instance.invoice.student.full_name} enviou um comprovativo de {instance.amount} Kz.",
                link=f"/finance/treasury/dashboard/" # Link para a Dashboard que criamos
            )



@receiver(post_save, sender=Payment)
def trigger_agreement_activation(sender, instance, **kwargs):
    """
    RIGOR SOTARQ: Ativa o acordo de dívida se a primeira prestação for paga.
    Corrigido SyntaxError: Não repetimos o argumento no filter.
    """
    if instance.validation_status == 'validated':
        invoice = instance.invoice
        
        # Para buscar DUAS strings no mesmo campo, usamos Q objects ou encadeamos filtros
        from django.db.models import Q
        
        first_installment_item = invoice.items.filter(
            Q(description__icontains="Prestação 1/") & 
            Q(description__icontains="Acordo #")
        ).first()

        if first_installment_item:
            try:
                desc = first_installment_item.description
                # Extrair ID: "Acordo #123" -> ["Acordo ", "123"] -> "123"
                agreement_id = desc.split('#')[1].strip()
                
                from .models import DebtAgreement
                agreement = DebtAgreement.objects.get(id=agreement_id)
                agreement.check_activation()
                
            except (IndexError, ValueError, DebtAgreement.DoesNotExist):
                pass



@receiver(post_save, sender=Payment)
def sync_to_fiscal_module(sender, instance, created, **kwargs):
    """
    REFATORADO (v2.0): Sincronização Fiscal via BillingFactory
    
    IMPORTANTE: Esta função é chamada APÓS um pagamento ser validado.
    
    MAS: Se a Invoice foi criada via BillingFactory, ela JÁ TEM fiscal_doc!
    Esta função é um FALLBACK apenas para invoices legadas (migrações).
    
    Não cria mais DocumentoFiscal com número errado. A Factory é a fonte única.
    """
    if instance.validation_status == 'validated':
        invoice = instance.invoice
        
        # PROTEÇÃO: Se já tem fiscal_doc linkado, nada a fazer
        if invoice.fiscal_doc:
            return
        
        # AVISO: Se chegou aqui, é porque a Invoice foi criada FORA do Factory
        # Isto indica possível bug ou dados legados
        logger.warning(
            f"Invoice #{invoice.id} validada mas sem DocumentoFiscal linkado. "
            f"Esta invoice NÃO foi criada via BillingFactory (dados legados?). "
            f"Use BillingFactory.create_invoice_with_fiscal() para futuras criações."
        )
        
        # FALLBACK: Tenta criar DocumentoFiscal, mas com número seguro
        # NÃO usa generate_document_number() que pode gerar número duplicado
        try:
            from apps.fiscal.factories import BillingFactory
            from apps.fiscal.models import DocumentoFiscal as DocFiscal
            
            doc_fiscal = BillingFactory.create_documento_fiscal(
                cliente=invoice.student,
                tipo_documento=invoice.doc_type,
                valor_base=invoice.subtotal,
                valor_iva=invoice.tax_amount,
                taxa_iva=invoice.tax_type,
                usuario_criacao=instance.confirmed_by,
                documento_origem=None,
                status='confirmed'  # Já nasce confirmado porque Payment foi validado
            )
            
            # Vincular as linhas
            for item in invoice.items.all():
                from apps.fiscal.models import DocumentoFiscalLinha
                DocumentoFiscalLinha.objects.create(
                    documento=doc_fiscal,
                    descricao=item.description,
                    quantidade=Decimal('1'),
                    preco_unitario=item.amount,
                    taxa_iva=invoice.tax_type,
                    valor_total_linha=item.amount,
                    valor_iva_linha=Decimal('0'),  # Pode calcular se necessário
                    numero_linha=1
                )
            
            # Linkar o fiscal_doc
            invoice.fiscal_doc = doc_fiscal
            invoice.save(update_fields=['fiscal_doc'])
            
            logger.info(f"Fallback: DocumentoFiscal criado para Invoice #{invoice.id}")
            
        except Exception as e:
            logger.error(
                f"CRÍTICO: Não consegui criar DocumentoFiscal fallback para Invoice #{invoice.id}: {e}. "
                f"O documento pode estar SEM espelho fiscal!"
            )


@receiver(post_save, sender=Payment)
def master_finance_sync(sender, instance, created, **kwargs):
    """
    ORQUESTRADOR DEPRECADO
    
    Mantido apenas para compatibilidade histórica.
    Toda a sincronização agora é feita via BillingFactory e sync_to_fiscal_module.
    """
    # NOOP: Tudo já é feito no sync_to_fiscal_module acima
    pass
                status='confirmed'
            )

            # 3. SINCRONIZAÇÃO COM APP DOCUMENTS (Arquivo Digital do Aluno)
            from apps.documents.models import Document, DocumentType
            doc_type_obj, _ = DocumentType.objects.get_or_create(name=invoice.get_doc_type_display())
            Document.objects.create(
                student=invoice.student,
                document_type=doc_type_obj,
                related_fiscal_doc=doc_fiscal # Novo campo para rastreio
            )

            # 4. ATUALIZAÇÃO DA INVOICE COMERCIAL
            invoice.fiscal_doc = doc_fiscal
            invoice.status = 'paid'
            invoice.save()

            # 5. NOTIFICAÇÃO DE SUCESSO (UX de Elite)
            Notification.objects.create(
                user=invoice.student.user,
                title="Pagamento Confirmado ✅",
                message=f"Seu recibo {doc_fiscal.numero_documento} já está disponível no portal.",
                link=f"/portal/documents/"
            )


@receiver(pre_save, sender=Receipt)
def protect_receipt_immutability(sender, instance, **kwargs):
    """
    RIGOR SOTARQ: Bloqueia qualquer alteração em um Recibo já existente.
    Um documento fiscal (RC) uma vez emitido não pode ser editado, apenas anulado.
    """
    if instance.pk:
        # Se o objeto já existe no banco, buscamos a versão original
        original = Receipt.objects.get(pk=instance.pk)
        
        # Lista de campos protegidos
        protected_fields = ['amount_paid', 'number', 'payment', 'issue_date']
        
        for field in protected_fields:
            if getattr(original, field) != getattr(instance, field):
                raise PermissionDenied(
                    f"VIOLAÇÃO FISCAL: O campo '{field}' do Recibo {original.number} é imutável."
                )

@receiver(post_save, sender=Receipt)
def sync_receipt_to_cashflow(sender, instance, created, **kwargs):
    """
    AUTOMAÇÃO DE TESOURARIA: Sempre que um Recibo (RC) é gerado, 
    ele espelha a entrada real no Fluxo de Caixa Global.
    """
    if created:
        payment = instance.payment
        invoice = payment.invoice
        
        # Determinar categoria com base no primeiro item da fatura (Rigor de Auditoria)
        first_item = invoice.items.first()
        category_name = "Serviços Escolares"
        if first_item and first_item.fee_type:
            category_name = first_item.fee_type.name

        # Criar a entrada no CashFlow
        CashFlow.objects.create(
            description=f"RECEBIMENTO (RC): {instance.number} - {invoice.student.full_name}",
            amount=instance.amount_paid,
            transaction_type='IN', # Entrada
            payment=payment,
            category=category_name,
            date=instance.issue_date.date(),
            created_by=payment.confirmed_by
        )


# Para garantir que ninguém modifique um recibo pago

@receiver(pre_save, sender=Receipt)
@receiver(pre_save, sender=CashFlow)
def prevent_financial_modification(sender, instance, **kwargs):
    """
    RIGOR SOTARQ: Imutabilidade Fiscal.
    Se o registro já possui ID (já existe no banco), bloqueia qualquer update.
    """
    if instance.pk:
        raise PermissionDenied(
            f"ERRO CRÍTICO: Registros de {sender.__name__} são imutáveis. "
            "Para corrigir, use uma Nota de Crédito ou estorno oficial."
        )

@receiver(pre_delete, sender=Receipt)
@receiver(pre_delete, sender=CashFlow)
def prevent_financial_deletion(sender, instance, **kwargs):
    """
    Bloqueia a deleção de registros financeiros. 
    O rastro deve existir para sempre para auditoria da AGT.
    """
    raise PermissionDenied(
        f"VIOLAÇÃO DE SEGURANÇA: Não é permitido apagar registros de {sender.__name__}."
    )



@receiver(post_save, sender=Receipt)
def generate_receipt_document_file(sender, instance, created, **kwargs):
    """
    RIGOR SOTARQ: Assim que o Receipt é criado (com Hash), 
    gera o PDF e arquiva no repositório digital do aluno.
    """
    if created:
        from .utils import SOTARQExporter # Import local para evitar circularity

        # 1. Gerar o binário do PDF via sua classe Enterprise
        pdf_content = SOTARQExporter.generate_fiscal_document(
            instance=instance, 
            doc_type_code='RC', 
            page_format='A4'
        )

        # 2. Criar o registro no App Documents (Onde o aluno visualiza)
        doc_type_obj, _ = DocumentType.objects.get_or_create(name="Recibo de Pagamento")
        
        new_doc = Document.objects.create(
            student=instance.payment.invoice.student,
            document_type=doc_type_obj,
            description=f"Recibo de Pagamento {instance.number}",
            related_receipt=instance # FK para rastreio
        )

        # 3. Salvar o arquivo físico (S3 ou Local)
        filename = f"Recibo_{instance.number.replace('/', '_')}.pdf"
        new_doc.file.save(filename, ContentFile(pdf_content))
        new_doc.save()



@receiver(pre_save, sender=Invoice)
def protect_printed_invoice(sender, instance, **kwargs) :
    """
    RIGOR SOTARQ: Impede alteração de dados financeiros após a primeira impressão/emissão.
    Permite apenas a alteração do próprio campo 'is_printed' ou status de liquidação.
    """
    if instance.pk:
        old_instance = Invoice.objects.get(pk=instance.pk)
        
        # Se o documento já foi marcado como impresso
        if old_instance.is_printed:
            # Lista de campos permitidos para alteração mesmo após impressão (ex: status de pagamento)
            allowed_updates = ['status', 'is_printed', 'updated_at']
            
            # Verificação de campos sensíveis (Total, Itens, Aluno, Data de Emissão)
            for field in instance._meta.fields:
                field_name = field.name
                if field_name not in allowed_updates:
                    if getattr(old_instance, field_name) != getattr(instance, field_name):
                        raise PermissionDenied(
                            f"VIOLAÇÃO FISCAL SOTARQ: A Fatura {instance.number} já foi impressa e não pode ser alterada."
                        )



