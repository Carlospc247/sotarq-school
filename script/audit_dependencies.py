import os
import ast
import sys
import importlib.util

# Configurações
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IGNORE_DIRS = {'venv', '.git', '__pycache__', 'media', 'static', 'templates', 'docs', 'theme'}
IGNORE_FILES = {'manage.py'}

# Mapeamento de imports para nomes de pacotes reais (PyPI)
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
}

def get_stdlib():
    """Retorna lista de bibliotecas padrão do Python (Nativo 3.10+)."""
    if hasattr(sys, 'stdlib_module_names'):
        return sys.stdlib_module_names
    else:
        # Fallback para versões antigas (apenas essencial)
        return sys.builtin_module_names

def is_local_app(module_name):
    """Verifica se o import é de uma app local."""
    if module_name.startswith('apps.') or module_name.startswith('config.'):
        return True
    return False

def extract_imports(file_path):
    """Lê um arquivo Python e extrai todos os módulos importados."""
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        try:
            tree = ast.parse(f.read(), filename=file_path)
        except SyntaxError:
            return set()

    imports = set()
    for node in ast.walk(tree):
        # Captura "import x"
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name.split('.')[0])
        # Captura "from x import y"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module.split('.')[0])
    return imports

def main():
    print(f"🔍 Iniciando auditoria em: {PROJECT_ROOT}\n")
    
    std_lib = get_stdlib()
    all_imports = set()
    
    # 1. Varredura
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        
        for file in files:
            if file.endswith('.py') and file not in IGNORE_FILES:
                full_path = os.path.join(root, file)
                imports = extract_imports(full_path)
                all_imports.update(imports)

    # 2. Análise
    missing_packages = []
    
    print(f"📦 Módulos encontrados no código: {len(all_imports)}")
    print("-" * 60)

    for module in sorted(all_imports):
        # Ignora stdlib, apps locais e imports relativos
        if module in std_lib or is_local_app(module) or module.startswith('.'):
            continue
            
        # Verifica se está instalado
        spec = importlib.util.find_spec(module)
        package_name = PACKAGE_MAPPING.get(module, module)
        
        if spec is None:
            # Filtro extra para falsos positivos comuns
            if module not in ['management', 'migrations']: 
                missing_packages.append((module, package_name))
                print(f"❌ EM FALTA: Import '{module}' detectado (Pacote sugerido: {package_name})")

    print("-" * 60)
    
    # 3. Relatório Final
    if missing_packages:
        print("\n🚨 AÇÃO NECESSÁRIA - Copie e rode o comando abaixo:")
        unique_pkgs = sorted(list(set([pkg[1] for pkg in missing_packages])))
        print(f"pip install {' '.join(unique_pkgs)}")
    else:
        print("\n✅ SUCESSO: Todas as dependências importadas parecem estar instaladas!")

if __name__ == '__main__':
    main()