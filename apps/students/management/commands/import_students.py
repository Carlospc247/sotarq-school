import csv
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.students.models import Student
from apps.academic.models import Class, Enrollment

class Command(BaseCommand):
    help = 'Importa alunos de um ficheiro CSV para o Tenant atual'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str)
        parser.add_argument('class_id', type=int)

    @transaction.atomic
    def handle(self, *args, **options):
        path = options['csv_file']
        klass = Class.objects.get(id=options['class_id'])
        
        with open(path, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            count = 0
            for row in reader:
                # Criar o Aluno
                student, created = Student.objects.get_or_create(
                    registration_number=row['processo'],
                    defaults={
                        'full_name': row['nome'],
                        'bi_number': row['bi'],
                        'email': row.get('email', ''),
                        'phone': row.get('telefone', '')
                    }
                )
                # Matricular na Turma
                Enrollment.objects.get_or_create(student=student, klass=klass)
                count += 1
        
        self.stdout.write(self.style.SUCCESS(f'Sucesso! {count} alunos importados e matriculados.'))

