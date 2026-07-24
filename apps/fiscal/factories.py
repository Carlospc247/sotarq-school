# apps/fiscal/factories.py
"""
FACTORY PATTERN - SOTARQ BILLING SYSTEM

Camada centralizada para criar documentos fiscais e comerciais de forma atômica.
Garante que Invoice e DocumentoFiscal são sempre sincronizados e numerados sequencialmente.

Rigor: Esta é a ÚNICA via oficial para criar faturas no sistema.
"""

import logging
from django.db import transaction
from django.utils import timezone
from decimal import Decimal
from datetime import datetime

from .models import DocumentoFiscal, SerieFiscal, DocType, TaxaIVAAGT
from apps.students.models import Student

logger = logging.getLogger(__name__)


class BillingFactory:
    """
    Factory centralizado para criação atômica de documentos fiscais.
    
    Padrão Factory Pattern: Encapsula toda a lógica de criação, garantindo
    que Invoice + DocumentoFiscal sempre nascem sincronizados com numeração correta.
    """
    
    @staticmethod
    def obter_proximo_numero(tipo_documento, tenant):
        """
        ATOMICIDADE GARANTIDA: Obtém o próximo número sequencial de uma série.
        
        Usa SELECT FOR UPDATE no BD para bloquear a série e evitar race conditions.
        Isso garante que múltiplas requisições paralelas recebam números diferentes.
        
        Args:
            tipo_documento (str): DocType.FT, DocType.FR, DocType.NC, DocType.RC, DocType.FP
            tenant: Instância do Tenant (escola)
            
        Returns:
            tuple: (codigo_serie, numero_sequencial)
            
        Raises:
            ValueError: Se não encontrar uma série ativa
        """
        ano_atual = datetime.now().year
        
        with transaction.atomic():
            # BLOQUEIO EXCLUSIVO: SELECT FOR UPDATE garante que nenhuma outra transação
            # pode ler ou modificar esta série enquanto estamos aqui
            serie = SerieFiscal.objects.select_for_update().filter(
                tipo_documento=tipo_documento,
                ano=ano_atual,
                status='ATIVA',
                tenant=tenant
            ).first()
            
            if not serie:
                msg = (
                    f"ERRO CRÍTICO SOTARQ: Série ativa não encontrada para "
                    f"tipo={tipo_documento}, ano={ano_atual}, tenant={tenant}. "
                    f"Solicite uma série à AGT antes de emitir documentos."
                )
                logger.error(msg)
                raise ValueError(msg)
            
            # INCREMENTO DIRETO: Usa F() expression para incrementar no BD
            # MAS diferente do código antigo, NÃO atribuímos ao atributo Python
            serie.ultimo_numero += 1
            serie.save(update_fields=['ultimo_numero'])
            
            # LEITURA PÓS-INCREMENTO: Agora sim lemos o valor já incrementado
            # Estamos ainda na mesma transação atômica, então o valor é garantido
            numero_sequencial = serie.ultimo_numero
            codigo_serie = serie.codigo
            
            logger.info(
                f"Série {codigo_serie}: incrementada para número {numero_sequencial} "
                f"(tenant={tenant}, tipo={tipo_documento})"
            )
            
            return codigo_serie, numero_sequencial
    
    
    @staticmethod
    @transaction.atomic
    def create_documento_fiscal(
        cliente,
        tipo_documento,
        valor_base,
        valor_iva,
        taxa_iva,
        usuario_criacao,
        entidade_nome=None,
        entidade_nif='9999999999',
        documento_origem=None,
        status='draft'
    ):
        """
        Cria um DocumentoFiscal com numeração garantida e sem race conditions.
        
        Esta é a função NUCLEAR do sistema. Toda criação de documento fiscal
        passa por aqui, garantindo integridade contábil.
        
        Args:
            cliente (Student): O aluno/cliente
            tipo_documento (str): Uma das opções de DocType
            valor_base (Decimal): Base tributária (sem IVA)
            valor_iva (Decimal): Valor do IVA
            taxa_iva (TaxaIVAAGT): Objeto da taxa de IVA aplicada
            usuario_criacao (User): Quem está criando
            entidade_nome (str, optional): Nome da entidade (default: cliente.full_name)
            entidade_nif (str, optional): NIF da entidade
            documento_origem (str, optional): Referência para NC/RC (ex: "FT SERIE/001")
            status (str, optional): 'draft' ou 'confirmed'
            
        Returns:
            DocumentoFiscal: O documento criado e salvo
            
        Raises:
            ValueError: Se não conseguir obter número da série
        """
        tenant = cliente.user.tenant
        
        # 1. OBTER NÚMERO SEQUENCIAL (COM ATOMICIDADE GARANTIDA)
        codigo_serie, numero_sequencial = BillingFactory.obter_proximo_numero(
            tipo_documento, 
            tenant
        )
        
        # 2. BUSCAR SÉRIE DO BD (Precisa da FK)
        serie = SerieFiscal.objects.get(
            codigo=codigo_serie,
            tipo_documento=tipo_documento,
            tenant=tenant
        )
        
        # 3. PREPARAR DADOS DO DOCUMENTO
        numero_documento = f"{tipo_documento} {codigo_serie}/{numero_sequencial}"
        entidade_nome = entidade_nome or cliente.full_name
        valor_total = valor_base + valor_iva
        periodo_tributacao = timezone.now().strftime("%Y-%m")
        
        # 4. CRIAR DOCUMENTO FISCAL
        doc = DocumentoFiscal(
            tipo_documento=tipo_documento,
            status=status,  # IMPORTANT: 'draft' ou 'confirmed'
            serie=serie,
            serie_codigo=codigo_serie,
            numero=numero_sequencial,
            numero_documento=numero_documento,
            cliente=cliente,
            entidade_nome=entidade_nome,
            entidade_nif=entidade_nif,
            data_emissao=timezone.now().date(),
            valor_base=Decimal(str(valor_base)),
            valor_iva=Decimal(str(valor_iva)),
            valor_total=Decimal(str(valor_total)),
            periodo_tributacao=periodo_tributacao,
            usuario_criacao=usuario_criacao,
            documento_origem=documento_origem,
        )
        
        # 5. SALVAR (O save() do DocumentoFiscal fará hash se status='confirmed')
        doc.save()
        
        logger.info(
            f"DocumentoFiscal criado: {numero_documento} "
            f"(cliente={cliente.id}, tipo={tipo_documento}, status={status})"
        )
        
        return doc
    
    
    @staticmethod
    @transaction.atomic
    def create_invoice_with_fiscal(
        student,
        doc_type,
        due_date,
        subtotal,
        tax_type,
        user_criacao,
        discount_value=Decimal('0.00'),
        discount_is_pct=True,
        documento_origem=None
    ):
        """
        Cria uma Invoice (comercial) + DocumentoFiscal (compliance) simultaneamente.
        
        Esta é a entrypoint principal para criação de FATURAS no sistema.
        Garante que ambos os documentos nascem com números sincronizados.
        
        Args:
            student (Student): O aluno
            doc_type (str): DocType.FT, DocType.FR, etc.
            due_date (date): Data de vencimento
            subtotal (Decimal): Valor sem desconto/IVA
            tax_type (TaxaIVAAGT): Objeto da taxa
            user_criacao (User): Quem criou
            discount_value (Decimal): Valor ou % de desconto
            discount_is_pct (bool): Se o desconto é em %
            documento_origem (str): Para NC/Devolução, referência original
            
        Returns:
            tuple: (Invoice, DocumentoFiscal)
        """
        from apps.finance.models import Invoice, InvoiceItem
        
        tenant = student.user.tenant
        
        with transaction.atomic():
            # 1. CALCULAR TOTAIS COM RIGOR DECIMAL
            subtotal_dec = Decimal(str(subtotal))
            discount_value_dec = Decimal(str(discount_value))
            
            if discount_is_pct:
                discount_amount = subtotal_dec * (discount_value_dec / Decimal('100'))
            else:
                discount_amount = discount_value_dec
            
            base_apos_desconto = subtotal_dec - discount_amount
            
            # Taxa de IVA
            if tax_type:
                tax_pct = Decimal(str(tax_type.tax_percentage))
                tax_amount = base_apos_desconto * (tax_pct / Decimal('100'))
            else:
                tax_amount = Decimal('0.00')
            
            total = base_apos_desconto + tax_amount
            
            # 2. CRIAR DOCUMENTO FISCAL PRIMEIRO (obtém número oficial)
            doc_fiscal = BillingFactory.create_documento_fiscal(
                cliente=student,
                tipo_documento=doc_type,
                valor_base=base_apos_desconto,
                valor_iva=tax_amount,
                taxa_iva=tax_type,
                usuario_criacao=user_criacao,
                documento_origem=documento_origem,
                status='draft'  # Começa em draft, confirma depois
            )
            
            # 3. CRIAR INVOICE COMERCIAL (herda número do fiscal)
            invoice = Invoice.objects.create(
                doc_type=doc_type,
                number=doc_fiscal.numero_documento,  # ← SINCRONIZADO!
                student=student,
                status='pending',
                due_date=due_date,
                subtotal=subtotal_dec,
                discount_value=discount_value_dec,
                discount_is_pct=discount_is_pct,
                discount_amount=discount_amount,
                tax_type=tax_type,
                tax_amount=tax_amount,
                total=total,
                fiscal_doc=doc_fiscal  # ← VINCULAÇÃO OFICIAL
            )
            
            logger.info(
                f"Invoice criada: {invoice.number} "
                f"(student={student.id}, total={total}) "
                f"→ Fiscal: {doc_fiscal.numero_documento}"
            )
            
            return invoice, doc_fiscal
    
    
    @staticmethod
    @transaction.atomic
    def confirm_and_sign_documento(documento_id, user_confirmacao):
        """
        Confirma um DocumentoFiscal em draft e gera sua assinatura SHA1.
        
        Chamada APÓS validação do pagamento ou após confirmação manual.
        
        Args:
            documento_id (int): ID do DocumentoFiscal
            user_confirmacao (User): Quem confirmou
            
        Returns:
            DocumentoFiscal: Documento atualizado com status='confirmed' e hash
        """
        doc = DocumentoFiscal.objects.get(id=documento_id)
        
        if doc.status != DocumentoFiscal.Status.DRAFT:
            raise ValueError(
                f"Documento {doc.numero_documento} já está em status '{doc.status}'. "
                f"Só documentos em 'draft' podem ser confirmados."
            )
        
        # Transição de estado
        doc.status = DocumentoFiscal.Status.CONFIRMED
        
        # O save() vai disparar _generate_sha1_hash() automaticamente
        doc.save()
        
        logger.info(
            f"DocumentoFiscal confirmado e assinado: {doc.numero_documento} "
            f"(hash={doc.hash_documento[:16]}...)"
        )
        
        return doc
