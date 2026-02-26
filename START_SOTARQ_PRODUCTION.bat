@echo off
TITLE SOTARQ SCHOOL ENTERPRISE - PRODUCTION MODE
COLOR 0A

echo ======================================================================
echo           SOTARQ SCHOOL - PROTOCOLO DE INICIALIZACAO
echo ======================================================================

:: 1. INICIAR REDIS (O Coração das Tarefas e Notificações)
echo [1/4] Verificando Broker de Mensagens (Redis)...
:: Tenta iniciar o container se ele já existir, caso contrário cria um novo
docker start redis_sotarq 2>nul || docker run --name redis_sotarq -d -p 6379:6379 redis
timeout /t 3 >nul

:: 2. INICIAR DJANGO (Servidor de Aplicação)
echo [2/4] Lancando Servidor Web Django (Porta 8080)...
start "SOTARQ_WEB_SERVER" cmd /k "venv\Scripts\activate && python manage.py runserver 0.0.0.0:8080"

:: 3. INICIAR CELERY WORKER (O Executor de Despachos e Juros)
echo [3/4] Lancando Celery Worker (Pool Eventlet para Windows)...
start "SOTARQ_CELERY_WORKER" cmd /k "venv\Scripts\activate && celery -A config worker -l info -P eventlet"

:: 4. INICIAR CELERY BEAT (O Relogio de Manutencao)
echo [4/4] Lancando Celery Beat (Agendador de Limpeza e Juros)...
start "SOTARQ_CELERY_BEAT" cmd /k "venv\Scripts\activate && celery -A config beat -l info"

echo ======================================================================
echo   SISTEMA ONLINE - MONITORE AS JANELAS PARA LOGS DE AUDITORIA
echo ======================================================================
echo Pressione qualquer tecla para fechar este inicializador (os servicos continuarao rodando).
pause >nul