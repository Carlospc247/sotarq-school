# apps/reports/services/__init__.py

# Importa a função do ficheiro bulletins.py que criámos no Passo 1
from .bulletins import generate_student_bulletin

# Importa a classe do ficheiro kpi_engine.py que criámos no Passo 2
from .kpi_engine import AcademicKPIEngine

# Define o que é exportado quando alguém faz "from apps.reports.services import *"
__all__ = ['generate_student_bulletin', 'AcademicKPIEngine']