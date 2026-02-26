from django.urls import path
from . import views

app_name = 'inventory'

urlpatterns = [
    path('dashboard/', views.inventory_dashboard, name='dashboard'),
    path('check/<int:asset_id>/', views.asset_qr_detail, name='asset_qr_detail'),
]