# apps/billing/services.py
import requests
from django.utils import timezone
from dateutil.relativedelta import relativedelta
from apps.licenses.models import License






def initiate_saas_payment(invoice):
    gateway_url = "https://api.gateway.com/v1/payments"
    # Defina os headers como um dicionário real
    headers = {
        "Authorization": "Bearer SEU_TOKEN_AQUI",
        "Content-Type": "application/json"
    }
    payload = {
        "amount": str(invoice.amount),
        "currency": "AOA",
        "external_reference": invoice.reference,
        "callback_url": "https://sotarqschool.com/billing/webhook/"
    }

    response = requests.post(gateway_url, json=payload, headers=headers)
    invoice.payment_url = response.json().get('payment_link')
    invoice.save()
    
    return invoice.payment_url


def process_license_renewal(tenant, months=1):
    """
    Lógica única de renovação de licença para todo o ecossistema Sotarq.
    """
    lic, created = License.objects.get_or_create(
        tenant=tenant,
        is_active=True,
        defaults={'expiry_date': timezone.now().date()}
    )
    
    # Lógica inteligente: soma ao prazo restante ou a partir de hoje
    base_date = max(lic.expiry_date, timezone.now().date())
    lic.expiry_date = base_date + relativedelta(months=months)
    lic.save()
    return lic


