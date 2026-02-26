from .base import *
import os

DEBUG = False

# Domínios reais do seu negócio (Exemplo)
ALLOWED_HOSTS = ['.sotarqschool.com', '.sotarq.ao', 'sotarq.com']

# A chave secreta vem das variáveis de ambiente do servidor (Segurança Máxima)
SOTARQ_PRIVATE_KEY = os.environ.get('SOTARQ_PRIVATE_KEY')

# Base de Dados de Produção (Lê do ambiente)
DATABASES = {
    'default': {
        'ENGINE': 'django_tenants.postgresql_backend',
        'NAME': os.environ.get('DB_NAME', 'sotarq_school_prod'),
        'USER': os.environ.get('DB_USER', 'postgres'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
        'HOST': os.environ.get('DB_HOST', 'localhost'),
        'PORT': os.environ.get('DB_PORT', '5432'),
    }
}

# Segurança HTTPS (Obrigatório em produção)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Email Real (SMTP)
EMAIL_HOST = os.environ.get('EMAIL_HOST')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
EMAIL_PORT = 587
EMAIL_USE_TLS = True

GATEWAY_WEBHOOK_SECRET = os.environ.get('GATEWAY_SECRET')