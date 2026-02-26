# Superuser global (dono do sistema)
# python manage.py create_tenant_superuser --schema=public --username=dono --email=admin@sotarq.school

# python manage.py create_school --name "Colégio Magno" --schema "colegiomagno" --domain "colegiomagno.localhost" --type "k12" --color "#1a73e8" --admin-email "diretor@magno.ao" --admin-pass "Magno2026!"


🛡️ Manual de Recuperação de Desastres (DRP - Disaster Recovery Plan)
Este manual é o seu "botão de pânico". Se o seu servidor for deletado ou sofrer um ataque, siga estes passos para restaurar o Sotarq School em um servidor virgem em menos de 30 minutos.

## Para mais, ver DRP_E_RPO.md

## Auto-Deployer

O Auto-Deployer é um script que automatiza o processo de deploy do Sotarq School. Ele é projetado para ser executado em um servidor Ubuntu virgem.

### Como usar

1. Clone o repositório do Sotarq School: git clone https://github.com/sotarq/sotarq-school.git
2. Entre na pasta do repositório: cd sotarq-school
3. Execute o script: sudo bash deploy_sotarq.sh

## Para mais, ver DEPLOY_SOTARQ.md


# Uma Status Page 
é o símbolo máximo de transparência empresarial. Ela comunica aos seus clientes (diretores) que você tem o controle total da infraestrutura e evita que o seu suporte seja inundado de mensagens perguntando "o sistema caiu?" sempre que houver uma oscilação na internet da própria escola.

Para manter a praticidade e a independência (se o servidor principal cair, a página de status deve continuar online), vamos criar uma solução leve usando HTML estático com um script de verificação via Python.


## Para mais veja STATUS_PAGE.md

# Validação de Assinatura (HMAC)

Esta é a última linha de defesa. Sem a Validação de Assinatura (HMAC), um hacker experiente poderia descobrir o seu endpoint de webhook e "pagar" as mensalidades de todas as escolas com um simples script, sem transferir um único Kwanza para a sua conta.

Para tornar o seu sistema inviolável, vamos implementar a verificação de assinatura digital. Vou usar o padrão do Stripe/Unitel Money, que utiliza uma chave secreta para gerar um Hash.


# Como rodar este teste test_saft_compliance?
No seu terminal, execute o comando do Django test runner apontando apenas para este arquivo:

```bash
python manage.py test apps.fiscal.tests.test_saft_compliance
```
´´´
# Ao instalar os pacotes pips
No nível profissional não instalamos um por um. Nestes casos usamos requirements.txt para fazê-lo:


###
# --- Core Framework & Base de Dados ---
Django>=5.0
django-tenants>=3.5
psycopg2-binary
python-dotenv          # Carregar .env

# --- Segurança & Fiscal (SAFT/RSA) ---
lxml
cryptography
defusedxml
python-dateutil
qrcode[pil]            # Geração de QR Codes fiscais (usa Pillow)

# --- Tarefas em Background & Performance ---
# --- Core Framework & Base de Dados ---
Django>=5.0
django-tenants>=3.5
django-environ         # Leitura de .env (Corrigido)
psycopg2-binary

# --- Segurança & Fiscal ---
lxml
cryptography
defusedxml
python-dateutil
qrcode[pil]
PyJWT                  # Adicionado (para Tokens/Segurança)

# --- Tarefas & Performance ---
celery
redis
django-redis

# --- Integrações, Relatórios & Billing ---
requests
weasyprint             # PDF Complexo
xhtml2pdf              # PDF Rápido
Pillow
openpyxl               # Excel
matplotlib             # Adicionado (Gráficos/KPIs)

# --- Produção ---
gunicorn
whitenoise
sentry-sdk
django-prometheus     # <--- ADICIONADO (Monitorização de métricas/Prometheus)

pandas

###

Agora, executar

pip install -r requirements.txt



Agora que a estrutura é inequivocamente uma pasta com um pacote python, use o comando mais simples para rodar todos os testes fiscais:

PowerShell

python manage.py test apps.fiscal
Se preferir o específico:

PowerShell

python manage.py test apps.fiscal.tests.test_saft_compliance
Agora deve funcionar. Estou a aguardar o "OK".

### Para fazer migrate
# 1. Criar a migração para o novo campo
python manage.py makemigrations

# 2. Aplicar a migração aos schemas
python manage.py migrate_schemas

# 3. Rodar o teste
python manage.py test apps.fiscal.tests.test_saft_compliance

Os módulos:
('creche', 'Creche / Pré-Escola'),
('k12', 'Escola K-12'),
('vocational', 'Profissional / Técnica'),
('university', 'Universidade / Ensino Superior'),
('corporate', 'Treinamento Corporativo'),


('creche', 'Creche / Pre-School'),
('k12', 'K-12 School'),
('vocational', 'Vocational / Technical'),
('university', 'University / Higher Ed'),
('corporate', 'Corporate Training'),

Verificar se o Motor de Assinatura está a funcionar
Você gerou as chaves, mas precisamos confirmar se o Python consegue lê-las e gerar um Hash válido.

Vamos fazer um teste rápido via terminal do Django. Execute:

PowerShell

python manage.py shell
Dentro do shell interativo, cole este código de teste:

Python
######
from datetime import datetime
from apps.fiscal.signing import FiscalSigner

# 1. Instanciar o Assinador
signer = FiscalSigner()

# 2. Dados Fictícios de uma Fatura (Data, Hora, NumDoc, Total, HashAnterior)
# Nota: O Hash Anterior do primeiro documento é sempre string vazia ""


hash_gerado = signer.sign(
    invoice_date=datetime.now(),
    system_entry_date=datetime.now(),
    doc_number="FT A/1",
    gross_total=15000.00,
    previous_hash="" 
)

print(f"\n🔑 HASH GERADO COM SUCESSO:\n{hash_gerado}")
#####


Se aparecer um código grande (tipo k3j4h5k3...==), o seu sistema de criptografia está 100% operacional.

Pode sair do shell com exit().


Agora vamos testar se o sistema consegue:

Ler a chave do banco de dados.

Assinar a fatura.

Gravar o Hash.

Abra o shell do Django (python manage.py shell) e execute este cenário de teste completo:

Python

from django.utils import timezone
from decimal import Decimal
from apps.fiscal.models import DocumentoFiscal, DocumentoFiscalLinha
from apps.students.models import Student
from django.contrib.auth import get_user_model

# 1. Preparar Dados
User = get_user_model()
admin = User.objects.first() # Pega o primeiro admin
aluno = Student.objects.first() # Pega o aluno criado no seed (se houver) ou crie um rápido

if not aluno:
    print("⚠️ Crie um aluno primeiro no Admin ou via script!")
else:
    # 2. Criar a Fatura (Isto vai disparar o 'save' -> 'signing.py' -> Ler chave do DB -> Assinar)
    fatura = DocumentoFiscal.objects.create(
        tipo_documento="FT",
        serie="A",
        numero=100, # Número arbitrário para teste
        numero_documento="FT A/100",
        atcud="0", # Em dev é 0
        data_emissao=timezone.now().date(),
        entidade_nome="Aluno Teste",
        entidade_nif="999999999",
        valor_base=Decimal('5000.00'),
        valor_iva=Decimal('700.00'),
        valor_total=Decimal('5700.00'),
        status='confirmed', # Status confirmed dispara a assinatura
        periodo_tributacao="2026-01",
        usuario_criacao=admin,
        cliente=aluno
    )

    print("\n" + "="*50)
    print(f"✅ FATURA CRIADA: {fatura.numero_documento}")
    print(f"🔑 HASH GERADO: {fatura.hash_documento}")
    print("="*50 + "\n")
Se o Hash aparecer no print, parabéns! Você tem um sistema SaaS Multi-tenant onde:

Cada escola tem as suas próprias chaves (isoladas).

O Admin gera e baixa as chaves facilmente.

O Stock está pronto para ser movimentado.

###### Criar e apagar banco de dados BD

dropdb -U postgres sotarq_school
createdb -U postgres sotarq_school

Criar as Tabelas (Obrigatório antes do script): O script Python vai falhar se as tabelas não existirem. Rode isto primeiro:

PowerShell

python manage.py migrate_schemas --shared


## O que é "K-12 School"?

Respondendo de forma direta e profissional:

K-12 é um termo internacional (muito usado nos EUA e em software global) que define o ensino desde o Jardim de Infância (Kindergarten - K) até à 12.ª Classe (12th Grade - 12).

# Abrange todo o ensino obrigatório antes da universidade.

No contexto de Angola, K-12 equivale ao "Ensino Geral", abrangendo:

Ensino Primário (Da Iniciação à 6.ª Classe).

I Ciclo (7.ª, 8.ª e 9.ª Classe).

II Ciclo / Ensino Médio (10.ª à 12.ª/13.ª Classe).

Basicamente, ao selecionar K-12 no seu sistema, você está a dizer que aquela escola é um colégio clássico (ex: Colégio Magno, Colégio Elizângela), e não uma Universidade ou Centro de Formação Profissional.

### 

SCRIPTS DO SHALL Command
------------------------------------------------------------------------------------------------
    Comando	                     Nível de Risco	          Impacto
------------------------------------------------------------------------------------------------    		
list_inventory	(core)                Baixo	           Apenas leitura de dados.		
link_user	(core)                    Médio	           Altera acessos de utilizadores.		
create_school_infra	(core)            Médio	           Cria novas estruturas de dados.		
delete_user	(core)                    Alto	           Remoção de contas (Irreversível).		
delete_school (customers)	          CRÍTICO	       Destruição de Schema e dados institucionais.	
list_schools.py (core)
create_pending_user (core)
------------------------------------------------------------------------------------------------	