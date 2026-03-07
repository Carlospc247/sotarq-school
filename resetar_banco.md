-- 1. Desativa a paginação chata para evitar o erro do 'more'
\pset pager off

-- 2. Corre novamente a limpeza de conexões (só por garantia)
SELECT pg_terminate_backend(pg_stat_activity.pid)
FROM pg_stat_activity
WHERE pg_stat_activity.datname = 'sotarq_school'
  AND pid <> pg_backend_pid();

-- 3. Apaga a base de dados (Use aspas porque o nome tem hífen)
DROP DATABASE "sotarq_school";

-- 4. Cria a base de dados novamente, limpinha
CREATE DATABASE "sotarq_school";