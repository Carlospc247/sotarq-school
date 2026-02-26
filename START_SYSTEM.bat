@echo off
TITLE SOTARQ SCHOOL - AUTOMATED STARTUP
COLOR 0B

echo =======================================================
echo    SOTARQ SCHOOL ENTERPRISE - INICIANDO SISTEMAS
echo =======================================================

:: 1. INICIAR REDIS (Assumindo que o senhor usa Docker para o Redis)
echo [1/4] Iniciando Broker de Mensagens (Redis)...
start "SOTARQ_REDIS" docker start redis_sotarq 2>nul || start "SOTARQ_REDIS" docker run --name redis_sotarq -d -p 6379:6379 redis

:: 2. INICIAR DJANGO SERVER
echo [2/4] Iniciando Servidor Web Django...
start "SOTARQ_WEB" cmd /k "venv\Scripts\activate && python manage.py runserver 8080"

:: 3. INICIAR CELERY WORKER
echo [3/4] Iniciando Executor de Tarefas (Worker)...
start "SOTARQ_WORKER" cmd /k "venv\Scripts\activate && celery -A config worker -l info -P eventlet"

:: 4. INICIAR CELERY BEAT
echo [4/4] Iniciando Agendador (Beat)...
start "SOTARQ_BEAT" cmd /k "venv\Scripts\activate && celery -A config beat -l info"

echo -------------------------------------------------------
echo SISTEMAS ONLINE. MONITORE AS JANELAS PARA LOGS.
echo -------------------------------------------------------
pause