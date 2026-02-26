# apps/reports/finance/utils_reports.py
import os
from io import BytesIO
from django.conf import settings
from django.utils import timezone
from django.db.models import Sum
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors

class CashClosingReport:
    """
    Motor Supremo de Auditoria SOTARQ ENTERPRISE.
    Unifica: Saldo Inicial + Entradas Cash - Sangrias = Saldo Esperado.
    """
    @staticmethod
    def generate_daily_closing(session, payments, user, totals):
        buffer = BytesIO()
        p = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        # 1. CABEÇALHO INSTITUCIONAL SOTARQ
        p.setFont("Helvetica-Bold", 16)
        p.drawString(2*cm, height-2*cm, "RELATÓRIO DE FECHO DE CAIXA")
        p.setFont("Helvetica", 10)
        p.drawString(2*cm, height-2.6*cm, f"Operador: {user.get_full_name()} | Data: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
        p.line(2*cm, height-2.8*cm, 19*cm, height-2.8*cm)

        # 2. RESUMO DE CONSOLIDAÇÃO FINANCEIRA (RIGOR MATEMÁTICO)
        y = height - 4.5*cm
        p.setFont("Helvetica-Bold", 11)
        p.drawString(2*cm, y, "RESUMO DE CONSOLIDAÇÃO FINANCEIRA")
        
        y -= 0.8*cm
        p.setFont("Helvetica", 10)
        
        # Fundo de Maneio
        p.drawString(2.5*cm, y, "(+) FUNDO DE MANEIO (ABERTURA)")
        p.drawRightString(18.5*cm, y, f"{session.opening_balance:,.2f} Kz")
        
        # Entradas em Cash
        y -= 0.6*cm
        cash_in = totals.get('CH', 0)
        p.drawString(2.5*cm, y, "(+) VENDAS / RECEBIMENTOS EM DINHEIRO")
        p.drawRightString(18.5*cm, y, f"{cash_in:,.2f} Kz")

        # Suprimentos (Aporte de troco)
        y -= 0.6*cm
        total_inflows = session.inflows.aggregate(Sum('amount'))['amount__sum'] or 0
        p.drawString(2.5*cm, y, "(+) SUPRIMENTOS / REFORÇOS DE CAIXA")
        p.drawRightString(18.5*cm, y, f"{total_inflows:,.2f} Kz")

        # Sangrias (Saídas)
        y -= 0.6*cm
        total_outflows = session.outflows.aggregate(Sum('amount'))['amount__sum'] or 0
        p.setFillColor(colors.red)
        p.drawString(2.5*cm, y, "(-) SANGRIA / SAÍDAS DE CAIXA")
        p.drawRightString(18.5*cm, y, f"- {total_outflows:,.2f} Kz")
        p.setFillColor(colors.black)

        # CÁLCULO DO SALDO ESPERADO EM ESPÉCIE
        # (Abertura + Entradas Dinheiro + Reforços) - Saídas
        expected_cash = (session.opening_balance + cash_in + total_inflows) - total_outflows

        y -= 1.0*cm
        p.line(12*cm, y+0.2*cm, 18.5*cm, y+0.2*cm)
        p.setFillColor(colors.red if expected_cash < 0 else colors.black)
        p.setFont("Helvetica-Bold", 12)
        p.drawString(12*cm, y, "TOTAL ESPERADO EM CAIXA:")
        p.drawRightString(18.5*cm, y, f"{expected_cash:,.2f} Kz")
        p.setFillColor(colors.black)

        # 3. CONSOLIDAÇÃO DE PAGAMENTOS DIGITAIS (TPA/TRANSFERÊNCIA)
        y -= 1.5*cm
        p.setFont("Helvetica-Bold", 11)
        p.drawString(2*cm, y, "MOVIMENTAÇÃO BANCÁRIA (CONCILIAÇÃO)")
        y -= 0.8*cm
        p.setFont("Helvetica", 10)
        
        digital_methods = [
            ('MULTICAIXA (TPA)', totals.get('MC', 0)),
            ('TRANSFERÊNCIA BANCÁRIA', totals.get('TR', 0)),
            ('DEPÓSITO BANCÁRIO', totals.get('DP', 0)),
        ]
        for label, val in digital_methods:
            p.drawString(2.5*cm, y, label)
            p.drawRightString(18.5*cm, y, f"{val:,.2f} Kz")
            y -= 0.6*cm

        # 4. LISTAGEM DETALHADA DAS TRANSAÇÕES (PARA AUDITORIA)
        y -= 1.0*cm
        p.setFont("Helvetica-Bold", 10)
        p.drawString(2*cm, y, "DETALHE DAS TRANSAÇÕES DO DIA")
        y -= 0.6*cm
        p.setFont("Helvetica-Bold", 8)
        p.drawString(2*cm, y, "HORA")
        p.drawString(4*cm, y, "ESTUDANTE")
        p.drawString(12*cm, y, "DOCUMENTO")
        p.drawRightString(18.5*cm, y, "VALOR")
        
        p.setFont("Helvetica", 8)
        for pay in payments:
            y -= 0.5*cm
            if y < 4*cm: # Rigor de Quebra de Página
                p.showPage()
                y = height-2*cm
                p.setFont("Helvetica", 8)
            p.drawString(2*cm, y, pay.confirmed_at.strftime('%H:%M'))
            p.drawString(4*cm, y, pay.invoice.student.full_name[:45].upper())
            p.drawString(12*cm, y, pay.invoice.number)
            p.drawRightString(18.5*cm, y, f"{pay.amount:,.2f}")

        # 5. ÁREA DE ASSINATURA E VALIDACAO
        p.line(3*cm, 3*cm, 8*cm, 3*cm)
        p.drawCentredString(5.5*cm, 2.5*cm, "O Tesoureiro")
        p.line(13*cm, 3*cm, 18*cm, 3*cm)
        p.drawCentredString(15.5*cm, 2.5*cm, "Direcção Financeira")

        p.showPage()
        p.save()
        return buffer.getvalue()