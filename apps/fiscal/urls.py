from django.urls import path
from . import views

app_name = 'fiscal'

urlpatterns = [
    # Painel de Controle Fiscal e Histórico SAFT
    path('saft/list/', views.saft_list, name='saft_list'),
    
    # Download do XML para entrega à AGT
    path('saft/download/<int:pk>/', views.download_saft, name='download_saft'),
    
    # Configuração de Agendamento (Dia de Geração)
    path('config/update/', views.update_config, name='update_config'),
    
    # [Sugestão] Visualização de Documentos Assinados RSA
    #path('documents/audit/', views.fiscal_audit_log, name='fiscal_audit_log'),

    
    path('gestao-chaves/', views.gestao_chaves_rsa, name='gestao_chaves_rsa'),
    path('gestao-chaves/gerar/', views.gerar_nova_chave_action, name='gerar_nova_chave'),
    path('gestao-chaves/baixar-publica/<int:pk>/', views.baixar_chave_publica, name='baixar_chave_publica'),

    path('series/', views.gestao_series_fiscal, name='gestao_series'),
    path('series/gerar/', views.gerar_series_fiscal, name='gerar_series'),

    # Ex: /fiscal/imprimir/45/?format=80mm
    path('imprimir/<int:doc_id>/', views.imprimir_documento_fiscal, name='imprimir_documento_fiscal'),

    path('saft/delete/<int:pk>/', views.delete_saft, name='delete_saft'),
    
    path('api/agt-status/', views.api_agt_status, name='api_agt_status'),
    
    # Listagem e Configuração do SAF-T
    path('saft/list/', views.saft_list, name='saft_list'),
    path('saft/download/<int:pk>/', views.download_saft, name='download_saft'),
    path('config/update/', views.update_config, name='update_config'),
    
    # Anulação com Auditoria e Captura de IP
    path('anular/<int:doc_id>/', views.anular_documento_fiscal, name='anular_documento'),

    path('dashboard/', views.fiscal_audit_log, name='fiscal_audit_log'),

    path('config/iva/', views.taxa_iva_list, name='taxa_iva_list'),
    path('config/iva/novo/', views.taxa_iva_create, name='taxa_iva_create'),
]