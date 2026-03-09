from django.urls import path
from . import views

app_name = 'teachers'

urlpatterns = [
    # --- 1. DASHBOARD DO PROFESSOR ---
    path('dashboard/', views.teacher_dashboard, name='dashboard'),

    # --- 2. GESTÃO DE ALOCAÇÕES ---
    path('allocations/', views.TeacherAllocationListView.as_view(), name='allocation_list'),
    path('allocations/add/', views.TeacherAllocationCreateView.as_view(), name='allocation_create'),
    
    # ESTA É A LINHA QUE ESTAVA FALTANDO:
    path('allocations/delete/<int:pk>/', views.TeacherAllocationDeleteView.as_view(), name='allocation_delete'),

    # --- 3. MOTOR AJAX ---
    path('ajax/get-subjects/', views.get_subjects_by_class, name='ajax_get_subjects'),
]