# /var/www/sotarq/scripts/weekly_maintenance.sh
#!/bin/bash
PROJECT_DIR="/var/www/sotarq"
DB_NAME="sotarq_school"
LOG_FILE="/var/log/sotarq_maintenance.log"

echo "--- Início da Manutenção: $(date) ---" >> $LOG_FILE

# 1. Limpar Sessões Expiradas do Django
# Evita que a tabela django_session cresça infinitamente
cd $PROJECT_DIR
source venv/bin/activate
python3 manage.py clearsessions
echo "✅ Sessões limpas." >> $LOG_FILE

# 2. Limpar Arquivos Temporários e Cache de Templates
find $PROJECT_DIR -name "*.pyc" -delete
find $PROJECT_DIR -name "__pycache__" -delete
echo "✅ Cache limpo." >> $LOG_FILE

# 3. Otimização do PostgreSQL (VACUUM ANALYZE)
# Recupera espaço em disco de registros deletados e atualiza estatísticas do planejador
sudo -u postgres psql -d $DB_NAME -c "VACUUM ANALYZE;"
echo "✅ Banco de dados otimizado." >> $LOG_FILE

deactivate
echo "--- Manutenção Finalizada: $(date) ---" >> $LOG_FILE