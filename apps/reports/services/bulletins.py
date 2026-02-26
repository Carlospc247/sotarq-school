# apps/reports/services/bulletins.py

from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from django.utils import timezone
from django.conf import settings
from weasyprint import HTML

from apps.students.models import Student
from apps.academic.models import Class, StudentGrade
from apps.reports.models import ReportExecution, ReportArtifact

def generate_student_bulletin(execution_id, student_id, class_id):
    """
    Gera o Boletim de Notas (PDF) para um aluno específico.
    """
    # 1. Recuperação de Dados
    student = Student.objects.select_related('user').get(id=student_id)
    klass = Class.objects.select_related('academic_year', 'grade_level').get(id=class_id)
    execution = ReportExecution.objects.get(id=execution_id)
    
    grades = StudentGrade.objects.filter(
        student_id=student_id,
        klass_id=class_id
    ).select_related('subject').order_by('subject__name')

    # Recupera o tenant a partir do ano letivo da turma
    tenant = klass.academic_year.tenant

    # 2. Contexto
    context = {
        'student': student,
        'class': klass,
        'grades': grades,
        'academic_year': klass.academic_year,
        'school_name': tenant.name,
        'generated_at': timezone.now(),
        # Se tenant.primary_color falhar, usa preto como fallback
        'primary_color': getattr(tenant, 'primary_color', '#000000'),
    }

    # 3. Renderização HTML
    html_string = render_to_string('reports/pdf/bulletin_template.html', context)

    # 4. Geração do PDF
    # base_url é crucial para carregar imagens/css locais
    html = HTML(string=html_string, base_url=str(settings.BASE_DIR))
    pdf_file = html.write_pdf()

    # 5. Salvar Artefato
    filename = f"Boletim_{klass.academic_year.name}_{student.process_number}.pdf"
    
    artifact = ReportArtifact(
        execution=execution,
        format='pdf',
        is_notified=False
    )
    artifact.file.save(filename, ContentFile(pdf_file), save=True)
    
    return artifact




