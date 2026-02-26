# apps/finance/signals.py
from datetime import timezone

from apps.core.utils import generate_document_number
from apps.documents.models import Document, DocumentType
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Payment
from apps.core.models import Notification
from django.contrib.auth import get_user_model
from .models import Payment, DebtAgreement
from apps.fiscal.models import DocumentoFiscal, DocumentoFiscalLinha



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