# apps/fiscal/validators.py
import os
import logging
from lxml import etree
from django.conf import settings

logger = logging.getLogger(__name__)

class SAFTValidator:
    """
    Motor de Conformidade Técnica SOTARQ.
    Valida o XML contra o esquema oficial AO_1.01_01.xsd.
    """
    
    # Caminho para o esquema oficial que deve estar na pasta de schemas
    XSD_PATH = os.path.join(settings.BASE_DIR, 'apps', 'fiscal', 'schemas', 'SAFTAO1.01_01.xsd')

    def __init__(self):
        if not os.path.exists(self.XSD_PATH):
            logger.error(f"CRÍTICO: Esquema XSD não encontrado em: {self.XSD_PATH}")
            self.schema = None
            return

        try:
            with open(self.XSD_PATH, 'rb') as f:
                schema_root = etree.XML(f.read())
            self.schema = etree.XMLSchema(schema_root)
        except Exception as e:
            logger.critical(f"Falha ao compilar XSD da AGT: {e}")
            self.schema = None

    def validate(self, xml_content_bytes):
        """
        Executa a perícia. Retorna (True, []) ou (False, [erros]).
        """
        if self.schema is None:
            return False, ["Validador offline: Esquema XSD ausente no servidor."]

        try:
            xml_doc = etree.fromstring(xml_content_bytes)
            if self.schema.validate(xml_doc):
                return True, []
            else:
                # Extrai os erros técnicos detalhados para o log
                return False, [f"Linha {e.line}: {e.message}" for e in self.schema.error_log]
        except etree.XMLSyntaxError as e:
            return False, [f"Erro de sintaxe XML: {e}"]
        except Exception as e:
            return False, [f"Erro inesperado na validação: {e}"]