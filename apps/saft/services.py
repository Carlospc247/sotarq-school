# apps/saft/services.py
from .crypto import generate_invoice_hash
from .models import InvoiceControl, SAFTSettings

class SAFTEngine:
    @staticmethod
    def sign_invoice(invoice_instance):
        """
        Ponto de entrada único para selar uma fatura.
        """
        settings = SAFTSettings.objects.first()
        last_invoice = InvoiceControl.objects.last()
        
        # Formato: Data;DataHora;Numero;Total
        invoice_data = (
            f"{invoice_instance.issue_date.strftime('%Y-%m-%d')};"
            f"{invoice_instance.created_at.strftime('%Y-%m-%dT%H:%M:%S')};"
            f"{invoice_instance.number};"
            f"{float(invoice_instance.total):.2f}"
        )
        
        previous_hash = last_invoice.hash_value if last_invoice else None
        
        # Gera a assinatura RSA
        full_signature = generate_invoice_hash(
            invoice_data, 
            previous_hash, 
            settings.private_key
        )
        
        # Salva no rasto de auditoria
        InvoiceControl.objects.create(
            invoice_number=invoice_instance.number,
            hash_value=full_signature
        )
        
        return full_signature
