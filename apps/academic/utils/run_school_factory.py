# apps/academic/utils/run_school_factory.py
import datetime
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
from django.db import transaction, connection
from django_tenants.utils import schema_context

def run_full_school_setup(instance, stdout=None):
    """
    ORQUESTRADOR SOTARQ:
    Configura apenas o essencial (Fiscal e Académico) forçando o contexto do schema.
    """
    
    # 1. RIGOR: Entramos no contexto do tenant para garantir que as tabelas existam
    with schema_context(instance.schema_name):
        
        # Atualiza lista de tabelas do schema atual (da escola)
        existing_tables = connection.introspection.table_names()

        try:
            with transaction.atomic():
                from apps.fiscal.models import AssinaturaDigital
                from apps.academic.models import AcademicGlobal, AcademicYear

                # Segurança: verificar se as migrations já criaram as tabelas no schema
                if AcademicGlobal._meta.db_table not in existing_tables:
                    if stdout:
                        stdout.write(f"  [AVISO] Tabelas não prontas em {instance.schema_name}")
                    return

                # --- PARTE 1: FISCAL ---
                if not AssinaturaDigital.objects.exists():
                    private_key = rsa.generate_private_key(
                        public_exponent=65537,
                        key_size=2048
                    )
                    private_pem = private_key.private_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PrivateFormat.PKCS8,
                        encryption_algorithm=serialization.NoEncryption()
                    ).decode("utf-8")
                    public_pem = private_key.public_key().public_bytes(
                        encoding=serialization.Encoding.PEM,
                        format=serialization.PublicFormat.SubjectPublicKeyInfo
                    ).decode("utf-8")

                    AssinaturaDigital.objects.create(
                        tenant=instance,
                        chave_privada_pem=private_pem,
                        chave_publica_pem=public_pem,
                        descricao=f"Chaves AGT - {instance.name}",
                        ativa=True
                    )
                    if stdout:
                        stdout.write("  [FISCAL] Chaves RSA geradas.")

                # --- PARTE 2: CONFIG ACADÉMICA ---
                AcademicGlobal.objects.get_or_create(tenant=instance)

                # --- PARTE 3: ANO ACADÉMICO ---
                today = datetime.date.today()
                start_year = today.year if today.month >= 9 else today.year - 1
                start_date = datetime.date(start_year, 9, 2)
                end_date = datetime.date(start_year + 1, 7, 31)
                name = f"{start_year}/{start_year+1}"

                if not AcademicYear.objects.exists():
                    AcademicYear.objects.create(
                        tenant=instance,
                        name=name,
                        start_date=start_date,
                        end_date=end_date,
                        is_active=True
                    )
                    if stdout:
                        stdout.write(f"  [ACADEMIC] Ano académico criado: {name}")

        except Exception as e:
            if stdout:
                stdout.write(f"  [ERRO CRÍTICO] {instance.schema_name}: {str(e)}")
            raise e