# apps/fiscal/generators.py
import logging
from decimal import Decimal
from datetime import datetime
from lxml import etree
from django.conf import settings
from django.db.models import Sum

from .models import DocumentoFiscal, TaxaIVAAGT
from apps.students.models import Student

logger = logging.getLogger(__name__)

class SAFTGenerator:
    NSMAP = {
        'ns': 'urn:OECD:StandardAuditFile-Tax:AO_1.01_01',
        None: 'urn:OECD:StandardAuditFile-Tax:AO_1.01_01'
    }

    def __init__(self, start_date, end_date, tenant_company):
        self.start_date = start_date
        self.end_date = end_date
        self.company = tenant_company
        self.filters = {
            'data_emissao__range': [self.start_date, self.end_date],
            'status__in': ['confirmed', 'cancelled']
        }

    def generate_xml(self):
        root = etree.Element("AuditFile", nsmap=self.NSMAP)
        self._build_header(root)
        self._build_master_files(root)
        self._build_source_documents(root)
        return etree.tostring(root, encoding='utf-8', xml_declaration=True, pretty_print=True)

    def _build_header(self, root):
        header = etree.SubElement(root, "Header")
        self._add(header, "AuditFileVersion", "1.01_01")
        
        # NIF: Garante 10 dígitos (regra de validação SAFAOAngolaVatNumber)
        nif = getattr(self.company, 'nif', '999999999')
        if len(nif) < 10: nif = nif.zfill(10)

        self._add(header, "CompanyID", nif)
        self._add(header, "TaxRegistrationNumber", nif)
        self._add(header, "TaxAccountingBasis", "F")
        self._add(header, "CompanyName", getattr(self.company, 'name', 'Escola Demo'))
        
        addr = etree.SubElement(header, "CompanyAddress")
        self._add(addr, "AddressDetail", "Sede")
        self._add(addr, "City", "Luanda")
        self._add(addr, "Country", "AO")
        
        self._add(header, "FiscalYear", str(self.start_date.year))
        self._add(header, "StartDate", self.start_date.strftime("%Y-%m-%d"))
        self._add(header, "EndDate", self.end_date.strftime("%Y-%m-%d"))
        self._add(header, "CurrencyCode", "AOA")
        self._add(header, "DateCreated", datetime.now().strftime("%Y-%m-%d"))
        self._add(header, "TaxEntity", "Global")
        self._add(header, "ProductCompanyTaxID", getattr(settings, 'AGT_PRODUCER_NIF', '5002764377'))
        self._add(header, "SoftwareValidationNumber", getattr(settings, 'AGT_CERTIFICATE_NUMBER', '000/AGT/2026'))
        self._add(header, "ProductID", f"Sotarq School/v{getattr(settings, 'AGT_SOFTWARE_VERSION', '1.0')}")
        self._add(header, "ProductVersion", getattr(settings, 'AGT_SOFTWARE_VERSION', '1.0'))

    def _build_master_files(self, root):
        master = etree.SubElement(root, "MasterFiles")
        
        # A. CLIENTES (Filtrados por movimentação no período)
        student_ids = DocumentoFiscal.objects.filter(**self.filters).values_list('cliente_id', flat=True).distinct()
        alunos = Student.objects.filter(id__in=student_ids)

        for aluno in alunos:
            cust = etree.SubElement(master, "Customer")
            # Rigor: ID oficial e imutável
            self._add(cust, "CustomerID", str(aluno.registration_number)) 
            self._add(cust, "AccountID", "31.1.2.1")
            
            # --- HIGIENE DE NIF RIGOROSA (PADRÃO 10 DÍGITOS) ---
            nif = str(getattr(aluno, 'nif', '')).strip()
            
            # Rigor SOTARQ: Se não tiver 10 dígitos exatos, força Consumidor Final
            if len(nif) != 10 or not nif.isdigit():
                nif = '9999999999' # Padrão AGT 10 dígitos para Consumidor Final
                
            self._add(cust, "CustomerTaxID", nif) 
            self._add(cust, "CompanyName", aluno.full_name.upper())
            
            bill = etree.SubElement(cust, "BillingAddress")
            self._add(bill, "AddressDetail", "ANGOLA")
            self._add(bill, "City", "LUANDA")
            self._add(bill, "Country", "AO")
            self._add(cust, "SelfBillingIndicator", "0")

        # B. PRODUTOS (Obrigatório por lei)
        self._build_products(master)

        # C. TABELA DE TAXAS (Rigor: Sem motivos de isenção aqui no XSD 1.01)
        tax_table = etree.SubElement(master, "TaxTable")
        for tax in TaxaIVAAGT.objects.filter(ativo=True):
            entry = etree.SubElement(tax_table, "TaxTableEntry")
            self._add(entry, "TaxType", tax.tax_type)
            self._add(entry, "TaxCode", tax.tax_code)
            self._add(entry, "Description", tax.nome.upper())
            self._add(entry, "TaxPercentage", f"{tax.tax_percentage:.2f}")

    def _build_products(self, parent):
        """Tabela de produtos simples"""
        products_node = etree.SubElement(parent, "Product")
        self._add(products_node, "ProductType", "S") 
        self._add(products_node, "ProductCode", "SERV")
        self._add(products_node, "ProductGroup", "Servicos")
        self._add(products_node, "ProductDescription", "Servicos de Ensino")
        self._add(products_node, "ProductNumberCode", "SERV")

    def _build_source_documents(self, root):
        source = etree.SubElement(root, "SourceDocuments")
        sales = etree.SubElement(source, "SalesInvoices")
        
        # Filtro rigoroso conforme sua app fiscal
        docs = DocumentoFiscal.objects.filter(
            tipo_documento__in=['FT', 'FR', 'NC', 'VD', 'ND', 'RC'], 
            **self.filters
        ).select_related('cliente', 'usuario_criacao')
        
        if not docs.exists():
            return

        self._add(sales, "NumberOfEntries", str(docs.count()))
        
        # Rigor Matemático AGT: Créditos vs Débitos
        total_credit = sum(d.valor_total for d in docs if d.tipo_documento not in ['NC', 'ND'])
        total_debit = sum(d.valor_total for d in docs if d.tipo_documento in ['NC', 'ND'])
        
        self._add(sales, "TotalDebit", f"{total_debit:.2f}")
        self._add(sales, "TotalCredit", f"{total_credit:.2f}")

        for doc in docs:
            inv = etree.SubElement(sales, "Invoice")
            self._add(inv, "InvoiceNo", doc.numero_documento)
            
            # 1. DocumentStatus (Conforme xs:complexType do XSD)
            status_node = etree.SubElement(inv, "DocumentStatus")
            # Mapeamento Rigoroso: confirmed -> N (Normal), cancelled -> A (Anulado)
            agt_status_code = 'N' if doc.status == 'confirmed' else 'A'
            self._add(status_node, "InvoiceStatus", agt_status_code)
            self._add(status_node, "InvoiceStatusDate", doc.updated_at.strftime("%Y-%m-%dT%H:%M:%S"))
            self._add(status_node, "SourceID", str(doc.usuario_criacao.id))
            self._add(status_node, "SourceBilling", "P")

            # 2. Dados de Assinatura e Período (Ordem OBRIGATÓRIA do XSD)
            self._add(inv, "Hash", doc.hash_documento)
            self._add(inv, "HashControl", "1") 
            # Extrai o mês do período YYYY-MM (Ex: 01, 02...)
            self._add(inv, "Period", doc.periodo_tributacao.split('-')[1]) 
            self._add(inv, "InvoiceDate", doc.data_emissao.strftime("%Y-%m-%d"))
            self._add(inv, "InvoiceType", doc.tipo_documento)
            
            # 3. SpecialRegimes (Obrigatório conforme xs:sequence do XSD)
            sr = etree.SubElement(inv, "SpecialRegimes")
            self._add(sr, "SelfBillingIndicator", "0")
            self._add(sr, "CashVATSchemeIndicator", "0")
            self._add(sr, "ThirdPartiesBillingIndicator", "0")

            self._add(inv, "SourceID", str(doc.usuario_criacao.id))
            self._add(inv, "SystemEntryDate", doc.created_at.strftime("%Y-%m-%dT%H:%M:%S"))
            
            # Link com o MasterFiles via Registration Number
            self._add(inv, "CustomerID", str(doc.cliente.registration_number)) 

            # 4. Linhas do Documento (Line)
            for linha in doc.linhas.all().order_by('numero_linha'):
                ln = etree.SubElement(inv, "Line")
                self._add(ln, "LineNumber", str(linha.numero_linha))
                self._add(ln, "ProductCode", "SERV")
                self._add(ln, "ProductDescription", linha.descricao)
                self._add(ln, "Quantity", f"{linha.quantidade:.2f}")
                self._add(ln, "UnitOfMeasure", "UN")
                self._add(ln, "UnitPrice", f"{linha.preco_unitario:.2f}")
                self._add(ln, "TaxPointDate", doc.data_emissao.strftime("%Y-%m-%d"))
                self._add(ln, "Description", linha.descricao)
                
                amount_str = f"{linha.valor_total_linha:.2f}"
                if doc.tipo_documento in ['NC', 'ND']:
                    self._add(ln, "DebitAmount", amount_str)
                else:
                    self._add(ln, "CreditAmount", amount_str)

                # Estrutura Tax (xs:complexType Tax)
                tax = etree.SubElement(ln, "Tax")
                self._add(tax, "TaxType", linha.taxa_iva.tax_type)
                self._add(tax, "TaxCountryRegion", "AO")
                self._add(tax, "TaxCode", linha.taxa_iva.tax_code)
                self._add(tax, "TaxPercentage", f"{linha.taxa_iva.tax_percentage:.2f}")
                
                # Grupo de Isenções (Obrigatório se TaxPercentage == 0)
                if linha.taxa_iva.tax_percentage == 0:
                    self._add(ln, "TaxExemptionReason", linha.taxa_iva.nome)
                    self._add(ln, "TaxExemptionCode", linha.taxa_iva.exemption_reason or "M99")

            # 5. DocumentTotals
            totals = etree.SubElement(inv, "DocumentTotals")
            self._add(totals, "TaxPayable", f"{doc.valor_iva:.2f}")
            self._add(totals, "NetTotal", f"{doc.valor_base:.2f}")
            self._add(totals, "GrossTotal", f"{doc.valor_total:.2f}")