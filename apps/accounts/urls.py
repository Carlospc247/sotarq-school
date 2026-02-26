from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    # Visualização do Plano de Contas
    path('financial/ledger/', views.account_list, name='ledger_list'),
    
    # Gestão de Configurações do Sistema
    path('settings/general/', views.settings_dashboard, name='settings_dashboard'),
    path('settings/update/', views.update_setting, name='update_setting'),
]