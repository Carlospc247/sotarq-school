# apps/finance/templatetags/finance_extras.py
from django import template
from apps.finance.services import PenaltyEngine

register = template.Library()

@register.filter
def updated_total(invoice):
    """Uso: {{ invoice|updated_total }}"""
    _, _, total = PenaltyEngine.calculate_invoice_mora(invoice)
    return total