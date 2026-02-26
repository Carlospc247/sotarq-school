from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # URL para verificação pública do documento via token QR Code
    path('verify/<str:tenant_slug>/<uuid:token_uuid>/', views.verify_document_view, name='verify_document'),
]