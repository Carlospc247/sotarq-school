#!/bin/bash

# 1. ATIVAR AMBIENTE (No Linux é bin/activate, não Scripts/activate)
source venv/bin/activate

# 2. INICIAR REDIS (Assumindo Docker no Ubuntu)
sudo docker start redis_sotarq || sudo docker run --name redis_sotarq -d -p 6379:6379 redis

# 3. LANÇAR WORKER (No Linux NÃO usamos eventlet, usamos o pool padrão que é mais rápido)
screen -dmS celery_worker venv/bin/celery -A config worker -l info

# 4. LANÇAR BEAT
screen -dmS celery_beat venv/bin/celery -A config beat -l info

# 5. LANÇAR DJANGO (Em produção real usaríamos GUNICORN)
python manage.py runserver 0.0.0.0:8000