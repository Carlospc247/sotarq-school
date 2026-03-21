#Sotarq-school/config/base.py
from pathlib import Path
import os
import environ
import sentry_sdk
import cloudinary
import cloudinary.uploader
import cloudinary.api
from sentry_sdk.integrations.django import DjangoIntegration
from celery.schedules import crontab
from dotenv import load_dotenv
import logging
from django_tenants.middleware.main import TenantMainMiddleware


env = environ.Env()


# Carrega o ficheiro .env
load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')
# Carrega a chave privada para a memória
raw_key = os.environ.get('SOTARQ_PRIVATE_KEY', '')
# Corrige as quebras de linha para o formato PEM correto
SOTARQ_PRIVATE_KEY_BYTES = raw_key.replace('\\n', '\n').encode('utf-8')

# Ajuste crítico: Adicionámos mais um .parent porque descemos um nível na pasta
BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False)
)

environ.Env.read_env(BASE_DIR / '.env')

# Chave secreta de fallback (Em produção será substituída)
SENTRY_DSN = env('SENTRY_DSN', default=None)

if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[DjangoIntegration()],
        traces_sample_rate=1.0,
        send_default_pii=True,
    )




def debug_get_tenant(self, domain_model, hostname):
    try:
        # Apenas identificamos o tenant
        tenant = domain_model.objects.select_related('tenant').get(domain=hostname).tenant
        
        # Mantemos o print para debug profissional, mas sem forçar URLCONF aqui
        print(f"\n[ENGINEER_SUCCESS] Conectado ao Tenant: {tenant.schema_name}")
        return tenant
    except domain_model.DoesNotExist:
        return None

# Aplicamos o patch para o debug aparecer no terminal
TenantMainMiddleware.get_tenant = debug_get_tenant



# Application definition
SHARED_APPS = [
    'django_tenants',
    'apps.customers',
    'apps.licenses',
    'apps.plans',
    'apps.billing',
    'apps.platform',
    'apps.keys',
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django_prometheus', # Adicione aqui
    'apps.core',
    'apps.audit',
]

TENANT_APPS = [
    'django.contrib.contenttypes',
    'django.contrib.auth',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.admin',
    'django.contrib.humanize',
    'apps.academic',
    'apps.students',
    'apps.teachers',
    'apps.finance',
    'apps.documents',
    'apps.portal',
    'apps.reports',
    'apps.audit',
    'apps.accounts',
    'apps.saft',
    'apps.fiscal',
    'apps.library',
    'apps.transport',
]

INSTALLED_APPS = list(SHARED_APPS) + [app for app in TENANT_APPS if app not in SHARED_APPS]

TENANT_MODEL = "customers.Client"
TENANT_DOMAIN_MODEL = "customers.Domain"

MIDDLEWARE = [
    #'django_prometheus.middleware.PrometheusBeforeMiddleware', # 1. Métrica começa aqui
    'django_tenants.middleware.main.TenantMainMiddleware',     # 2. IDENTIFICA A ESCOLA (Crucial)
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    
    # Middlewares de Regras de Negócio (Sempre DEPOIS da Autenticação)
    'apps.audit.middleware.AuditMiddleware',
    'apps.core.middleware.LicenseCheckMiddleware',
    'apps.core.middleware.SuspensionMiddleware',
    'apps.academic.middleware.AcademicLockMiddleware',
    
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_prometheus.middleware.PrometheusAfterMiddleware',  # Último
]



CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")

# Config storage default (opcional)
DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"



DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # ADICIONE A LINHA ABAIXO:
                'apps.core.context_processors.school_branding',
                'apps.core.context_processors.active_modules_processor',
                'apps.portal.context_processors.notification_count',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# 1. QUEM pode autenticar (Backends) - ISSO É UMA LISTA DE STRINGS
AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
]

# Isto garante que o utilizador, ao logar no tenant, seja buscado na tabela global
DATABASE_ROUTERS = ('django_tenants.routers.TenantSyncRouter',)

# 2. VALIDAÇÃO DE FORÇA DA SENHA (Validators) - ISSO É UMA LISTA DE DICIONÁRIOS
# Removi o ModelBackend daqui, pois ele NÃO é um validador!
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Configurações de Cookie (Correto para Isolamento)
SESSION_COOKIE_NAME = 'sotarq_sessionid'
SESSION_COOKIE_DOMAIN = None 
SESSION_COOKIE_HTTPONLY = True # Segurança contra ataques XSS


# Internationalization
LANGUAGE_CODE = 'pt-pt'
TIME_ZONE = 'Africa/Luanda'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
AUTH_USER_MODEL = 'core.User'

# Media
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'


CELERY_BEAT_SCHEDULE = {
    'limpar-notificacoes-lidas-mensal': {
        'task': 'apps.core.tasks.cleanup_read_notifications', # Verifique se precisa do 'apps.'
        'schedule': crontab(day_of_month='1', hour=3, minute=0),
    },
    'processar-juros-meia-noite': {
        'task': 'apps.finance.tasks.update_overdue_payments_and_interests',
        'schedule': crontab(hour=0, minute=0),
    },
}

# Configurações SaaS
LOGIN_URL = 'core:login'
LOGIN_REDIRECT_URL = 'core:dashboard'
LOGOUT_REDIRECT_URL = 'core:login'

# Email (Configuração Base)
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
DEFAULT_FROM_EMAIL = 'Sotarq School <notificacoes@sotarq.com>'

# Celery & APIs
CELERY_BROKER_URL = env('CELERY_BROKER_URL')
CELERY_RESULT_BACKEND = env('CELERY_RESULT_BACKEND')

WHATSAPP_API_URL = 'https://api.ultramsg.com/instance123/messages/chat'


# Adicione isto no final do ficheiro em desenvolvimento
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://excellence.local:8080',
    'http://sotarq.local:8080',
    'http://colegiomagno.local:8080',
]

# ==========================================
# CONFIGURAÇÕES AGT / SAF-T (Angola)
# ==========================================

AGT_WEBSERVICE_URL = "https://sifp.minfin.gov.ao/sigt/fe/v1/consultarFactura"
AGT_JWS_SOFTWARE_SIGNATURE = "O_TOKEN_QUE_A_AGT_TE_DARÁ"

# ==========================================
# CONFIGURAÇÕES AGT / FATURAÇÃO ELETRÓNICA
# ==========================================


AGT_ENVIRONMENT = env('AGT_ENVIRONMENT')

AGT_JWS_SOFTWARE_SIGNATURE = env('AGT_JWS_SOFTWARE_SIGNATURE')
AGT_PRODUCER_NIF = env('AGT_PRODUCER_NIF')
AGT_CERTIFICATE_NUMBER = env('AGT_CERTIFICATE_NUMBER')
AGT_SOFTWARE_VERSION= env('AGT_SOFTWARE_VERSION')
AGT_SOFTWARE_NAME= env('AGT_SOFTWARE_NAME')


if AGT_ENVIRONMENT == 'PRODUCTION':
    AGT_BASE_URL = "https://sifp.minfin.gov.ao/sigt/fe/v1"
    AGT_PORTAL_URL = "https://portaldoparceiro.minfin.gov.ao"
else:
    AGT_BASE_URL = "https://sifphml.minfin.gov.ao/sigt/fe/v1"
    AGT_PORTAL_URL = "https://portaldoparceiro.hml.minfin.gov.ao"

# Token JWS fornecido pela AGT (Ficará vazio até você passar nos testes)
AGT_JWS_SOFTWARE_SIGNATURE = os.environ.get("AGT_JWS_SOFTWARE_SIGNATURE", "TOKEN_PENDENTE")

# O django-tenants precisa que tu definas explicitamente que o UnitSelectionMiddleware e outros não devem correr no schema public
TENANT_LIMITER_EXEMPT_VIEWS = [
    'admin:index', 
    'admin:login',
]
ROOT_URLCONF = 'config.urls_public'
PUBLIC_SCHEMA_URLCONF = 'config.urls_public'
TENANT_URLCONF = 'config.urls_tenants'

# 2. Comportamento de Segurança para Domínios Inexistentes
# Se True, evita o erro 'NoneType' e mostra o urls_public
SHOW_PUBLIC_IF_NO_TENANT = True  

# 3. Tratamento de Hostname
REMOVE_PORT_FROM_HOST = True
PUBLIC_SCHEMA_NAME = 'public'
# Impede que scripts maliciosos acedam ao cookie de sessão
SESSION_COOKIE_HTTPONLY = True
# Garante que o CSRF esteja vinculado ao domínio específico
CSRF_COOKIE_DOMAIN = None






# Adicione esta linha para o código da View conseguir ler a variável:
DEFAULT_CANDIDATE_PASSWORD = os.environ.get('DEFAULT_CANDIDATE_PASSWORD')