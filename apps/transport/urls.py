from django.urls import path
from . import views

app_name = 'transport'

urlpatterns = [
    # Dashboard Operacional (Frota e Ocupação)
    path('dashboard/', views.transport_dashboard, name='dashboard'),
    
    # Interface de Scanner (Para Tablets nos Autocarros)
    path('scanner/<int:bus_id>/', views.scan_student_badge, name='scanner'),
    
    # Relatório de BI (Análise de Eficiência e Motoristas)
    path('analytics/', views.transport_analytics_report, name='analytics'),
    path('track/<int:bus_id>/', views.live_tracking, name='live_tracking'),
    path('checkpoint/process/', views.process_checkpoint, name='process_checkpoint'),

    path('history/export/pdf/', views.export_history_pdf, name='export_history_pdf'),
]