from django.urls import path
from . import views

app_name = 'saft'

urlpatterns = [
    # Exportação do ficheiro mensal para submeter no portal da AGT
    path('export/xml/', views.export_saft_xml, name='export_xml'),
    
    # Download do documento de integridade da chave pública
    #path('key/certificate/<int:key_id>/', views.download_public_key_pdf, name='download_public_key_pdf'),
    
    # Dashboard de Auditoria (Monitor de hashes)
    path('audit/', views.saft_audit_dashboard, name='audit_dashboard'),
]