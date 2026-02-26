import os
import ast
import sys
import importlib.util

# ==========================================
# CONFIGURAÇÕES ENTERPRISE
# ==========================================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Diretórios que NÃO contêm código fonte do projeto (Ignorar)
IGNORE_DIRS = {
    'venv', 'env', '.git', '__pycache__', '.idea', '.vscode', 
    'media', 'static', 'templates', 'docs', 'theme', 'logs'
}

# Arquivos que não devem ser auditados
IGNORE_FILES = {'manage.py'}

# Mapeamento Inteligente: Import -> Nome Real no PIP
PACKAGE_MAPPING = {
    'environ': 'django-environ',
    'dotenv': 'python-dotenv',
    'yaml': 'PyYAML',
    'PIL': 'Pillow',
    'rest_framework': 'djangorestframework',
    'bs4': 'beautifulsoup4',
    'jwt': 'PyJWT',
    'xhtml2pdf': 'xhtml2pdf',
    'weasyprint': 'weasyprint',
    'tenants': 'django-tenants',
    'celery': 'celery',
    'redis': 'redis',
    'psycopg2': 'psycopg2-binary',
    'lxml': 'lxml',
    'cryptography': 'cryptography',
    'defusedxml': 'defusedxml',
    'dateutil': 'python-dateutil',
    'qrcode': 'qrcode',
    'requests': 'requests',
    'openpyxl': 'openpyxl',
    'sentry_sdk': 'sentry-sdk',
    'matplotlib': 'matplotlib',
}

# Lista negra de termos que NUNCA devem ser sugeridos para instalação
# (São nomes de arquivos comuns em Django)
FORBIDDEN_SUGGESTIONS = {
    'apps', 'core', 'students', 'teachers', 'academic', 'finance', 'public', 
    'models', 'views', 'urls', 'forms', 'admin', 'tests', 'utils', 'services',
    'tasks', 'signals', 'apps', 'config', 'migrations', 'settings', 'templatetags',
    'management', 'base', 'mixins', 'decorators', 'exceptions', 'pagination',
    'permissions', 'serializers', 'validators', 'widgets', 'context_processors',
    'middleware', 'exports', 'generator', 'metrics', 'kpi_engine', 'bulletins',
    'signing', 'verification_engine', 'crypto'
}

def get_stdlib():
    """Obtém lista de módulos nativos do Python 3.13."""
    if hasattr(sys, 'stdlib_module_names'):
        return sys.stdlib_module_names
    return sys.builtin_module_names

def scan_local_structure(root_path):
    """
    Mapeia todos os arquivos .py e diretórios locais para evitar falsos positivos.
    Retorna um SET com nomes de módulos locais.
    """
    local_modules = set()
    
    for root, dirs, files in os.walk(root_path):
        # Limpar diretórios ignorados para não descer neles
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        # 1. Adicionar nomes de arquivos .py como módulos locais
        for file in files:
            if file.endswith('.py'):
                module_name = file[:-3] # Remove .py
                local_modules.add(module_name)
        
        # 2. Adicionar nomes de pastas que são pacotes Python (__init__.py)
        for d in dirs:
            if os.path.exists(os.path.join(root, d, '__init__.py')):
                local_modules.add(d)
                
    return local_modules

def extract_imports(file_path):
    """Lê arquivo e extrai imports usando AST."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return set()

    imports = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

def main():
    print(f"🔍 [SOTARQ AUDIT] Iniciando análise inteligente em: {PROJECT_ROOT}\n")
    
    # 1. Levantamento de Contexto
    std_lib = get_stdlib()
    local_structure = scan_local_structure(PROJECT_ROOT)
    
    # Adicionar pastas raiz comuns do Django manualmente por segurança
    local_structure.update({'apps', 'config', 'theme', 'templates'})
    
    print(f"📂 Arquivos/Módulos Locais Mapeados: {len(local_structure)} (Serão ignorados)")
    
    all_imports = set()
    
    # 2. Varredura de Código
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file.endswith('.py') and file not in IGNORE_FILES:
                full_path = os.path.join(root, file)
                imports = extract_imports(full_path)
                all_imports.update(imports)

    # 3. Análise e Filtragem
    missing_packages = set()
    
    print(f"📦 Total de Imports Detectados: {len(all_imports)}")
    print("-" * 60)

    for module in sorted(all_imports):
        # FILTRO 1: É biblioteca padrão do Python?
        if module in std_lib:
            continue
            
        # FILTRO 2: É um arquivo ou pasta local do projeto? (A CORREÇÃO PRINCIPAL)
        if module in local_structure:
            continue
            
        # FILTRO 3: É um import relativo (começa com ponto)?
        if module.startswith('.'):
            continue
            
        # FILTRO 4: Está na lista negra de nomes proibidos?
        if module in FORBIDDEN_SUGGESTIONS:
            continue

        # Verificação Real no Ambiente Virtual
        try:
            spec = importlib.util.find_spec(module)
        except (ValueError, ImportError):
            spec = None
            
        package_name = PACKAGE_MAPPING.get(module, module)
        
        if spec is None:
            # Dupla checagem: Se o nome mapeado for diferente, checa o mapeado também
            if package_name != module:
                if importlib.util.find_spec(package_name):
                    continue # O pacote real está instalado
            
            missing_packages.add(package_name)
            print(f"⚠️  SUSPEITO: Import '{module}' -> Pacote '{package_name}' não encontrado.")

    print("-" * 60)
    
    # 4. Relatório Executivo
    if missing_packages:
        # Filtragem final de segurança
        final_list = [p for p in missing_packages if p not in FORBIDDEN_SUGGESTIONS and p not in local_structure]
        
        if final_list:
            print("\n🚨 AÇÃO RECOMENDADA (APENAS PACOTES REAIS):")
            print(f"pip install {' '.join(sorted(final_list))}")
        else:
            print("\n✅ DIAGNÓSTICO: Nenhuma dependência externa faltando. Os imports suspeitos são internos.")
    else:
        print("\n✅ SUCESSO: Ambiente 100% íntegro. Nenhuma dependência faltando.")

if __name__ == '__main__':
    main()