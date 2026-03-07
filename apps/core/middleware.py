# apps/core/middleware.py

from django.utils import timezone
from django.shortcuts import redirect, render
from django.conf import settings
from django.urls import NoReverseMatch, reverse
from django_tenants.utils import schema_context
from apps.academic.models import AcademicYear
from apps.academic.views import is_manager_check
from apps.finance.apps import FinanceConfig
from apps.licenses.models import License
from django.shortcuts import redirect
from django.http import HttpResponse
from django_tenants.middleware.main import TenantMainMiddleware
from django.db import connection
from django.contrib import messages
from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from apps.academic.models import AcademicYear
from apps.finance.models import FinanceConfig # Certifique-se que o modelo existe
from django.urls import reverse




class LicenseCheckMiddleware:
    """
    CAMADA 1: SOTARQ vs ESCOLA.
    Bloqueio total se a instituição não tiver licença ativa no PUBLIC.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Ignora o esquema public
        if not hasattr(request, 'tenant') or request.tenant.schema_name == 'public':
            return self.get_response(request)

        # 2. Isenção apenas para recursos críticos de infraestrutura
        exempt_prefixes = ['/static/', '/media/', '/billing/']
        if any(request.path.startswith(url) for url in exempt_prefixes):
            return self.get_response(request)

        # 3. Verificação de Licença no Contexto PUBLIC
        has_valid_license = False
        license_obj = None

        with schema_context('public'):
            try:
                # Busca a licença ativa mais recente
                license_obj = License.objects.filter(
                    tenant=request.tenant, 
                    is_active=True
                ).latest('created_at')
                
                if license_obj.expiry_date >= timezone.now().date():
                    has_valid_license = True
            except Exception:
                license_obj = None

        # 4. Bloqueio Absoluto
        if not has_valid_license:
            # Bypass apenas para Superuser (Equipa SOTARQ - suporte técnico)
            if request.user.is_authenticated and request.user.is_superuser:
                return self.get_response(request)

            # Ninguém passa. Nem login, nem dashboard. Bloqueio total na raiz.
            return render(request, 'errors/license_expired.html', {
                'message': "O acesso a esta plataforma foi suspenso pela administração do SOTARQ por falta de licença válida.",
                'tenant': request.tenant,
            }, status=403)

        return self.get_response(request)


class SuspensionMiddleware:
    """
    CAMADA 2: ESCOLA vs ALUNO/ENCARREGADO.
    Bloqueio interno por motivos disciplinares ou financeiros (Propinas).
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not hasattr(request, 'tenant') or request.tenant.schema_name == 'public':
            return self.get_response(request)

        # Se o utilizador está logado e não é da equipa de gestão (Staff/Admin)
        if request.user.is_authenticated and not request.user.is_staff:
            try:
                # Verifica Alunos e Encarregados vinculados
                # Assumimos que o perfil do aluno tem 'is_suspended' ou 'is_financially_blocked'
                if hasattr(request.user, 'student_profile'):
                    student = request.user.student_profile
                    
                    # Bloqueio disciplinar OU financeiro (Dívida de Propinas)
                    if student.is_suspended or getattr(student, 'is_financially_blocked', False):
                        if not request.path.startswith('/static/') and 'logout' not in request.path:
                            return render(request, 'core/suspended.html', {
                                'student': student,
                                'reason': "Financeira" if getattr(student, 'is_financially_blocked', False) else "Disciplinar"
                            }, status=403)
                
                # Lógica para Encarregados (se estiverem vinculados ao estado financeiro do aluno)
                elif hasattr(request.user, 'guardian_profile'):
                    # Se algum dos educandos do encarregado estiver bloqueado financeiramente
                    if request.user.guardian_profile.has_debt_block:
                         if not request.path.startswith('/static/') and 'logout' not in request.path:
                            return render(request, 'core/suspended.html', {
                                'reason': "Financeira (Pendente de Regularização)"
                            }, status=403)

            except Exception:
                pass
                    
        return self.get_response(request)



class SOTARQSecurityMiddleware:
    """Rigor de Interdição: Bloqueia acesso se houver fraude detectada."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            # Acessando o seu profile através da OneToOneField que você criou
            student_profile = getattr(request.user, 'student_profile', None)
            
            if student_profile and student_profile.is_blocked_for_fraud:
                # Se estiver bloqueado e tentar acessar algo que não seja a página de aviso
                allowed_paths = [reverse('portal:blocked_page'), reverse('logout')]
                if request.path not in allowed_paths:
                    return redirect('portal:blocked_page')
        
        return self.get_response(request)



# MIDDLEWARE para exibir mensagem se o domínio digitado não existir


class SotarqTenantMiddleware(TenantMainMiddleware):
    """
    Rigor SOTARQ: Captura falhas de domínio e exibe 
    uma mensagem amigável em vez de erro 500.
    """
    def process_request(self, request):
        try:
            super().process_request(request)
        except Exception:
            # Se o domínio não existir, redireciona para o portal principal
            # ou exibe uma página de erro customizada
            return HttpResponse(
                "<h1>🏫 SOTARQ SCHOOL: Instituição não encontrada</h1>"
                "<p>O endereço digitado não corresponde a nenhuma escola ativa em nossa rede.</p>", 
                status=404
            )


class CriticalConfigCheckMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # 1. Filtro de Elite: Só verifica Staff/Admin logados
        if request.user.is_authenticated and request.user.is_staff:
            
            # 2. Definição de Caminhos Isentos (Prevenção de Loop Infinito)
            try:
                wizard_url = reverse('core:setup_wizard')
            except NoReverseMatch:
                wizard_url = '/settings/setup/' # Fallback manual

            exempt_paths = [
                '/admin/',
                '/logout/',
                '/static/',
                '/media/',
                wizard_url,
            ]

            # Se o utilizador estiver a navegar em caminhos isentos, deixa passar
            if any(request.path.startswith(path) for path in exempt_paths):
                return self.get_response(request)

            # 3. Verificação Rigorosa (Base de Dados)
            has_year = AcademicYear.objects.filter(is_active=True).exists()
            has_finance = FinanceConfig.objects.exists()

            # 4. Bloqueio e Redirecionamento
            if not has_year or not has_finance:
                # Mensagem de alerta apenas se ainda não estiver no Wizard
                if request.path != wizard_url:
                    messages.error(request, "BLOQUEIO DE SEGURANÇA: Configure um Ano Letivo Ativo e as Regras de Multas.")
                return redirect(wizard_url)

        return self.get_response(request)

