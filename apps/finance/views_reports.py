# apps/finance/views_reports.py
from django.shortcuts import render
import matplotlib
from django.contrib.auth.decorators import login_required
from apps.core.models import SchoolConfiguration
matplotlib.use('Agg') # Necessário para ambientes sem interface gráfica
import matplotlib.pyplot as plt
from io import BytesIO
from django.http import HttpResponse, HttpResponseForbidden
from django.db.models import Sum
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from .models import Invoice, Payment
from apps.reports.services.finance_bi import MonthlyExplorationEngine


"""

def generate_monthly_map(request):

    #PRODUÇÃO: Gera Relatório Consolidado para Contabilidade com Gráficos BI.

    month = request.GET.get('month', timezone.now().month)
    year = request.GET.get('year', timezone.now().year)
    
    # 1. Agregação de Dados
    receita_total = Invoice.objects.filter(issue_date__month=month, issue_date__year=year).aggregate(Sum('total'))['total__sum'] or 0
    receita_paga = Payment.objects.filter(confirmed_at__month=month, confirmed_at__year=year, validation_status='validated').aggregate(Sum('amount'))['amount__sum'] or 0
    inadimplencia = receita_total - receita_paga

    # 2. Geração do Gráfico de Pizza (Donut Style - Mais elegante)
    plt.figure(figsize=(6, 4))
    labels = ['Liquidado', 'Em Dívida']
    values = [float(receita_paga), float(inadimplencia)]
    colors_list = ['#10b981', '#ef4444'] # Emerald e Red
    
    fig, ax = plt.subplots()
    ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, colors=colors_list, pctdistance=0.85)
    # Desenha um círculo branco no meio para transformar em Donut
    centre_circle = plt.Circle((0,0), 0.70, fc='white')
    fig.gca().add_artist(centre_circle)
    
    plt.title(f"Performance Financeira - {month}/{year}", fontsize=12, fontweight='bold')
    plt.axis('equal') 
    
    chart_buffer = BytesIO()
    plt.savefig(chart_buffer, format='png', bbox_inches='tight', dpi=100)
    plt.close()
    chart_buffer.seek(0)

    # 3. Construção do PDF (Mapa de Exploração)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Mapa_Mensal_{month}_{year}.pdf"'
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Identidade Institucional
    p.setFont("Helvetica-Bold", 14)
    p.drawString(2*cm, height-2*cm, f"RELATÓRIO MENSAL FINANCEIRO - {request.tenant.name.upper()}")
    p.setFont("Helvetica", 9)
    p.drawString(2*cm, height-2.6*cm, f"Gerado para Contabilidade em: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    p.line(2*cm, height-2.8*cm, 19*cm, height-2.8*cm)

    # Inserir Gráfico
    p.drawImage(ImageReader(chart_buffer), 4*cm, height-11*cm, width=13*cm, preserveAspectRatio=True)

    # Resumo Executivo
    y_pos = height-11.5*cm
    p.setFont("Helvetica-Bold", 11)
    p.drawString(2*cm, y_pos, "SUMÁRIO DO PERÍODO")
    p.line(2*cm, y_pos-0.2*cm, 6*cm, y_pos-0.2*cm)
    
    p.setFont("Helvetica", 10)
    p.drawString(2*cm, y_pos-1*cm, f"Total Faturado no Mês:")
    p.drawRightString(19*cm, y_pos-1*cm, f"{receita_total:,.2f} Kz")
    
    p.setFillColor(colors.green)
    p.drawString(2*cm, y_pos-1.6*cm, f"Total Cobrado (Eficiência):")
    p.drawRightString(19*cm, y_pos-1.6*cm, f"{receita_paga:,.2f} Kz")
    
    p.setFillColor(colors.red)
    p.drawString(2*cm, y_pos-2.2*cm, f"Inadimplência Gerada:")
    p.drawRightString(19*cm, y_pos-2.2*cm, f"{inadimplencia:,.2f} Kz")
    
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width/2, 2*cm, "Este documento é gerado automaticamente e serve apenas para fins de análise interna e contabilidade.")

    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    return response

"""




def generate_monthly_map(request):
    """
    PRODUÇÃO: Gera Relatório Consolidado para Contabilidade com Gráficos BI.
    Rigor: Proteção contra NaN e Layout Donut Style.
    """
    # 1. Parâmetros e Agregação de Dados
    month = request.GET.get('month', timezone.now().month)
    year = request.GET.get('year', timezone.now().year)
    
    receita_total = Invoice.objects.filter(
        issue_date__month=month, 
        issue_date__year=year
    ).aggregate(Sum('total'))['total__sum'] or 0
    
    receita_paga = Payment.objects.filter(
        confirmed_at__month=month, 
        confirmed_at__year=year, 
        validation_status='validated'
    ).aggregate(Sum('amount'))['amount__sum'] or 0
    
    inadimplencia = receita_total - receita_paga

    # 2. Geração do Gráfico (Rigorosa contra erro NaN)
    chart_buffer = None
    if receita_total > 0:
        plt.figure(figsize=(6, 4))
        labels = ['Liquidado', 'Em Dívida']
        
        # Garantia de valores para o motor do Matplotlib
        val_pago = float(max(0, receita_paga))
        val_divida = float(max(0, inadimplencia))
        values = [val_pago, val_divida]
        
        colors_list = ['#10b981', '#ef4444'] # Emerald e Red (SOTARQ Standard)
        
        fig, ax = plt.subplots()
        if sum(values) > 0:
            ax.pie(values, labels=labels, autopct='%1.1f%%', startangle=90, 
                   colors=colors_list, pctdistance=0.85)
            
            # Desenha o círculo central para efeito Donut
            centre_circle = plt.Circle((0,0), 0.70, fc='white')
            fig.gca().add_artist(centre_circle)
            
            plt.title(f"Performance Financeira - {month}/{year}", fontsize=12, fontweight='bold')
            plt.axis('equal') 
            
            chart_buffer = BytesIO()
            plt.savefig(chart_buffer, format='png', bbox_inches='tight', dpi=100)
            plt.close('all') 
            chart_buffer.seek(0)

    # 3. Construção do PDF (Mapa de Exploração)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="Mapa_Mensal_{month}_{year}.pdf"'
    
    buffer = BytesIO()
    p = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # Identidade Institucional
    p.setFont("Helvetica-Bold", 14)
    p.drawString(2*cm, height-2*cm, f"RELATÓRIO MENSAL FINANCEIRO - {request.tenant.name.upper()}")
    
    p.setFont("Helvetica", 9)
    p.drawString(2*cm, height-2.6*cm, f"Gerado para Contabilidade em: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    p.line(2*cm, height-2.8*cm, 19*cm, height-2.8*cm)

    # Inserção do Gráfico ou Mensagem de Fallback
    if chart_buffer:
        p.drawImage(ImageReader(chart_buffer), 4*cm, height-11*cm, width=13*cm, preserveAspectRatio=True)
    else:
        p.setFont("Helvetica-Oblique", 11)
        p.setFillColor(colors.grey)
        p.drawCentredString(width/2, height-7*cm, "SEM MOVIMENTAÇÃO FINANCEIRA REGISTADA NESTE PERÍODO")
        p.setFillColor(colors.black)

    # Resumo Executivo
    y_pos = height-11.5*cm
    p.setFont("Helvetica-Bold", 11)
    p.drawString(2*cm, y_pos, "SUMÁRIO DO PERÍODO")
    p.line(2*cm, y_pos-0.2*cm, 6*cm, y_pos-0.2*cm)
    
    p.setFont("Helvetica", 10)
    p.drawString(2*cm, y_pos-1*cm, "Total Faturado no Mês:")
    p.drawRightString(19*cm, y_pos-1*cm, f"{receita_total:,.2f} Kz")
    
    p.setFillColor(colors.green)
    p.drawString(2*cm, y_pos-1.6*cm, "Total Cobrado (Eficiência):")
    p.drawRightString(19*cm, y_pos-1.6*cm, f"{receita_paga:,.2f} Kz")
    
    p.setFillColor(colors.red)
    p.drawString(2*cm, y_pos-2.2*cm, "Inadimplência Gerada:")
    p.drawRightString(19*cm, y_pos-2.2*cm, f"{inadimplencia:,.2f} Kz")
    
    # Rodapé Legal
    p.setFillColor(colors.black)
    p.setFont("Helvetica-Oblique", 8)
    p.drawCentredString(width/2, 2*cm, "Este documento é gerado automaticamente pelo SOTARQ SCHOOL e serve para fins de análise interna.")

    p.showPage()
    p.save()
    
    pdf = buffer.getvalue()
    buffer.close()
    response.write(pdf)
    
    return response


@login_required
def generate_detailed_exploration_map(request):
    """Visualização manual do mapa para o Diretor Financeiro."""
    if not request.user.current_role in ['ADMIN', 'DIRECTOR', 'DIRECT_FINANC']:
        return HttpResponseForbidden("Acesso negado.")

    month = request.GET.get('month', timezone.now().month)
    year = request.GET.get('year', timezone.now().year)
    
    # Chama o motor que agora está na app 'reports'
    data = MonthlyExplorationEngine.get_monthly_summary(month, year, request.tenant.schema_name)
    
    return render(request, 'finance/reports/exploration_map.html', {
        'data': data,
        'config': SchoolConfiguration.objects.first()
    })

