# apps/billing/urls.py
from django.urls import path
from . import views

app_name = 'billing'

urlpatterns = [
    # Aponte ambos para 'billing_webhook', que é a função que existe no seu views.py
    path('webhook/global/', views.billing_webhook, name='webhook_global'),
    path('webhook/emis/', views.billing_webhook, name='webhook_emis'), # CORRIGIDO AQUI
    
    path('payment-success/', views.payment_success, name='payment_success'),
]