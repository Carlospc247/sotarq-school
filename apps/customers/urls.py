# apps/customers/urls.py
from django.urls import path
from . import views

app_name = 'customers'

urlpatterns = [
    # Painel onde você vê todas as escolas (Tenants) criadas
    path('list/', views.AdminClientListView.as_view(), name='list_tenants'),
    path('create/', views.AdminClientCreateView.as_view(), name='create_tenant'),
]