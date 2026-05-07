# apps/finance/signals.py
from datetime import timezone

from apps.core.utils import generate_document_number
from apps.documents.models import Document, DocumentType
from django.db.models import transaction
from django.dispatch import receiver
from .models import Payment
from apps.core.models import Notification
from django.contrib.auth import get_user_model
from .models import Payment, DebtAgreement
from apps.fiscal.models import DocumentoFiscal, DocumentoFiscalLinha
from django.core.exceptions import PermissionDenied
from django.db.models.signals import pre_save, post_save, pre_delete
from .models import Receipt, CashFlow
from django.core.files.base import ContentFile





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
    Sempre que um pagamento é validado, verifica se ativa um acordo de dívida.
    """
    if instance.validation_status == 'validated':
        invoice = instance.invoice
        # Verifica se esta fatura é a "Prestação 1" de algum acordo
        if "Prestação 1/" in invoice.description and "Acordo #" in invoice.description:
            # Extrair ID do acordo da descrição (ex: "Acordo #123")
            try:
                agreement_id = invoice.description.split('#')[1]
                agreement = DebtAgreement.objects.get(id=agreement_id)
                agreement.check_activation()
            except (IndexError, DebtAgreement.DoesNotExist):
                pass





@receiver(post_save, sender=Payment)
def sync_to_fiscal_module(sender, instance, created, **kwargs):
    """
    Rigor SOTARQ: Assim que um pagamento é VALIDADO, 
    ele gera o espelho na app FISCAL para o SAF-T.
    """
    if instance.validation_status == 'validated' and not hasattr(instance.invoice, 'fiscal_doc'):
        invoice = instance.invoice
        # Criar o Documento Fiscal
        doc_fiscal = DocumentoFiscal.objects.create(
            tipo_documento=invoice.doc_type,
            serie=f"{invoice.doc_type}{timezone.now().year}",
            numero=int(invoice.number.split('/')[-1]),
            numero_documento=invoice.number,
            cliente=invoice.student,
            data_emissao=timezone.now().date(),
            entidade_nome=invoice.student.full_name,
            valor_base=invoice.subtotal,
            valor_total=invoice.total,
            valor_iva=invoice.tax_amount,
            periodo_tributacao=timezone.now().strftime("%Y-%m"),
            usuario_criacao=instance.confirmed_by,
            status='confirmed' # Já nasce confirmado para assinar RSA
        )
        
        # Vincular as linhas
        for item in invoice.items.all():
            DocumentoFiscalLinha.objects.create(
                documento=doc_fiscal,
                descricao=item.description,
                quantidade=1,
                preco_unitario=item.amount,
                taxa_iva=invoice.tax_type, # FK para TaxaIVAAGT
                valor_total_linha=item.amount,
                numero_linha=1
            )
        
        # Atualiza a invoice comercial com o link fiscal
        invoice.fiscal_doc = doc_fiscal
        invoice.save()

# apps/finance/signals.py unificado

@receiver(post_save, sender=Payment)
def master_finance_sync(sender, instance, created, **kwargs):
    """
    ORQUESTRADOR SUPREMO: Sincroniza Financeiro -> Fiscal -> Documentos -> Notificações.
    """
    if instance.validation_status == 'validated':
        invoice = instance.invoice
        
        # 1. EVITAR DUPLICIDADE (Rigor Anti-Fatura-Dupla)
        if invoice.fiscal_doc:
            return

        with transaction.atomic():
            # 2. GERAÇÃO DO ESPELHO FISCAL (Para AGT/SAFT)
            from apps.fiscal.models import DocumentoFiscal, DocumentoFiscalLinha, DocType
            
            doc_fiscal = DocumentoFiscal.objects.create(
                tipo_documento=invoice.doc_type,
                serie=f"{invoice.doc_type}{timezone.now().year}",
                # O número real fiscal é gerado aqui para garantir sequência sem furos
                numero_documento=generate_document_number(DocumentoFiscal, invoice.doc_type), 
                cliente=invoice.student,
                data_emissao=timezone.now().date(),
                entidade_nome=invoice.student.full_name,
                valor_total=invoice.total,
                usuario_criacao=instance.confirmed_by,
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



