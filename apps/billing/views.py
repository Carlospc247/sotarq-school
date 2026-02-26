# apps/billing/views.py
import json
from pyexpat.errors import messages
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.customers.models import SubAgent
from .models import SaaSInvoice
from .utils import is_valid_webhook_signature
from .services import process_license_renewal
from apps.licenses.models import License
from apps.audit.models import AuditLog




@csrf_exempt
def billing_webhook(request):
    """
    Motor Universal de Webhooks SOTARQ.
    Gere Gateways Internacionais (JSON) e EMIS/GPO (POST).
    """
    if request.method != 'POST':
        return HttpResponse(status=405)

    # 1. Identificação de Origem e Extração de Dados
    content_type = request.headers.get('Content-Type', '')
    
    if 'application/json' in content_type:
        # Fluxo Internacional (Stripe/Global)
        try:
            payload = request.body
            signature = request.headers.get('X-Gateway-Signature')
            if not is_valid_webhook_signature(payload, signature):
                return HttpResponse(status=403)
            
            data = json.loads(payload)
            reference = data.get('external_reference') or data.get('id')
            status_code = data.get('status')
            is_success = status_code in ['paid', 'succeeded', 'completed']
        except Exception:
            return HttpResponse(status=400)
    else:
        # Fluxo EMIS/GPO (Angola)
        data = request.POST
        reference = data.get('TransactionID')
        status_code = data.get('ResponseCode')
        signature = data.get('Signature')
        
        # Rigor: Validação de Assinatura EMIS
        payload_para_validar = f"{reference}{data.get('Amount')}{status_code}"
        if not is_valid_webhook_signature(payload_para_validar.encode(), signature):
            return HttpResponse(status=403)
        
        is_success = status_code == '00'

    # 2. Processamento Atómico (Rigor SOTARQ)
    if is_success:
        try:
            with transaction.atomic():
                # select_for_update() impede que outro processo mexa nesta fatura
                invoice = SaaSInvoice.objects.select_for_update().get(
                    reference=reference, 
                    status='pending'
                )
                
                invoice.status = 'paid'
                invoice.save()

                # Renovação Inteligente (Soma ao prazo ou hoje)
                lic = process_license_renewal(invoice.tenant, months=1)

                # Rastro de Auditoria Global (Para o Painel do Dono)
                AuditLog.objects.create(
                    user=None, # Webhook é um processo de sistema
                    action='BILLING_SUCCESS',
                    content_type_id=None, # Log de sistema
                    object_id=str(invoice.id),
                    details=json.dumps({
                        'tenant': invoice.tenant.name,
                        'reference': reference,
                        'new_expiry': str(lic.expiry_date)
                    })
                )
                print(f"✅ PAGAMENTO SUCESSO: {invoice.tenant.name} renovado.")
                return HttpResponse("OK", status=200)

        except SaaSInvoice.DoesNotExist:
            return HttpResponse("Invoice Not Found", status=404)
        except Exception as e:
            return HttpResponse(f"Error: {str(e)}", status=400)

    return HttpResponse("Payment Failed or Pending", status=200)


@login_required
def payment_success(request):
    """Página de celebração e redirecionamento pós-pagamento."""
    try:
        # request.tenant injetado pelo middleware de multi-tenant
        license = License.objects.get(tenant=request.tenant, is_active=True)
        return render(request, 'billing/payment_success.html', {
            'new_expiry_date': license.expiry_date
        })
    except License.DoesNotExist:
        return redirect('core:dashboard')



@user_passes_test(lambda u: u.is_superuser)
def agent_commission_manager(request):
    """Interface para o Dono definir as regras de ganhos dos subagentes."""
    if request.method == 'POST':
        agent_id = request.POST.get('agent_id')
        new_pct = request.POST.get('commission_pct')
        agent = get_object_or_404(SubAgent, id=agent_id)
        agent.commission_pct = new_pct
        agent.save()
        messages.success(request, f"Comissão de {agent.user.get_full_name()} atualizada para {new_pct}%.")

    agents = SubAgent.objects.all().select_related('user')
    # Faturas em massa para auditoria global
    invoices = SaaSInvoice.objects.all().select_related('tenant__sub_agent__user').order_by('-created_at')[:1000]

    return render(request, 'platform/agent_commissions.html', {
        'agents': agents,
        'invoices': invoices
    })

