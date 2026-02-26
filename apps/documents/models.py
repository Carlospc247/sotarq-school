# apps/documents/models.py
import uuid
import qrcode
import os
from io import BytesIO
from datetime import timedelta

from django.db import models, connection
from django.conf import settings
from django.utils import timezone
from django.core.files import File
from django.core.files.base import ContentFile
from django.urls import reverse
from apps.students.models import Student
from django_tenants.utils import get_tenant_domain_model, get_public_schema_name
from .services import stamp_qr_on_pdf


class DocumentType(models.Model):
    name = models.CharField(max_length=100, help_text="Ex: Boletim, Certificado, Declaração")
    requires_payment = models.BooleanField(default=False)
    requires_qr_verification = models.BooleanField(default=False, help_text="Gera QR Code para verificação de autenticidade.")
    # Optional: link to a Template if needed for generation
    # template = models.TextField(blank=True) 

    def __str__(self):
        return self.name

class Document(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='documents')
    document_type = models.ForeignKey(DocumentType, on_delete=models.PROTECT)
    file = models.FileField(upload_to='documents/%Y/%m/')
    issued_at = models.DateTimeField(auto_now_add=True)
    qr_code = models.ImageField(upload_to='qr_codes/%Y/%m/', blank=True, null=True)
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        super().save(*args, **kwargs) # Primeiro save para gerar ID

        if self.document_type.requires_qr_verification and not self.qr_code:
            token_obj = self.generate_verification_token()
            if token_obj:
                verif_url = token_obj.get_public_verification_url()
                
                qr = qrcode.QRCode(version=1, box_size=10, border=5)
                qr.add_data(verif_url)
                qr.make(fit=True)
                
                img = qr.make_image(fill_color="black", back_color="white")
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                
                filename = f"qr-{self.id}.png"
                self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=False)
                
                # Salva o QR e processa o carimbo no PDF
                super().save(update_fields=['qr_code'])
                self.process_and_stamp() # Carimba o PDF logo após gerar o QR



    def __str__(self):
        return f"{self.document_type} - {self.student}"
    
    def generate_verification_token(self, user=None, expires_in_days=365):
        """
        Gera um token de acesso único e com expiração para o documento.
        """
        if not self.document_type.requires_qr_verification:
            return None # Apenas gera tokens para tipos de documento que exigem.

        expires_at = timezone.now() + timedelta(days=expires_in_days)
        token_obj = DocumentAccessToken.objects.create(
            document=self,
            user=user, # O usuário que gerou o token (se houver)
            expires_at=expires_at
        )
        return token_obj
    
    def process_and_stamp(self):
        if self.file and self.qr_code:
            # Chama o serviço de carimbo
            stamped_pdf_buffer = stamp_qr_on_pdf(self.file.path, self.qr_code.path)
            
            # Substitui o arquivo original pelo assinado
            filename = os.path.basename(self.file.name)
            self.file.save(filename, ContentFile(stamped_pdf_buffer.read()), save=True)

class DocumentAccessToken(models.Model):
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='access_tokens')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True, help_text="Data/hora do primeiro uso, para tokens de uso único.")

    def is_valid(self):
        """Verifica se o token ainda é válido (não expirou e não foi usado, se for OTP)."""
        if self.used_at is not None:
            return False # Já foi usado
        if timezone.now() > self.expires_at:
            return False
        return True

    
from django.db import connection 

# Dentro da classe DocumentAccessToken:
def get_public_verification_url(self):
    """
    Retorna a URL pública para verificação, incluindo o slug do tenant.
    """
    public_domain = get_tenant_domain_model().objects.get(schema_name=get_public_schema_name())
    
    # O slug do tenant atual (quem está a emitir o documento)
    tenant_slug = connection.tenant.schema_name # Ou .slug se tiveres esse campo
    
    # IMPORTANTE: Os args devem bater com o path('verify/<str:tenant_slug>/<uuid:token_uuid>/')
    path = reverse('documents:verify_document', args=[tenant_slug, self.token])
    
    return f"https://{public_domain.domain}{path}"

    def __str__(self):
        return f"Token for {self.document} ({self.token})"