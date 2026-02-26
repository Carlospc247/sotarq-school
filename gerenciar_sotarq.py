import os
import django
import sys
from django.db import connection, transaction
from django.core.management import call_command

# 1. SETUP AMBIENTE - EXCLUSIVO SOTARQ SCHOOL
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.local')
django.setup()

from django_tenants.utils import schema_context
from apps.customers.models import Client, Domain
from apps.core.models import User

def format_header(title):
    print(f"\n{'='*50}\n {title.upper()} \n{'='*50}")

# --- (00) CONFIGURAÇÃO INICIAL DO SCHEMA PUBLIC ---
def configurar_public_inicial():
    format_header("Configuração Inicial SOTARQ SCHOOL (PUBLIC)")
    if Client.objects.filter(schema_name='public').exists():
        print("Aviso: O registro 'public' já existe.")
        return

    try:
        with transaction.atomic():
            # Cria o Tenant Mestre (Infraestrutura)
            public_tenant = Client(
                schema_name='public',
                name="SOTARQ SCHOOL - GLOBAL ADMIN",
                institution_type='complexo',
                is_active=True
            )
            public_tenant.save() 
            
            domain_name = input("Domínio mestre (ex: school.localhost): ")
            Domain.objects.create(
                domain=domain_name, 
                tenant=public_tenant, 
                is_primary=True
            )
            print(f"✔ Infraestrutura SOTARQ SCHOOL configurada com sucesso.")
    except Exception as e:
        print(f"❌ Erro ao configurar Public: {e}")

# --- (1) CRIAR DOMÍNIO ADICIONAL ---
def criar_dominio_extra():
    format_header("Criar Domínio")
    domain_name = input("URL do Domínio: ")
    schema = input("Schema da Escola (ex: public ou escola_primaria): ")
    try:
        tenant = Client.objects.get(schema_name=schema)
        Domain.objects.get_or_create(domain=domain_name, tenant=tenant, is_primary=False)
        print(f"✔ Domínio '{domain_name}' vinculado a {tenant.name}.")
    except Client.DoesNotExist:
        print("❌ Escola não encontrada.")

# --- (2) CRIAR SUPERUSER GLOBAL ---
def criar_superuser_global():
    format_header("Criar Superuser Global (Dono do Sistema)")
    username = input("Username: ")
    email = input("Email: ")
    password = input("Senha: ")
    
    with schema_context('public'):
        if User.objects.filter(username=username).exists():
            print("❌ Erro: Usuário já existe.")
            return
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f"✔ Superuser '{username}' criado no Global.")

# --- (3) CRIAR ESCOLA + ADMIN DO TENANT ---
def criar_escola_completa():
    format_header("Nova Escola (Tenant) + Administrador")
    name = input("Nome da Instituição: ")
    schema = input("Schema Name (ex: colegio_angola): ")
    domain_name = input("Subdomínio (ex: colegio.localhost): ")
    
    print("\nTipos: primario, complexo, medio, colegio, formacao")
    inst_type = input("Tipo de Instituição: ")
    
    adm_user = input("\nUsername do Admin da Escola: ")
    adm_pass = input("Senha do Admin: ")

    try:
        # 1. Cria a Escola no Public
        tenant = Client(
            schema_name=schema, 
            name=name, 
            institution_type=inst_type, 
            is_active=True
        )
        tenant.save()
        Domain.objects.create(domain=domain_name, tenant=tenant, is_primary=True)
        
        print(f"✔ Registro criado. Sincronizando banco de dados da escola...")
        
        # 2. Migração Física e Criação do Admin Local
        with schema_context(schema):
            call_command('migrate', verbosity=0)
            
            User.objects.create_user(
                username=adm_user, 
                password=adm_pass,
                tenant=tenant,
                is_staff=True
            )
            print(f"✔ Escola '{name}' pronta e Admin '{adm_user}' criado.")
            
    except Exception as e:
        print(f"❌ Erro Crítico: {e}")

# --- (4) LISTAR ESCOLAS ---
def listar_escolas():
    format_header("Lista de Escolas (Tenants)")
    escolas = Client.objects.all().order_by('id')
    print(f"{'ID':<5} | {'SCHEMA':<20} | {'TIPO':<12} | {'NOME'}")
    print("-" * 75)
    for e in escolas:
        print(f"{e.id:<5} | {e.schema_name:<20} | {e.institution_type:<12} | {e.name}")

# --- (5) LISTAR USUÁRIOS ---
def listar_usuarios():
    format_header("Lista Global de Usuários (Core)")
    usuarios = User.objects.all().select_related('tenant').order_by('id')
    print(f"{'ID':<5} | {'USER':<15} | {'PERMISSÃO':<12} | {'INSTITUIÇÃO'}")
    print("-" * 75)
    for u in usuarios:
        tipo = "SUPERUSER" if u.is_superuser else "STAFF/USER"
        inst = u.tenant.name if u.tenant else "ADMINISTRAÇÃO CENTRAL"
        print(f"{u.id:<5} | {u.username:<15} | {tipo:<12} | {inst}")

# --- (6) VINCULAR USUÁRIO ---
def vincular_usuario_escola():
    format_header("Vincular Usuário a Escola")
    u_id = input("ID do Usuário: ")
    e_id = input("ID da Escola: ")
    try:
        user = User.objects.get(id=u_id)
        escola = Client.objects.get(id=e_id)
        user.tenant = escola
        user.save()
        print(f"✔ Sucesso: {user.username} agora pertence a {escola.name}.")
    except Exception as e:
        print(f"❌ Erro: {e}")

# --- (7) APAGAR ESCOLA ---
def apagar_escola():
    format_header("Remover Escola (Permanente)")
    e_id = input("ID da Escola para APAGAR: ")
    try:
        escola = Client.objects.get(id=e_id)
        if escola.schema_name == 'public':
            print("❌ Erro: Proibido apagar o schema público.")
            return
        
        if input(f"Confirma apagar '{escola.name}'? (s/n): ").lower() == 's':
            if input(f"CONFIRMAÇÃO FINAL: Digite '{escola.name}' para confirmar: ") == escola.name:
                escola.delete()
                print("✔ Escola e dados excluídos.")
    except Exception as e: print(f"❌ Erro: {e}")

# --- (8) APAGAR USUÁRIO ---
def apagar_usuario():
    format_header("Apagar Usuário")
    u_id = input("ID do Usuário: ")
    try:
        user = User.objects.get(id=u_id)
        if input(f"Apagar '{user.username}'? (s/n): ").lower() == 's':
            user.delete()
            print("✔ Usuário removido.")
    except Exception as e: print(f"❌ Erro: {e}")

# --- (9) RESETAR SENHA ---
def resetar_senha():
    format_header("Resetar Senha de Usuário")
    u_id = input("ID do Usuário: ")
    try:
        user = User.objects.get(id=u_id)
        nova_senha = input("Nova Senha: ")
        if input(f"Confirmar reset para {user.username}? (s/n): ").lower() == 's':
            user.set_password(nova_senha)
            user.save()
            print("✔ Senha atualizada.")
    except User.DoesNotExist: print("❌ Usuário não encontrado.")

# --- MENU PRINCIPAL ---
def menu():
    while True:
        print("\nSOTARQ SCHOOL - CONSOLE DE ADMINISTRAÇÃO")
        print("00. Configurar Infraestrutura (PUBLIC)")
        print("1. Criar Domínio")
        print("2. Criar Superuser Global")
        print("3. Criar Escola + Admin (Nova Instituição)")
        print("4. Listar Escolas")
        print("5. Listar Usuários")
        print("6. Vincular Usuário a Escola")
        print("7. Apagar Escola")
        print("8. Apagar Usuário")
        print("9. Resetar Senha")
        print("0. Sair")
        
        opcao = input("\nEscolha: ")
        if opcao == '00': configurar_public_inicial()
        elif opcao == '1': criar_dominio_extra()
        elif opcao == '2': criar_superuser_global()
        elif opcao == '3': criar_escola_completa()
        elif opcao == '4': listar_escolas()
        elif opcao == '5': listar_usuarios()
        elif opcao == '6': vincular_usuario_escola()
        elif opcao == '7': apagar_escola()
        elif opcao == '8': apagar_usuario()
        elif opcao == '9': resetar_senha()
        elif opcao == '0': break

if __name__ == "__main__":
    menu()