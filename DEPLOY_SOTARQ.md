# Abaixo, apresento o Sotarq Auto-Deployer v1.0. Este script Bash foi projetado para ser executado em um servidor Ubuntu virgem.

# 1. Script de Automação: deploy_sotarq.sh
 Crie o arquivo no servidor: nano deploy_sotarq.sh, cole o código que está em deploy_sotarq.sh e execute com 
# sudo bash deploy_sotarq.sh.

# 2. Análise Estratégica do Script
# Segurança Dinâmica: 
O script gera uma SECRET_KEY única para cada servidor automaticamente, evitando que você use chaves de desenvolvimento em produção.

# Isolamento de Processos: 
O uso de unix sockets (/run/sotarq.sock) para a comunicação entre Nginx e Gunicorn é mais rápido e seguro do que usar portas TCP locais.

# Escalabilidade Horizontal: 
Se o número de escolas crescer além da capacidade de um servidor, você pode rodar este mesmo script em uma nova máquina (Node) em minutos.



# Recomendação Profissional: Adicione o UptimeRobot (gratuito para monitorar o domínio principal) e instale o Sentry no seu código Django. O Sentry avisará você por e-mail sobre qualquer erro 500 que ocorra no schema de qualquer cliente antes mesmo do cliente perceber.



# 4. Para um sistema Multi-Tenant que visa o mercado corporativo, o SSL (HTTPS) não é opcional; é a base da confiança. Sem o cadeado verde, os navegadores modernos bloquearão o acesso dos alunos e professores, rotulando o seu sistema como "Não Seguro".

# 5. Para configurar o SSL para subdomínios ilimitados (wildcard), utilizaremos o Certbot com o desafio DNS. Este é o método mais profissional, pois garante que tanto escola1.school.com quanto escola999.school.com estejam protegidos pelo mesmo certificado.


# 2. O Desafio do DNS (Crucial)
# Diferente de um site comum, para obter um certificado Wildcard (*.school.com), o Let's Encrypt exige que você prove que é dono do domínio principal.

# O Certbot vai pausar e dizer: "Please deploy a DNS TXT record under the name _acme-challenge.school.com with the following value: XYZ123...".

 Você deve ir ao painel da sua empresa de domínio (ex: Cloudflare, Namecheap, GoDaddy).

# Criar o registro TXT conforme solicitado.

# Aguardar alguns minutos para a propagação e pressionar Enter no terminal.

# 3. Análise Veemente: Por que Automatizar a Renovação?
# Certificados do Let's Encrypt expiram a cada 90 dias. Se você esquecer de renovar, o sistema de todas as escolas para simultaneamente.

# Sugestão Inovadora: Configure um Cron Job para tentar a renovação automática toda semana:

# 4. Visão de Negócio: Vantagem Competitiva
# Ao entregar um sistema onde o cliente apenas escolhe o nome (ex: minhaescola.school.com) e tudo já funciona com HTTPS instantaneamente, você transmite uma imagem de robustez tecnológica. Isso justifica cobranças de taxas de implementação mais elevadas, pois você está a entregar uma infraestrutura de rede complexa de forma simplificada.











python manage.py create_school `
  --name "Escola Rei" `
  --schema "escolarei" `
  --domain "escolarei.sotarq.local" `
  --type "complexo" `
  --color "#1a73e8" `
  --admin-email "diretor@escolarei.ao" `
  --admin-pass "@guimil@#$%666"

Nota: Se estiver no Ubuntu, use a barra invertida \ no final de cada linha para continuar o comando. No Windows (PowerShell), use o acento grave `.

python manage.py create_school \
  --name "Escola Rei" \
  --schema "escolarei" \
  --domain "escolarei.sotarq.local" \
  --type "complexo" \
  --color "#1a73e8" \
  --admin-email "diretor@escolarei.ao" \
  --admin-pass "@guimil@#$%666"