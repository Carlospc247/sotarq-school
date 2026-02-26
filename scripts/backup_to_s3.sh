#!/bin/bash

# Configurações
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_DIR="/app/backups"
DB_NAME="sotarq_db"
S3_BUCKET="s3://seu-bucket-sotarq-backups"
FILENAME="backup_full_${TIMESTAMP}.sql.gz"

echo "🚀 Iniciando Backup Sotarq Safe-Data..."

# 1. Extrair Dump (Usando docker exec para pegar do container ou direct do Managed DB)
# O pg_dumpall garante que todos os SCHEMAS (Tenants/Escolas) sejam salvos.
docker exec $(docker ps -q -f name=db) pg_dumpall -U sotarq_user | gzip > ${BACKUP_DIR}/${FILENAME}

# 2. Enviar para S3 (Necessário ter awscli configurado)
aws s3 cp ${BACKUP_DIR}/${FILENAME} ${S3_BUCKET}/daily/

# 3. Limpeza: Remover backups locais com mais de 7 dias
find ${BACKUP_DIR} -type f -mtime +7 -name "*.sql.gz" -delete

echo "✅ Backup concluído e enviado para S3 com sucesso!"