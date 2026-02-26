from django.urls import path
from . import views

# O app_name é o que permite o uso de 'audit:logs' no template
app_name = 'audit'

urlpatterns = [
    path('logs/', views.audit_logs, name='logs'),
    path('alerts/security/', views.security_alerts_list, name='security_alerts'),
    path('alerts/resolve/<int:alert_id>/', views.resolve_alert, name='resolve_alert'),
]