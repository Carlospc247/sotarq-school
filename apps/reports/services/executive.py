# apps/reports/services/executive.py
from django.conf import settings
from django.template.loader import render_to_string
from weasyprint import HTML
from apps.academic.models import AcademicYear
from apps.core.models import SchoolConfiguration
from apps.reports.services.kpi_engine import AcademicKPIEngine
from django.core.mail import EmailMessage

def send_monthly_executive_report(tenant):
    """Gera e envia o relatório de BI para o Diretor via E-mail."""
    config = SchoolConfiguration.objects.first()
    if not config or not config.executive_report_emails:
        return
    
    # Converte string "email1, email2" em lista
    email_list = [e.strip() for e in config.executive_report_emails.split(',') if e.strip()]
    
    active_year = AcademicYear.objects.filter(is_active=True).first()
    if not active_year: return

    # 1. Coleta de Dados BI
    engine = AcademicKPIEngine()
    performance = engine.calculate_teacher_performance(active_year.id)
    
    context = {
        'top_performers': sorted(performance, key=lambda x: x['pass_rate'], reverse=True)[:10],
        'alerts': sorted(performance, key=lambda x: x['pass_rate'])[:5],
        'school_name': tenant.name,
        'year': active_year.name,
    }

    # 2. Renderização para PDF
    html_string = render_to_string('reports/pdf/monthly_executive_report.html', context)
    pdf = HTML(string=html_string).write_pdf()

    # 3. Envio de E-mail
    all_recipients = email_list + [tenant.official_email]

    email = EmailMessage(
        subject=f"📊 Relatório Executivo Mensal - {tenant.name}",
        body=f"Saudações, Diretor. Segue em anexo a análise de performance académica de {active_year.name}.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=all_recipients, # Lista unificada e limpa
    )
    email.attach(f"Relatorio_BI_{active_year.name}.pdf", pdf, 'application/pdf')
    email.send()