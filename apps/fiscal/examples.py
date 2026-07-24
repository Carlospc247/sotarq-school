# apps/fiscal/examples.py
"""
EXEMPLOS DE USO - BillingFactory

Estes exemplos demonstram como usar a factory refatorada para criar documentos.
Copia-cola estes padrões no seu código em views, tasks, commands, etc.
"""

from decimal import Decimal
from django.utils import timezone
from apps.students.models import Student
from apps.fiscal.models import TaxaIVAAGT, DocType
from apps.fiscal.factories import BillingFactory


# ===========================================================================
# EXEMPLO 1: Criar uma Fatura (FT) com Pagamento Imediato (Via Operador)
# ===========================================================================

def exemplo_criar_fatura_simples():
    """
    Caso: Operador de caixa cria uma fatura de matrícula na hora.
    """
    from django.contrib.auth import get_user_model
    from apps.finance.models import InvoiceItem, Payment, PaymentMethod
    from django.db import transaction
    
    User = get_user_model()
    
    # 1. Buscar dados básicos
    student = Student.objects.get(registration_number='EXC-2026/001')
    user_operador = User.objects.get(username='joao_secretario')
    taxa_iva = TaxaIVAAGT.objects.get(tax_code='NOR')  # IVA Normal
    
    # 2. Preparar valores
    valor_propina = Decimal('24525.96')
    subtotal = valor_propina
    
    # 3. USAR A FACTORY (Esta é a forma correta!)
    with transaction.atomic():
        invoice, doc_fiscal = BillingFactory.create_invoice_with_fiscal(
            student=student,
            doc_type=DocType.FT,  # Fatura
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            subtotal=subtotal,
            tax_type=taxa_iva,
            user_criacao=user_operador
        )
        
        # 4. Adicionar itens à fatura
        InvoiceItem.objects.create(
            invoice=invoice,
            description='Propina Mensal - Maio 2026',
            amount=valor_propina,
            competence_month=5
        )
        
        # 5. Atualizar totais (motor de cálculo do Invoice)
        invoice.update_totals()
        
        # 6. Se for pagamento imediato (presencial):
        payment_method = PaymentMethod.objects.get(name='Dinheiro')
        payment = Payment.objects.create(
            invoice=invoice,
            amount=invoice.total,
            method=payment_method,
            confirmed_by=user_operador,
            confirmed_at=timezone.now(),
            validation_status='validated'
        )
        
        # Marcar invoice como paga
        invoice.status = 'paid'
        invoice.save()
        
        # 7. Confirmar documento fiscal (gera hash SHA1)
        BillingFactory.confirm_and_sign_documento(
            documento_id=doc_fiscal.id,
            user_confirmacao=user_operador
        )
    
    print(f"✓ Fatura criada: {invoice.number}")
    print(f"✓ Documento Fiscal: {doc_fiscal.numero_documento}")
    print(f"✓ Hash SHA1: {doc_fiscal.hash_documento[:32]}...")
    return invoice, doc_fiscal


# ===========================================================================
# EXEMPLO 2: Criar Fatura Pending (Será Paga Depois - Via Transfer Bancária)
# ===========================================================================

def exemplo_criar_fatura_pending():
    """
    Caso: Sistema emite fatura que será paga via Multicaixa/Transfer (não presencial).
    """
    from django.db import transaction
    
    student = Student.objects.get(id=123)
    user_sistema = User.objects.get(username='sistema_automate')
    taxa_iva = TaxaIVAAGT.objects.get(tax_code='NOR')
    
    with transaction.atomic():
        invoice, doc_fiscal = BillingFactory.create_invoice_with_fiscal(
            student=student,
            doc_type=DocType.FT,
            due_date=timezone.now().date() + timezone.timedelta(days=10),
            subtotal=Decimal('11400.00'),
            tax_type=taxa_iva,
            user_criacao=user_sistema
        )
        
        # Neste caso, deixamos a fatura em 'pending' (default)
        # Não vamos validar pagamento ainda
        # O DocumentoFiscal fica em 'draft' até o pagamento chegar
    
    print(f"✓ Fatura Pending: {invoice.number}")
    print(f"✓ Vencimento: {invoice.due_date}")
    print(f"  (Esperando confirmação de pagamento...)")
    return invoice, doc_fiscal


# ===========================================================================
# EXEMPLO 3: Criar uma Nota de Crédito (NC) Devolvendo uma Fatura
# ===========================================================================

def exemplo_criar_nota_credito():
    """
    Caso: Diretor anula parcialmente uma fatura anterior via Nota de Crédito.
    """
    from django.db import transaction
    
    # Buscar a fatura original
    fatura_original = Student.objects.get(id=123).invoices.filter(
        doc_type=DocType.FT,
        status='paid'
    ).first()
    
    if not fatura_original or not fatura_original.fiscal_doc:
        print("Erro: Fatura original não encontrada ou sem DocumentoFiscal")
        return None, None
    
    user_diretor = get_user_model().objects.get(username='diretor')
    taxa_iva = TaxaIVAAGT.objects.get(tax_code='NOR')
    
    # Valor da devolução (parcial ou total)
    valor_devolucao = Decimal('5000.00')  # Parte dos 24525.96
    
    with transaction.atomic():
        invoice_nc, doc_fiscal_nc = BillingFactory.create_invoice_with_fiscal(
            student=fatura_original.student,
            doc_type=DocType.NC,  # Nota de Crédito
            due_date=timezone.now().date(),
            subtotal=-valor_devolucao,  # NEGATIVO para devolução
            tax_type=taxa_iva,
            user_criacao=user_diretor,
            documento_origem=fatura_original.number  # Referência à original
        )
        
        # Adicionar item descrevendo o motivo
        from apps.finance.models import InvoiceItem
        InvoiceItem.objects.create(
            invoice=invoice_nc,
            description='Devolução - Erro de cobrança (aluno já pagou)',
            amount=-valor_devolucao
        )
        
        invoice_nc.update_totals()
    
    print(f"✓ Nota de Crédito emitida: {invoice_nc.number}")
    print(f"✓ Referência original: {fatura_original.number}")
    return invoice_nc, doc_fiscal_nc


# ===========================================================================
# EXEMPLO 4: Criar Fatura-Recibo (FR) - Liquidação Imediata
# ===========================================================================

def exemplo_criar_fatura_recibo():
    """
    Caso: Presença no operador, precisa dar recibo logo (FR).
    """
    from django.db import transaction
    
    student = Student.objects.get(id=456)
    user_operador = get_user_model().objects.get(username='caixa_principal')
    taxa_iva = TaxaIVAAGT.objects.get(tax_code='NOR')
    
    with transaction.atomic():
        # FR nasce com status='confirmed' automaticamente (no save do DocumentoFiscal)
        invoice, doc_fiscal = BillingFactory.create_invoice_with_fiscal(
            student=student,
            doc_type=DocType.FR,  # Fatura-Recibo
            due_date=timezone.now().date(),  # Sem vencimento, liquidação imediata
            subtotal=Decimal('2000.00'),
            tax_type=taxa_iva,
            user_criacao=user_operador
        )
        
        # FR nasce com status 'confirmed', logo o DocumentoFiscal tem hash
        assert doc_fiscal.status == 'confirmed'
        assert doc_fiscal.hash_documento is not None
    
    print(f"✓ Fatura-Recibo: {invoice.number}")
    print(f"✓ Status automático: CONFIRMED (Liquidação Imediata)")
    return invoice, doc_fiscal


# ===========================================================================
# EXEMPLO 5: Erro Intencional - O Que NÃO Fazer
# ===========================================================================

def exemplo_anti_pattern_criacao_direta():
    """
    ANTI-PATTERN! Não faça isto!
    """
    from apps.finance.models import Invoice
    
    # ❌ ERRADO: Criação direta sem Factory
    # (Isto vai falhar ou gerar número errado)
    try:
        invoice = Invoice.objects.create(
            student_id=123,
            doc_type=DocType.FT,
            due_date=timezone.now().date() + timezone.timedelta(days=30),
            total=Decimal('1000.00')
        )
        print(f"Invoice criada com número fallback: {invoice.number}")
        # Isto pode gerar um número errado tipo "FT FALLBACK-1714065432.123456"
    except Exception as e:
        print(f"✗ Erro esperado: {e}")
    
    # ✓ CORRETO: Use a Factory!


# ===========================================================================
# UTILS: Para usar nos seus scripts
# ===========================================================================

def criar_fatura_em_lote(student_ids, doc_type, valor):
    """
    Exemplo: Emitir 100 faturas para alunos em paralelo.
    Demonstra que BillingFactory é thread-safe.
    """
    from concurrent.futures import ThreadPoolExecutor
    from django.db import transaction
    
    def criar_para_aluno(student_id):
        try:
            student = Student.objects.get(id=student_id)
            user_sistema = get_user_model().objects.get(username='sistema')
            taxa = TaxaIVAAGT.objects.get(tax_code='NOR')
            
            invoice, doc = BillingFactory.create_invoice_with_fiscal(
                student=student,
                doc_type=doc_type,
                due_date=timezone.now().date() + timezone.timedelta(days=15),
                subtotal=Decimal(str(valor)),
                tax_type=taxa,
                user_criacao=user_sistema
            )
            
            return invoice.number, True, None
        except Exception as e:
            return None, False, str(e)
    
    # Executar em paralelo com 10 threads
    with ThreadPoolExecutor(max_workers=10) as executor:
        resultados = list(executor.map(criar_para_aluno, student_ids))
    
    # Verificar resultados
    sucessos = [r for r in resultados if r[1]]
    erros = [r for r in resultados if not r[1]]
    
    print(f"✓ {len(sucessos)} faturas criadas com sucesso")
    print(f"✗ {len(erros)} erros")
    
    return sucessos, erros


if __name__ == '__main__':
    print("Exemplos de BillingFactory\n")
    
    # Descomente para testar:
    # exemplo_criar_fatura_simples()
    # exemplo_criar_fatura_pending()
    # exemplo_anti_pattern_criacao_direta()
