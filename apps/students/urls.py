# apps/students/urls.py
from django.urls import path
from apps.students import views_reconfirmation
from . import views, views_public 

app_name = 'students'

urlpatterns = [
    # --- HUB DE GESTÃO ---
    path('management/', views.student_hub_dispatcher, name='student_list'),

    # --- MATRÍCULA PRESENCIAL (Backoffice) ---
    path('internal-enrollment/create/', views.student_add, name='internal_enrollment_create'),
    
    # --- IMPORT/EXPORT ---
    path('management/export/', views.student_export_excel, name='student_export'),
    path('management/import/', views.student_import_bulk, name='student_import'),
    path('management/import/template/', views.student_download_import_template, name='student_import_template'),

    path('management/student/<int:student_id>/modal/', views.student_detail_modal, name='student_detail_modal'),

    path('management/student/<int:student_id>/edit/', views.student_edit, name='student_edit'),
    path('management/student/<int:student_id>/print/', views.student_print_file, name='student_print_file'),
    path('management/student/<int:student_id>/finance/', views.student_financial_extract, name='student_financial_extract'),
    
    # --- OUTRAS ROTAS OPERACIONAIS ---
    path('search/', views.global_student_search, name='global_search'),
    path('lesson/start/<int:allocation_id>/', views.teacher_start_lesson, name='start_lesson'),
    path('lesson/end/<int:lesson_id>/', views.teacher_end_lesson, name='end_lesson'),
    path('validate/report-cards/<int:class_id>/', views.director_validate_grades, name='validate_grades'),
    path('enrollment/process/<int:student_id>/', views.process_enrollment, name='process_enrollment'),
    path('block/debtors/', views.block_debtors, name='block_debtors'),
    
    # --- ROTA PÚBLICA (APENAS MATRÍCULA NOVA) ---
    path('enrollment/public/', views_public.public_enrollment_form, name='public_enrollment'),

    # --- RECONFIRMAÇÃO ---
    # Interna (Secretaria - Presencial)
    path('management/reconfirmation/internal/', views_reconfirmation.internal_reconfirmation_process, name='internal_reconfirmation_process'),
    # Externa (Portal do Aluno - Online)
    path('portal/reconfirmation/', views_reconfirmation.portal_reconfirmation, name='portal_reconfirmation'),

    # --- CONFIGURAÇÕES DE PERÍODO (Trancar/Destrancar) ---
    path('enrollment/toggle/', views.toggle_enrollment_status, name='toggle_enrollment'),
    path('reconfirmation/toggle/', views.toggle_reconfirmation_status, name='toggle_reconfirmation'),
    
    path('ajax/load-grades/', views.load_grade_levels, name='ajax_load_grades'),
    path('ajax/load-classes/', views.load_classes, name='ajax_load_classes'),
]