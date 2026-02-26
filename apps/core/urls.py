# apps/core/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from django.views.generic import RedirectView

from apps.core import views_recruitment
from . import views, views_admin

app_name = 'core'

urlpatterns = [
    # --- AUTENTICAÇÃO ---
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.logout_view, name='logout'),

    path('notifications/check-new/', views.check_new_notifications, name='check_new_notifications'),

    # --- DASHBOARD E NAVEGAÇÃO ---
    path('dashboard/', views.dashboard, name='dashboard'),
    path('dashboard/export-pdf/', views.export_dashboard_pdf, name='export_dashboard_pdf'),

    # --- GESTÃO DE USUÁRIOS (Staff/Admin) ---
    path('management/', RedirectView.as_view(pattern_name='core:user_management_list', permanent=False)),
    path('management/users/', views.user_management_list, name='user_management_list'),
    path('management/users/add/', views.user_add, name='user_add'),
    path('management/users/edit/<int:user_id>/', views.user_edit, name='user_edit'),
    
    # Import/Export Excel
    path('management/users/export/', views.user_export_excel, name='user_export'),
    path('management/users/import/template/', views.user_download_import_template, name='user_import_template'),
    path('management/users/import/', views.user_import_bulk, name='user_import'),

    # --- UTILITÁRIOS ---
    path('notifications/live/', views.get_notifications, name='get_notifications'),
    path('help-center/', views.help_center, name='help_center'),
    path('health/', views.health_check, name='health_check'),

    
    # Auditoria e Finanças
    path('admin/audit/final/', views_admin.final_audit_report, name='final_audit'),
    
    # [CORREÇÃO] Rota para a ação de cobrança em massa (Faltava esta linha)
    path('admin/audit/notify-bulk/', views_admin.notify_debtors_bulk, name='notify_debtors_bulk'),

    # --- INSTITUCIONAL (Configuração) ---
    path('settings/school/', views.school_configuration_update, name='school_settings'),

    # --- PÁGINAS PÚBLICAS ---
    path('portal/about/', views.public_about, name='public_about'),
    path('portal/courses/', views.public_courses, name='public_courses'),
    path('portal/contact/', views.public_contact, name='public_contact'),
    path('verify/authenticity/', views.public_verification, name='public_verification'),

    path('careers/apply/', views_recruitment.public_job_apply, name='public_job_apply'),
    path('management/recruitment/', views_recruitment.recruitment_dashboard, name='recruitment_dashboard'),
    path('management/recruitment/hire/<int:application_id>/', views_recruitment.hire_candidate, name='hire_candidate'),

    path('management/recruitment/toggle/', views_recruitment.toggle_recruitment_status, name='toggle_recruitment'),
    path('management/recruitment/areas/', views_recruitment.update_job_areas, name='update_job_areas'),

    path('management/recruitment/delete/<int:application_id>/', views_recruitment.delete_candidate, name='delete_candidate'),
    path('management/recruitment/message/', views_recruitment.send_candidate_whatsapp, name='send_candidate_whatsapp'),
]