# python manage.py setup_school_structures
from django.core.management.base import BaseCommand
from django_tenants.utils import schema_context
from apps.customers.models import Client
from apps.academic.models import Course, GradeLevel

class Command(BaseCommand):
    help = 'RIGOR SOTARQ: Insere a estrutura de classes padrão em todas as escolas.'

    def handle(self, *args, **options):
        # Seleciona apenas os clientes reais (ignora o public)
        tenants = Client.objects.exclude(schema_name='public')
        
        self.stdout.write(self.style.SUCCESS(f"Iniciando atualização de {tenants.count()} escolas..."))

        for tenant in tenants:
            self.stdout.write(f"-> Processando: {tenant.name} ({tenant.schema_name})")
            
            with schema_context(tenant.schema_name):
                self.setup_structure(tenant)

        self.stdout.write(self.style.SUCCESS("Estruturas atualizadas com sucesso!"))

    def setup_structure(self, tenant):
        """Define a lógica de classes baseada no tipo de instituição."""
        structure = []
        course_name = "Ensino Geral"
        course_code = "GEN-01"
        course_level = Course.Level.HIGH_SCHOOL

        # Lógica de seleção por tipo (Rigor SOTARQ)
        if tenant.institution_type == 'primario':
            structure = [
                ('Iniciação', 0), ('1ª Classe', 1), ('2ª Classe', 2), 
                ('3ª Classe', 3), ('4ª Classe', 4), ('5ª Classe', 5), ('6ª Classe', 6)
            ]
        elif tenant.institution_type == 'complexo':
            structure = [
                ('Iniciação', 0), ('1ª Classe', 1), ('2ª Classe', 2), ('3ª Classe', 3), 
                ('4ª Classe', 4), ('5ª Classe', 5), ('6ª Classe', 6), ('7ª Classe', 7), 
                ('8ª Classe', 8), ('9ª Classe', 9), ('10ª Classe', 10), ('11ª Classe', 11), ('12ª Classe', 12)
            ]
        elif tenant.institution_type == 'medio':
            course_name, course_code = "Ensino Médio Técnico", "TEC-01"
            course_level = Course.Level.TECHNICAL
            structure = [('10ª Classe', 10), ('11ª Classe', 11), ('12ª Classe', 12), ('13ª Classe', 13)]
        elif tenant.institution_type == 'colegio':
            structure = [('10ª Classe', 10), ('11ª Classe', 11), ('12ª Classe', 12)]

        if not structure:
            self.stdout.write(self.style.WARNING(f"   [!] Tipo '{tenant.institution_type}' sem estrutura definida."))
            return

        # 1. Garantir o Curso
        course, _ = Course.objects.get_or_create(
            code=course_code,
            defaults={'name': course_name, 'level': course_level}
        )

        # 2. Garantir as Classes (GradeLevels)
        created_count = 0
        for name, index in structure:
            _, created = GradeLevel.objects.get_or_create(
                course=course,
                level_index=index,
                defaults={'name': name}
            )
            if created:
                created_count += 1
        
        if created_count > 0:
            self.stdout.write(self.style.SUCCESS(f"   [+] {created_count} novas classes criadas."))
        else:
            self.stdout.write("   [ok] Estrutura já estava completa.")