# apps/transport/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Bus, BusRoute, TransportEnrollment, BusEvent
from .services import TransportService
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from django.http import HttpResponse, JsonResponse
from apps.students.models import Student
from django.db import models
import io
from django.http import FileResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.units import cm





@login_required
def transport_dashboard(request):
    """Painel de comando com integração real de dados."""
    buses = Bus.objects.filter(is_active=True).annotate(
        current_passengers=models.Count(
            'busroute__transportenrollment', 
            filter=models.Q(busroute__transportenrollment__is_active=True)
        )
    )
    
    # 1. RADAR LATERAL: Apenas os 10 movimentos mais recentes
    recent_events = BusEvent.objects.select_related('student', 'bus').all()[:10]
    
    # 2. MODAL DE HISTÓRICO: Buscamos os últimos 100 registros reais do banco
    # Usamos select_related para carregar Aluno e Autocarro de uma só vez
    all_events = BusEvent.objects.select_related('student', 'bus').all()[:100]
    
    return render(request, 'transport/dashboard.html', {
        'buses': buses,
        'recent_events': recent_events,
        'all_events': all_events,  # Este dado alimenta o <tbody> do seu modal
        'total_revenue': TransportEnrollment.objects.filter(is_active=True).aggregate(
            total=models.Sum('zone__monthly_fee'))['total'] or 0
    })

# 3. VIEW PARA GERAR O PDF REAL
@login_required
def export_history_pdf(request):
    from django.template.loader import render_to_string
    from weasyprint import HTML
    
    # Busca dados reais para o documento oficial
    events = BusEvent.objects.select_related('student', 'bus').all()[:500]
    
    html_string = render_to_string('transport/pdf/history_report.html', {
        'events': events,
        'school_name': request.tenant.name,
        'generated_at': timezone.now()
    })
    
    pdf = HTML(string=html_string).write_pdf()
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="relatorio_frota_sotarq.pdf"'
    return response



@login_required
def export_history_pdf(request):
    """
    Geração Programática de PDF (Rigor SOTARQ - Alta Performance).
    """
    # 1. Configuração do Buffer e do Documento
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4,
        rightMargin=1.5*cm, leftMargin=1.5*cm,
        topMargin=1.5*cm, bottomMargin=1.5*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # 2. Estilos Personalizados
    title_style = ParagraphStyle(
        'SotarqTitle',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=colors.HexColor("#1e293b"),
        alignment=1, # Centralizado
        spaceAfter=10
    )
    
    # 3. Cabeçalho do Relatório
    school_name = getattr(request.tenant, 'name', 'SOTARQ SCHOOL')
    elements.append(Paragraph(school_name.upper(), title_style))
    elements.append(Paragraph("Relatório de Movimentação de Frota", styles['Heading3']))
    elements.append(Paragraph(f"Gerado em: {timezone.now().strftime('%d/%m/%Y %H:%M')}", styles['Normal']))
    elements.append(Spacer(1, 0.5*cm))

    # 4. Preparação dos Dados da Tabela
    # Cabeçalho da Tabela
    data = [["DATA/HORA", "ESTUDANTE", "MOVIMENTO", "AUTOCARRO"]]
    
    # Busca dados reais usando Rigor de Performance
    events = BusEvent.objects.select_related('student', 'bus').all()[:500]
    
    for event in events:
        data.append([
            event.timestamp.strftime('%d/%m/%Y %H:%M'),
            event.student.full_name[:30], # Truncamento para não quebrar layout
            event.get_event_type_display(),
            event.bus.plate_number
        ])

    # 5. Construção e Estilização da Tabela
    # Definimos as larguras das colunas para preencher o A4 (18cm úteis aprox)
    t = Table(data, colWidths=[3.5*cm, 8*cm, 3.5*cm, 3*cm])
    
    t_style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#4f46e5")), # Header Indigo
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]) # Zebra style
    ])
    t.setStyle(t_style)
    elements.append(t)

    # 6. Finalização
    doc.build(elements)
    buffer.seek(0)
    
    return FileResponse(
        buffer, 
        as_attachment=True, 
        filename=f"historico_frota_{timezone.now().strftime('%Y%m%d')}.pdf"
    )


@login_required
def transport_analytics_report(request):
    """
    Relatório de BI para a Direção: Eficiência da Frota.
    """
    # 1. Métrica de Ocupação por Autocarro
    # No transport_analytics_report:
    buses_efficiency = Bus.objects.filter(is_active=True).annotate(
        total_students=Count('busroute__transportenrollment', filter=Q(busroute__transportenrollment__is_active=True)),
    )

    # 2. Análise de Pontualidade (Eventos na última semana)
    last_week = timezone.now() - timedelta(days=7)
    events_by_driver = BusEvent.objects.filter(timestamp__gte=last_week).values(
        'bus__driver__first_name' # Atravessa Evento -> Autocarro -> Motorista
    ).annotate(
        total_scans=Count('id')
    ).order_by('-total_scans')

    # 3. Alunos que mais utilizam o serviço (Frequência)
    top_users = BusEvent.objects.filter(event_type='IN').values(
        'student__full_name', 'bus__plate_number'
    ).annotate(
        frequency=Count('id')
    ).order_by('-frequency')[:10]

    return render(request, 'transport/analytics.html', {
        'buses': buses_efficiency,
        'driver_stats': events_by_driver,
        'top_users': top_users,
        'report_date': timezone.now()
    })



@login_required
def scan_student_badge(request, bus_id):
    """
    Interface de Scanner para Tablet/Mobile.
    Regista entrada/saída vinculando o motorista atual.
    """
    # Garantimos que o autocarro existe
    bus = get_object_or_404(Bus, id=bus_id)
    
    if request.method == 'POST':
        student_reg = request.POST.get('registration_number')
        event_type = request.POST.get('event_type') # 'IN' ou 'OUT'
        
        try:
            student = Student.objects.get(registration_number=student_reg)
            
            # 1. Criar o Evento com Auditoria Completa
            BusEvent.objects.create(
                student=student,
                bus=bus,
                driver=request.user, # O motorista que fez o scan
                event_type=event_type
            )
            
            # 2. Notificação automática via WhatsApp (O serviço que já tens)
            TransportService.log_event(student.id, bus.id, event_type)
            
            return JsonResponse({
                'status': 'success', 
                'message': f"{student.full_name} registado com sucesso."
            })
            
        except Student.DoesNotExist:
            return JsonResponse({
                'status': 'error', 
                'message': 'QR Code ou Nº de Processo inválido.'
            }, status=404)

    return render(request, 'transport/scanner.html', {'bus': bus})



@login_required
def live_tracking(request, bus_id):
    """Visualização em tempo real do autocarro no mapa."""
    bus = get_object_or_404(Bus, id=bus_id)
    return render(request, 'transport/live_tracking.html', {'bus': bus})

@login_required
def process_checkpoint(request):
    """Endpoint para processar coordenadas enviadas pelo GPS/Tablet."""
    if request.method == 'POST':
        bus_id = request.POST.get('bus_id')
        student_id = request.POST.get('student_id')
        event_type = request.POST.get('event_type')
        coords = {
            'lat': request.POST.get('lat'),
            'lng': request.POST.get('lng')
        }
        
        student = get_object_or_404(Student, id=student_id)
        bus = get_object_or_404(Bus, id=bus_id)
        
        # Chama o motor Elite
        TransportService.process_checkpoint(student, bus, event_type, coords)
        
        return JsonResponse({'status': 'ok'})
    return HttpResponse(status=405)



