#!/bin/bash
#/var/www/sotarq/scripts/backup_db.sh
#!/bin/bash

# --- CONFIGURAÇÕES ---
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/var/www/sotarq/backups"
DB_NAME="sotarq_school"
LOG_FILE="/var/log/backup_sotarq.log"
S3_BUCKET="s3://seu-bucket-backup-sotarq"
WEBHOOK_URL="SUA_URL_DO_WEBHOOK_AQUI" 

# Função para enviar alerta em caso de falha
enviar_alerta() {
    mensagem="🚨 *ALERTA SOTARQ:* Falha no backup em $(hostname). Erro: $1"
    curl -H "Content-Type: application/json" -X POST -d "{\"content\": \"$mensagem\"}" $WEBHOOK_URL
}

mkdir -p $BACKUP_DIR

# 1. Executa o Dump e verifica erro
pg_dump $DB_NAME > $BACKUP_DIR/db_backup_$TIMESTAMP.sql
if [ $? -ne 0 ]; then enviar_alerta "Erro no pg_dump (Base de Dados)"; exit 1; fi

# 2. Compactação
tar -czvf $BACKUP_DIR/db_backup_$TIMESTAMP.tar.gz $BACKUP_DIR/db_backup_$TIMESTAMP.sql
if [ $? -ne 0 ]; then enviar_alerta "Erro na compactação (TAR)"; exit 1; fi

# 3. Envio para Nuvem (S3) e verifica erro
aws s3 cp $BACKUP_DIR/db_backup_$TIMESTAMP.tar.gz $S3_BUCKET
if [ $? -ne 0 ]; then enviar_alerta "Erro no upload para S3"; exit 1; fi

# 4. Limpeza do SQL bruto (mantém apenas o compactado)
rm $BACKUP_DIR/db_backup_$TIMESTAMP.sql

# 5. Limpeza de backups locais antigos (mais de 7 dias)
find $BACKUP_DIR -type f -mtime +7 -name "*.tar.gz" -delete

echo "✅ Backup concluído com sucesso e enviado para S3 em $TIMESTAMP" >> $LOG_FILE