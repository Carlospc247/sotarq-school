from django.contrib import admin
from django.utils.safestring import mark_safe
from .models import Document

@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('student', 'document_type', 'issued_at', 'qr_code_preview')
    readonly_fields = ('qr_code_preview',)

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return mark_safe(f'<img src="{obj.qr_code.url}" width="150" height="150" />')
        return "Pendente de geração"
    
    qr_code_preview.short_description = "QR Code de Autenticidade"