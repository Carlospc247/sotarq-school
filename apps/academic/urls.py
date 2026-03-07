# apps/academic/urls.py
print(">>>> REGISTRANDO URLS ACADEMICAS <<<<")
from django.urls import path
from . import views

app_name = 'academic'

urlpatterns = [
    # --- 1. PORTAL ACADÉMICO (Dashboard Unificada) ---
    path('dashboard/', views.student_dashboard, name='student_dashboard'),

    # --- 2. GESTÃO DE NOTAS (Unificadas com Suporte a 3 Trimestres) ---
    # Nota: Mantemos o nome 'grading_sheet' que o template academic_page.html usa
    path('grading/class/<int:class_id>/subject/<int:subject_id>/', views.class_grading_sheet, name='grading_sheet_default'),
    path('grading/class/<int:class_id>/subject/<int:subject_id>/<int:term>/', views.class_grading_sheet, name='grading_sheet'),
    
    # Lançamento em Massa
    path('mass-entry/<int:allocation_id>/<int:term>/', views.mass_grade_entry, name='mass_grade_entry'),
    
    # Motor AJAX de Salvamento
    path('grading/update-ajax/', views.update_grade_ajax, name='update_grade_ajax'),
    path('grading/update-inline/<int:grade_id>/', views.update_grade_inline, name='update_grade_inline'),

    # --- 3. GESTÃO DE VAGAS (Unificada do Core para o Academic) ---
    # O nome 'manage_vacancy_request' é o que usamos no botão do academic_page.html
    path('vacancy/manage/<int:vacancy_id>/', views.manage_vacancy_request, name='manage_vacancy_request'),

    path('messenger/mass-promotion-alert/', views.mass_whatsapp_promotion_alert, name='mass_whatsapp_promotion_alert'),
    
    # --- 4. ANALYTICS E BLOQUEIO (Corrigido: URLs únicas) ---
    path('analytics/efficiency/', views.academic_efficiency_dashboard, name='efficiency_dashboard'),
    path('analytics/efficiency/export-pdf/', views.export_efficiency_report_pdf, name='export_efficiency_pdf'),
    path('analytics/toggle-break/', views.toggle_pedagogical_break, name='toggle_pedagogical_break'),

    # --- 5. CONFIGURAÇÃO DE ANOS LETIVOS ---
    path('years/', views.academic_year_list, name='year_list'),
    path('years/activate/<int:year_id>/', views.academic_year_activate, name='year_activate'),
    path('years/deactivate/<int:year_id>/', views.academic_year_deactivate, name='year_deactivate'),
    path('years/delete/<int:year_id>/', views.academic_year_delete, name='year_delete'),

    path('courses/', views.CourseListView.as_view(), name='course_list'),
    path('courses/add/', views.CourseCreateView.as_view(), name='course_create'),
    
    path('grade-levels/', views.GradeLevelListView.as_view(), name='grade_level_list'),
    
    path('classes/', views.ClassListView.as_view(), name='class_list'),
    path('classes/add/', views.ClassCreateView.as_view(), name='class_create'),

    # --- 6. EXPORTAÇÕES (Sincronizadas com Rigor) ---
    path('class/<int:class_id>/pauta/excel/', views.export_class_pauta_excel, name='export_class_pauta_excel'),
    path('export/pauta/pdf/<int:class_id>/', views.download_pauta_pdf, name='download_pauta_pdf'),
    
    # --- 7. PLANOS DE AULA ---
    path('lesson-plan/create/', views.create_lesson_plan, name='create_lesson_plan'),

    path('attendance/control/<int:allocation_id>/', views.daily_attendance_control, name='daily_attendance'),
    path('attendance/report/pdf/<int:allocation_id>/', views.export_attendance_pdf, name='export_attendance_pdf'),

    path('export/minipauta/<int:allocation_id>/<int:term>/', views.export_minipauta_view, name='export_minipauta'),

    path('export/final-pauta/<int:class_id>/', views.export_final_pauta_excel, name='export_final_pauta_excel'),

    path('pauta-final/<int:class_id>/', views.final_pauta_view, name='final_pauta_view'),

    path('promote/class/<int:class_id>/', views.bulk_promote_students, name='bulk_promote'),
]