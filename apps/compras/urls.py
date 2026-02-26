from django.urls import path
from . import views, views_store, views_fulfillment

app_name = 'compras'

urlpatterns = [
    # --- GESTÃO DE STOCK E ARMAZÉM ---
    path('dashboard/', views.stock_dashboard, name='stock_dashboard'),
    path('purchase/new/', views.create_purchase, name='create_purchase'),

    # --- LOJA ESCOLAR (PDV/POS) ---
    path('store/sale/', views_store.process_store_sale, name='process_store_sale'),
    path('store/receipt/<int:sale_id>/', views_store.receipt_view, name='receipt'),

    # --- FULFILLMENT (LEVANTAMENTO DE ENCOMENDAS) ---
    path('fulfillment/scan/<int:reservation_id>/', views_fulfillment.fulfillment_scan, name='fulfillment_scan'),
    path('fulfillment/confirm/<int:reservation_id>/', views_fulfillment.confirm_pickup, name='confirm_pickup'),
    path('fulfillment/receipt/<int:reservation_id>/', views_fulfillment.generate_delivery_receipt, name='generate_receipt'),
]