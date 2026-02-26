Isso acontece porque há algum processo (provavelmente um terminal antigo do shell, o servidor runserver ou uma aba do psql) que ficou aberto e está "segurando" o banco.

Não perca tempo procurando a janela aberta. Use o comando de força bruta para desconectar toda a gente e apagar de vez.

No PowerShell, adicione a flag -f (force):

PowerShell

# dropdb -U postgres -f sotarq_school1

(Nota: Confirme se o nome do banco é sotarq_school1 ou sotarq_school. No seu erro apareceu com o número 1 no final).

Se o comando acima não funcionar (versões antigas do Postgres)
Se o -f falhar, use este comando SQL "Assassino" para matar todas as conexões manualmente e apagar o banco:

Entre no terminal SQL padrão:

PowerShell

### psql -U postgres -d postgres

Cole este bloco de código (ele mata quem estiver conectado e apaga o banco):

SQL

-- 1. Matar todas as conexões ativas nesse banco

# ****
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'sotarq_school1' -- <--- Confirme o nome aqui
  AND pid <> pg_backend_pid();

-- 2. Apagar o banco
DROP DATABASE sotarq_school1;

-- 3. Sair
\q

# ****
Depois disso, pode rodar o createdb tranquilamente.