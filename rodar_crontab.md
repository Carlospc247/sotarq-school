Perfeito, Chefe. Como na **DigitalOcean** o senhor tem uma **Droplet** (VPS) com acesso total ao Linux (Ubuntu/Debian), o processo é direto e rigoroso.

Siga estes passos exatos no seu terminal:

---

### 1. Acesso ao Servidor

Primeiro, entre no seu servidor via SSH (se já não estiver lá):

```bash
ssh root@seu_ip_da_digital_ocean

```

### 2. Abrir o Editor do Cron

Digite o comando:

```bash
crontab -e

```

> **Nota de Estagiário:** Se for a primeira vez, o Linux perguntará qual editor deseja usar. Escolha o `1` (para o **nano**), que é o mais simples.

### 3. Inserir a Linha de Faturamento SOTARQ

Vá até o fim do arquivo e cole a linha abaixo. **Atenção:** Adapte os caminhos para onde o senhor instalou o projeto (estou assumindo `/var/www/sotarq_school`).

```bash
# Roda o Robô de Faturação SOTARQ SCHOOL todo dia 1 de cada mês às 05:00
0 5 1 * * /var/www/sotarq_school/venv/bin/python /var/www/sotarq_school/manage.py run_monthly_billing >> /var/www/sotarq_school/logs/billing.log 2>&1

```

### 4. Salvar e Sair

* No **nano**: Pressione `Ctrl + O` (para gravar), depois `Enter` e `Ctrl + X` (para sair).
* O terminal deverá exibir a mensagem: `crontab: installing new crontab`.

---

### Verificações de Rigor (Não pule isto, Chefe!):

1. **Pasta de Logs:** O comando vai falhar se a pasta `logs` não existir. Crie-a agora:
```bash
mkdir -p /var/www/sotarq_school/logs

```


2. **Fuso Horário (Angola):** Por padrão, a DigitalOcean vem em UTC. Para o faturamento bater com o horário de Luanda/Malanje, verifique a hora do servidor:
```bash
date

```


Se não estiver correto, mude para o horário de Angola:
```bash
timedatectl set-timezone Africa/Luanda

```


3. **Variáveis de Ambiente:** Como o Cron roda num ambiente "limpo", ele pode não carregar o seu arquivo `.env` automaticamente. Certifique-se de que o seu `settings.py` do Django está preparado para ler o `.env` usando `python-dotenv` ou similar.

---

### Próximo Passo:

Agora que o agendamento está "no ferro" na DigitalOcean, o motor financeiro está protegido.

Deseja que eu escreva agora o **Modelo de Pagamento (`Payment`)** para que o sistema consiga registrar as transferências bancárias e dar "Baixa" (Status: Paid) nessas faturas automaticamente?