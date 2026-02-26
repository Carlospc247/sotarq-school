from .base import *


# Segurança relaxada para desenvolvimento
DEBUG = True

# Garante que o Django não tenta ser esperto com o host
USE_X_FORWARDED_HOST = False
SECURE_PROXY_SSL_HEADER = None

# Força o reconhecimento do domínio local
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.localhost', '*']

# Base de Dados Local (Postgres)
DATABASES = {
   'default': {
       'ENGINE': 'django_tenants.postgresql_backend',
       'NAME': 'sotarq_school',
       'USER': 'postgres',
       'PASSWORD': 'postgres', # Sua senha local
       'HOST': 'localhost',
       'PORT': '5432',
   }
}

# Email no Console (Para não enviar spam real durante testes)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Chaves de API falsas para dev
GATEWAY_WEBHOOK_SECRET = 'dev_secret_123'
WHATSAPP_API_TOKEN = 'dev_token_123'
# No teu settings de desenvolvimento (local.py)
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# config/settings/local.py

# Isto obriga o middleware a ignorar a porta na comparação do domínio
# e evita que tenhas de meter :8080 no banco de dados.
TENANT_SUBDOMAIN_RESOURCES_PORT = '8080'