from django.urls import path
from . import views

app_name = 'reports'

urlpatterns = [
    path('', views.report_list, name='report_catalog'),
    path('history/', views.execution_history, name='execution_history'),
    path('trigger/bulletin/<int:class_id>/', views.trigger_bulk_bulletins, name='trigger_bulk_bulletins'),
    path('dashboard/pedagogical/', views.pedagogical_quality_dashboard, name='pedagogical_dashboard'),
    path('ajax/search-allocations/', views.search_allocation_ajax, name='ajax_search_allocations'),
]