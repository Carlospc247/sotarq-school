from django.urls import path
from . import views

app_name = 'cafeteria'

urlpatterns = [
    # Interface Principal do Ponto de Venda (PDV/POS)
    path('pos/', views.pos_checkout, name='pos_checkout'),
    
    # Atualização de Limites (Ação do Encarregado/Portal)
    path('wallet/limit/update/', views.update_daily_limit, name='update_daily_limit'),
    
    # Controle de Restrições (Endpoint HTMX/AJAX)
    path('product/restriction/toggle/', views.toggle_product_restriction, name='toggle_restriction'),

    # Pesquisar alunos
    path('student/search/', views.search_student, name='search_student'),
    
    # Gestão de Inventário e Saúde
    path('inventory/', views.inventory_list, name='inventory_list'),
    
    # Gestão de Clientes (Alunos + Staff + Visitantes)
    path('clients/', views.client_manager, name='client_manager'),
    
    # Auditoria Financeira
    path('sessions/history/', views.sessions_history, name='sessions_history'),
]