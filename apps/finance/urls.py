# apps/finance/models.py
from django.urls import path

from apps.finance import views, views_admin, views_dashboard, views_reports, views_secretary, views_portal, views_staff


app_name = 'finance'

urlpatterns = [
    # --- INTERFACE DO ALUNO/ENCARREGADO ---
    path('checkout/<int:invoice_id>/', views.checkout_invoice, name='checkout'),
    
    # --- ÁREA DA TESOURARIA (OPERAÇÕES) ---
    path('staff/treasury/', views_staff.treasury_dashboard, name='treasury_dashboard'),
    path('staff/validate-fast/<int:payment_id>/', views_staff.validate_payment_fast, name='validate_payment_fast'),
    
    # --- BUSINESS INTELLIGENCE (DIRETORIA) ---
    path('admin/cash-flow/', views_dashboard.daily_cash_flow, name='daily_cash_flow'),
    path('admin/overview/', views_admin.financial_overview, name='overview'),
    
    # --- EXPORTAÇÃO E CONTABILIDADE ---
    path('reports/monthly-map/', views_reports.generate_monthly_map, name='generate_monthly_map'),
    path('download/report-card/<int:student_id>/', views.download_report_card, name='download_report_card'),

    path('admin/promotion-dashboard/', views_admin.promotion_finance_dashboard, name='promotion_dashboard'),
    
    # Dashboard e Operação
    path('secretary/dashboard/', views_secretary.secretary_finance_dashboard, name='secretary_dashboard'),
    path('budget/proforma/<int:student_id>/', views_secretary.generate_budget_view, name='generate_budget_proforma'),
    path('staff/treasury/', views_staff.treasury_dashboard, name='treasury_dashboard'),
    
    path('admin/budget-approvals/', views_admin.budget_approval_list, name='budget_approval_list'),
    path('admin/budget-discount/<int:proforma_id>/', views_admin.apply_budget_discount, name='apply_budget_discount'),


    # Validação e Estorno
    path('staff/validate-fast/<int:payment_id>/', views_staff.validate_payment_fast, name='validate_payment_fast'),
    path('staff/reject/<int:payment_id>/', views_staff.reject_payment, name='reject_payment'),
    path('staff/void-payment/<int:payment_id>/', views_staff.void_payment_action, name='void_payment'),
    
    # Motor de Mora e Perdão
    path('staff/waive-penalty/<int:invoice_id>/', views_staff.waive_penalty_action, name='waive_penalty'),
    
    # Ciclo de Caixa (Abertura e Fecho)
    path('cash/open/', views_secretary.open_cash_daily, name='open_cash_daily'),
    path('cash/close/', views_secretary.close_cash_daily, name='close_cash_daily'),

    path('cash/sangria/', views_secretary.process_sangria, name='process_sangria'),
    path('cash/suprimento/', views_secretary.process_suprimento, name='process_suprimento'),

    # apps/finance/urls.py
    path('staff/fraud-report/', views_staff.fraud_report_list, name='fraud_report'),
    path('staff/unblock-fraud/<int:student_id>/', views_staff.unblock_student_fraud, name='unblock_student_fraud'),

    # apps/portal/urls.py
    path('security/interdiction/', views_portal.blocked_page, name='blocked_page'),

    # Finance BI
    path('api/bi/monthly-stats/', views_admin.finance_bi_monthly_data, name='api_bi_monthly_stats'),
   
    path('api/bi/payment-methods/', views_admin.finance_bi_payment_methods, name='api_bi_payment_methods'),

    path('checkout/<int:invoice_id>/', views.checkout_invoice, name='checkout'),

    path('invoices/', views.invoice_list, name='invoice_list'),
    path('invoice/<int:invoice_id>/', views.invoice_detail, name='invoice_detail'),

    # Checkout e Upload de Comprovativo (Portal do Aluno)
    path('upload-proof/<int:invoice_id>/', views_portal.upload_proof, name='upload_proof'),
]