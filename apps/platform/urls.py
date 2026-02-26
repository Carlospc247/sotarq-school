from django.urls import path
from . import views

app_name = 'platform'

urlpatterns = [
    path('global-dashboard/', views.global_admin_dashboard, name='global_dashboard'),
    path('dashboard/', views.global_admin_dashboard, name='global_dashboard'),
    path('agents/commissions/', views.agent_commission_manager, name='agent_commission_manager'),
    path('agents/performance/', views.agent_performance_report, name='agent_performance'),
    path('licensing/hub/', views.license_management_hub, name='license_hub'),
    path('tenants/force-block/', views.force_block_tenant, name='force_block'),
]
