import os
from io import BytesIO
from datetime import datetime
from decimal import Decimal

from django.db import connection
from django.db.models import Avg

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.linecharts import HorizontalLineChart

from apps.academic.models import StudentGrade

def generate_report_card_pdf(student, academic_year, trimester=1):
    """
    Gera Boletins Dinâmicos. 
    O parâmetro 'trimester' (1, 2 ou 3) define quais campos o sistema vai ler.
    """
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    tenant = connection.tenant
    
    # Mapeamento de campos dinâmicos
    mac_field = f"mac{trimester}"
    npp_field = f"npp{trimester}"
    npt_field = f"npt{trimester}"
    mt_field = f"mt{trimester}"

    # --- 1. BRANDING DINÂMICO ---
    primary_color = colors.HexColor(getattr(tenant, 'primary_color', '#1e293b'))
    p.setFillColor(primary_color)
    p.setFont("Helvetica-Bold", 16)
    p.drawString(50, height - 50, tenant.name.upper())
    
    p.setFont("Helvetica-Bold", 11)
    p.drawRightString(width - 50, height - 50, f"BOLETIM: {trimester}º TRIMESTRE")
    p.line(50, height - 75, width - 50, height - 75)

    # --- 2. FILTRAGEM DE DADOS ---
    grades_qs = StudentGrade.objects.filter(
        student=student, 
        klass__academic_year=academic_year
    ).select_related('subject')

    # --- 3. ANALYTICS DINÂMICO (PIZZA) ---
    # O filtro de aprovação agora usa o mt_field dinâmico
    aprovadas = sum(1 for g in grades_qs if getattr(g, mt_field) >= 10)
    reprovadas = sum(1 for g in grades_qs if getattr(g, mt_field) < 10)
    
    d_pie = Drawing(200, 100)
    pc = Pie()
    pc.x, pc.y, pc.width, pc.height = 10, 10, 70, 70
    pc.data = [aprovadas, reprovadas]
    pc.labels = [f'Aprov ({aprovadas})', f'Reprov ({reprovadas})']
    pc.slices[0].fillColor = colors.emerald
    pc.slices[1].fillColor = colors.crimson
    d_pie.add(pc)
    p.drawString(50, height - 140, f"APROVEITAMENTO - {trimester}º TRIM")
    d_pie.drawOn(p, 50, height - 240)

    # --- 4. TABELA DE NOTAS DINÂMICA ---
    # Cabeçalho muda conforme o trimestre
    headers = ['DISCIPLINA', f'MAC {trimester}', f'NPP {trimester}', f'NPT {trimester}', f'MÉDIA {trimester}', 'STATUS']
    table_data = [headers]
    
    for g in grades_qs:
        mac = getattr(g, mac_field)
        npp = getattr(g, npp_field)
        npt = getattr(g, npt_field)
        mt = getattr(g, mt_field)
        
        status = "APROV" if mt >= 10 else "REPROV"
        table_data.append([
            g.subject.name[:25], 
            f"{mac:.1f}", 
            f"{npp:.1f}", 
            f"{npt:.1f}", 
            f"{mt:.1f}", 
            status
        ])

    t = Table(table_data, colWidths=[6*cm, 2*cm, 2*cm, 2*cm, 2*cm, 2.5*cm])
    style = TableStyle([
        ('BACKGROUND', (0,0), (-1,0), primary_color),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ])
    
    # Cores condicionais para as notas na tabela
    for i, row in enumerate(table_data[1:], start=1):
        if float(row[4]) < 10:
            style.add('TEXTCOLOR', (5, i), (5, i), colors.crimson)
        else:
            style.add('TEXTCOLOR', (5, i), (5, i), colors.emerald)

    t.setStyle(style)
    t.wrapOn(p, width, height)
    t.drawOn(p, 50, height - 350 - (len(table_data) * 20))

    # --- 5. FOOTER & SEGURANÇA ---
    p.setFont("Helvetica-Bold", 8)
    p.drawString(50, 50, f"VERIFICAÇÃO: SOT-{student.id}-{academic_year.id}-{trimester}")
    p.drawCentredString(width/2, 20, f"Emitido em: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

    p.showPage()
    p.save()
    return buffer.getvalue()