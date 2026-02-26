#!/bin/bash

# --- CONFIGURAÇÕES (EDITE ANTES DE EXECUTAR) ---
DB_NAME="sotarq_school"
DB_USER="sotarq_admin"
DB_PASS="StrongPassword123!"  # Use senhas complexas
PROJECT_DIR="/var/www/sotarq-school"
REPO_URL="https://github.com/Carlospc247/sotarq-school.git"
DOMAIN="school.com"

echo "🚀 Iniciando Deployment do Sotarq School SaaS..."

# 1. Atualização do Sistema e Dependências
apt update && apt upgrade -y
apt install -y python3-pip python3-venv nginx postgresql postgresql-contrib git libpq-dev

# 2. Configuração do PostgreSQL
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;"
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';"
sudo -u postgres psql -c "ALTER ROLE $DB_USER CREATEDB;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"

# 3. Preparação do Diretório e Código
mkdir -p $PROJECT_DIR
git clone $REPO_URL $PROJECT_DIR
cd $PROJECT_DIR

# 4. Ambiente Virtual e Dependências
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install gunicorn psycopg2-binary django-dotenv

# 5. Variáveis de Ambiente (.env)
cat <<EOF > .env
DEBUG=False
SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_urlsafe(50))')
DATABASE_URL=postgres://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
ALLOWED_HOSTS=.$DOMAIN
DOMAIN_URL=$DOMAIN
EOF

# 6. Migrações e Estáticos
python3 manage.py migrate_schemas --shared --noinput
python3 manage.py collectstatic --noinput

# 7. Configuração do Systemd (Gunicorn)
cat <<EOF > /etc/systemd/system/sotarq.service
[Unit]
Description=Gunicorn daemon para Sotarq School
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=$PROJECT_DIR
ExecStart=$PROJECT_DIR/venv/bin/gunicorn --workers 3 --bind unix:/run/sotarq.sock config.wsgi:application

[Install]
WantedBy=multi-user.target
EOF

systemctl start sotarq
systemctl enable sotarq

# ... (parte anterior do script igual)

# 8. Configuração do Nginx (Wildcard Subdomains)
apt install -y certbot python3-certbot-nginx

# CRÍTICO: Criar o link simbólico ANTES de testar e reiniciar
ln -sf /etc/nginx/sites-available/sotarq /etc/nginx/sites-enabled/

echo "🔒 Iniciando configuração do SSL Wildcard..."
certbot certonly --manual --preferred-challenges dns -d $DOMAIN -d *.$DOMAIN

# Atualizando o arquivo com as configurações SSL
cat <<EOF > /etc/nginx/sites-available/sotarq
server {
    listen 80;
    listen 443 ssl;
    server_name .$DOMAIN;

    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    if (\$scheme = http) {
        return 301 https://\$host\$request_uri;
    }

    location /static/ { alias $PROJECT_DIR/static/; }
    location /media/ { alias $PROJECT_DIR/media/; }

    location / {
        include proxy_params;
        proxy_pass http://unix:/run/sotarq.sock;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}
EOF

# Testar e Reiniciar
nginx -t && systemctl restart nginx

# Automação da renovação
echo "0 0 * * 1 root /usr/bin/certbot renew --quiet" >> /etc/crontab

echo "✅ Deployment Concluído! Sistema disponível em *.$DOMAIN"

