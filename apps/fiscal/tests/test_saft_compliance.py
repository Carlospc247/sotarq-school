import os
from decimal import Decimal
from datetime import date
from django_tenants.test.cases import TenantTestCase
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.fiscal.models import DocumentoFiscal, DocumentoFiscalLinha, TaxaIVAAGT
from apps.fiscal.generators import SAFTGenerator
from apps.fiscal.validators import SAFTValidator
from apps.students.models import Student

class MockTenantData:
    """Simula os dados do TenantMixin para o cabeçalho do XML"""
    name = "Sotarq School Teste"
    nif = "5000000001" # 10 dígitos obrigatórios
    endereco = "Luanda, Angola"
    cidade = "Luanda"

@override_settings(
    AGT_PRODUCER_NIF='5002764377',
    AGT_CERTIFICATE_NUMBER='000/AGT/2026',
    AGT_SOFTWARE_VERSION='1.0.0'
)
class SAFTComplianceTest(TenantTestCase):

    def setUp(self):
        super().setUp()
        User = get_user_model()

        # 1. CRIAR USUÁRIOS
        self.student_user = User.objects.create_user(username='student_user', password='123')
        self.admin_user = User.objects.create_user(username='admin_user', password='123')

        # 2. CRIAR ALUNO
        self.aluno = Student.objects.create(
            user=self.student_user,
            registration_number="20260001",
            full_name="João Teste",
            birth_date=date(2015, 1, 1),
            gender='M',
            is_active=True
        )

        # 3. Configurar Taxas
        self.taxa_normal = TaxaIVAAGT.objects.create(
            nome="IVA Normal", tax_type="IVA", tax_code="NOR", 
            tax_percentage=Decimal('14.00')
        )
        self.taxa_isenta = TaxaIVAAGT.objects.create(
            nome="Isento", tax_type="IVA", tax_code="ISE", 
            tax_percentage=Decimal('0.00'), exemption_reason="M02"
        )

        # 4. Criar Fatura
        self.fatura = DocumentoFiscal.objects.create(
            tipo_documento="FT", serie="A", numero=1,
            numero_documento="FT A/1", atcud="5410001234_FT_A_1_123456789",
            data_emissao=date.today(),
            entidade_nome=self.aluno.full_name, 
            entidade_nif="999999999",
            valor_base=Decimal('20000.00'), 
            valor_iva=Decimal('1400.00'),
            valor_total=Decimal('21400.00'), 
            status='confirmed',
            hash_documento="h/k3j4h5k3j4h5k3j4h5k3j4h5k3j4h5k3j4h5k3j4h5k3j4h5", 
            hash_anterior="0",
            periodo_tributacao=date.today().strftime("%Y-%m"),
            usuario_criacao=self.admin_user,
            cliente=self.aluno
        )

        DocumentoFiscalLinha.objects.create(
            documento=self.fatura, numero_linha=1, descricao="Propina",
            quantidade=Decimal('1.00'), preco_unitario=Decimal('10000.00'),
            taxa_iva=self.taxa_normal, valor_total=Decimal('11400.00'),
            valor_total_linha=Decimal('11400.00')
        )
        DocumentoFiscalLinha.objects.create(
            documento=self.fatura, numero_linha=2, descricao="Livro",
            quantidade=Decimal('1.00'), preco_unitario=Decimal('10000.00'),
            taxa_iva=self.taxa_isenta, valor_total=Decimal('10000.00'),
            valor_total_linha=Decimal('10000.00')
        )

    def test_geracao_e_validacao_xsd(self):
        print("\n🚀 Iniciando Teste de Conformidade AGT...")
        generator = SAFTGenerator(date.today(), date.today(), MockTenantData())
        xml_output = generator.generate_xml()
        
        self.assertTrue(xml_output.startswith(b'<?xml'), "O output deve ser XML")
        print("✅ XML Gerado.")

        validator = SAFTValidator()
        if not os.path.exists(validator.XSD_PATH):
            print(f"⚠️ AVISO: XSD não encontrado em {validator.XSD_PATH}")
            return

        is_valid, errors = validator.validate(xml_output)
        if not is_valid:
            print("\n❌ FALHA XSD:", errors)
            print("XML START:", xml_output[:300].decode('utf-8'))
        
        self.assertTrue(is_valid, f"Erros XSD: {errors}")
        print("🏆 SUCESSO! SAFT Validado.")

    def test_logica_debito_credito(self):
        nc = DocumentoFiscal.objects.create(
            tipo_documento="NC", serie="A", numero=1,
            numero_documento="NC A/1", atcud="5410001234_NC_A_1_123",
            data_emissao=date.today(), 
            valor_base=Decimal('1000.00'),
            valor_iva=Decimal('0.00'),
            valor_total=Decimal('1000.00'),
            status='confirmed', 
            entidade_nome="João",
            periodo_tributacao="2026-01", 
            usuario_criacao=self.admin_user,
            cliente=self.aluno
        )
        
        DocumentoFiscalLinha.objects.create(
            documento=nc, numero_linha=1, descricao="Estorno",
            quantidade=Decimal('1.00'), preco_unitario=Decimal('1000.00'),
            taxa_iva=self.taxa_isenta, valor_total=Decimal('1000.00'),
            valor_total_linha=Decimal('1000.00')
        )

        gen = SAFTGenerator(date.today(), date.today(), MockTenantData())
        xml_content = gen.generate_xml()
        
        from lxml import etree
        root = etree.fromstring(xml_content)
        ns = {'ns': 'urn:OECD:StandardAuditFile-Tax:AO_1.01_01'}
        
        ft_credit = root.xpath("//ns:SourceDocuments/ns:SalesInvoices/ns:Invoice[ns:InvoiceType='FT']/ns:Line/ns:CreditAmount", namespaces=ns)
        nc_debit = root.xpath("//ns:SourceDocuments/ns:SalesInvoices/ns:Invoice[ns:InvoiceType='NC']/ns:Line/ns:DebitAmount", namespaces=ns)
        
        self.assertTrue(len(ft_credit) > 0, "Fatura = CreditAmount")
        self.assertTrue(len(nc_debit) > 0, "NC = DebitAmount")
        print("✅ Lógica Contabilística verificada.")