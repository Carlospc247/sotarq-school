import xml.etree.ElementTree as ET

class SAFTBuilder:
    def __init__(self, tenant):
        self.root = ET.Element("AuditFile", {
            "xmlns": "urn:OECD:StandardAuditFile-Tax:AO:1.01_01",
            "xmlns:xsi": "http://www.w3.org/2001/XMLSchema-instance"
        })
        self.tenant = tenant

    def build_master_files(self):
        master = ET.SubElement(self.root, "MasterFiles")
        # Clientes (Students/Schools)
        # Produtos (Subjects/Fees)
        # TaxTable (Tabela de Impostos - Crucial para validação)
        taxes = ET.SubElement(master, "TaxTable")
        entry = ET.SubElement(taxes, "TaxTableEntry")
        ET.SubElement(entry, "TaxType").text = "IVA"
        ET.SubElement(entry, "TaxCode").text = "ISE" # Isento
        ET.SubElement(entry, "Description").text = "Isento nos termos da Lei"

    def build_sales_invoices(self, invoices):
        source = ET.SubElement(self.root, "SourceDocuments")
        sales = ET.SubElement(source, "SalesInvoices")
        
        for inv in invoices:
            node = ET.SubElement(sales, "Invoice")
            ET.SubElement(node, "InvoiceNo").text = inv.number
            ET.SubElement(node, "Hash").text = inv.hash_value # Gerado pelo crypto.py
            # Detalhes de linhas e impostos...