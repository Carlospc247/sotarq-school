# FASE 1: Preparação do Novo Servidor
Contrate um novo VPS (Ubuntu 24.04 ou superior).

Execute o seu script de automação inicial: sudo bash deploy_sotarq.sh.

Isso instalará o Nginx, PostgreSQL, Gunicorn e criará as pastas.

# FASE 2: Restauração da Base de Dados (O Coração)
Baixe o backup mais recente do S3:

Bash

# aws s3 cp s3://seu-bucket-backup-sotarq/db_backup_DATA_RECENTE.tar.gz /tmp/

Descompacte o arquivo:

Bash

# tar -xzvf /tmp/db_backup_DATA_RECENTE.tar.gz -C /tmp/
Restaure no PostgreSQL:

Nota: O banco de dados deve estar vazio. Se necessário, apague-o e crie-o novamente antes.

Bash

# sudo -u postgres psql sotarq_school < /tmp/db_backup_DATA_RECENTE.sql

# FASE 3: Restauração de Arquivos de Media (Fotos/Documentos)
Se você também faz backup da pasta media (onde estão os PDFs dos boletins e QR Codes), restaure-a agora:

Bash

# aws s3 sync s3://seu-bucket-media-sotarq /var/www/sotarq/media/

# FASE 4: Reconfiguração e Verificação
Ajuste o .env: Verifique se a SECRET_KEY e as credenciais do banco no novo servidor batem com o backup restaurado.

Migrações: Execute as migrações apenas para garantir que o schema está sincronizado:

Bash

python3 manage.py migrate_schemas --shared
Reinicie os Serviços:

Bash

sudo systemctl restart gunicorn
sudo systemctl restart nginx

🧠 Análise Veemente e Prática
Restauração de Schemas: Como você usa django-tenants, restaurar o banco via psql < file.sql restaura todos os schemas das escolas de uma só vez. Não precisa fazer um por um.

Teste de Incêndio: Uma vez por semestre, tente restaurar o backup em uma máquina local (seu PC). Um backup que nunca foi testado não é um backup, é uma esperança.

## RPO (Recovery Point Objective): 
Com backups às 02:00 AM, em caso de desastre total às 23:00, você perde no máximo 21 horas de dados. Para um sistema escolar, isso é aceitável e profissional.

Visão Empresarial
Apresentar este DRP a um investidor ou a um diretor de uma grande rede de escolas mostra que o seu SaaS é resiliente. Você não está a vender "um código que funciona", está a vender uma operação de missão crítica que não para.