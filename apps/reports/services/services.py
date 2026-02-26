# Em vez de apenas gerar um arquivo, este serviço extrai os dados da apps.academic, gera o HTML, converte para PDF e aplica o QR Code de autenticação da apps.documents.
# apps/reports/services.py
import os
import tempfile
from django.template.loader import render_to_string
from django.core.files.base import ContentFile
from apps.academic.models import StudentGrade, Enrollment
from apps.documents.models import Document, DocumentType
from apps.documents.services import stamp_qr_on_pdf
import weasyprint

from apps.reports.models import ReportArtifact, ReportExecution
from apps.reports.tasks import task_send_whatsapp_notification # Recomendo para converter HTML em PDF profissional

def generate_student_bulletin(execution_id, student_id, class_id):
    execution = ReportExecution.objects.get(id=execution_id)
    enrollment = Enrollment.objects.get(student_id=student_id, class_room_id=class_id)
    config = SchoolConfiguration.objects.first()
    
    quarter = config.current_quarter # 1, 2 ou 3
    quarter_label = config.get_current_quarter_display() # "1º Trimestre", etc.

    # 1. Extração de Dados
    grades = StudentGrade.objects.filter(
        student_id=student_id, 
        klass_id=class_id
    ).select_related('subject')

    context = {
        'student': enrollment.student,
        'klass': enrollment.class_room,
        'grades': grades,
        'school_name': config.school_name,
        'year': enrollment.class_room.academic_year.name,
        'quarter_label': quarter_label, # Dinâmico para o Template
        'quarter': quarter,
    }

    # 2. Geração do PDF
    html_string = render_to_string('reports/pdf/bulletin_template.html', context)
    pdf_buffer = weasyprint.HTML(string=html_string).write_pdf()

    # 3. Documento & QR
    doc_type, _ = DocumentType.objects.get_or_create(name=f"Boletim {quarter_label}")
    document = Document.objects.create(student=enrollment.student, document_type=doc_type)

    # 4. Arquivo Temporário Seguro
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(pdf_buffer)
        temp_path = tmp.name

    try:
        final_pdf_buffer = stamp_qr_on_pdf(temp_path, document.qr_code.path)

        # 5. Persistência
        artifact = ReportArtifact.objects.create(execution=execution, format='pdf')
        filename = f"Boletim_{quarter}_{enrollment.student.registration_number}.pdf"
        
        artifact.file.save(filename, ContentFile(final_pdf_buffer.read()))
        document.file.save(filename, ContentFile(final_pdf_buffer.getvalue()))

        # 6. GATILHO SOTARQ CONNECT (Agora com Trimestre Dinâmico)
        message_text = (
            f"Olá! O Boletim de {enrollment.student.full_name} referente ao {quarter_label} "
            f"já está disponível no Portal do Aluno."
        )
        task_send_whatsapp_notification.delay(student_id=student_id, message_text=message_text)

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)

    return artifact

