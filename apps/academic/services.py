# apps/academic/services.py
from django.db import transaction
from django.db.models import F
from .models import Class, Enrollment, VacancyRequest

class EnrollmentEngine:
    @staticmethod
    @transaction.atomic
    def place_student(student, grade_level, preferred_class=None):
        """
        Tenta alocar o aluno. Se a preferida estiver cheia, busca outra.
        Se todas estiverem cheias, retorna None para disparar solicitação.
        """
        # 1. Tentar classe preferida
        if preferred_class and preferred_class.has_vacancy:
            target_class = preferred_class
        else:
            # 2. Buscar qualquer classe vaga no mesmo nível/ano
            target_class = Class.objects.filter(
                grade_level=grade_level,
                academic_year__is_active=True
            ).annotate(count=models.Count('enrollments_records')).filter(count__lt=models.F('capacity')).first()

        if not target_class:
            return None # Lotação esgotada

        # 3. Criar Matrícula
        enrollment, created = Enrollment.objects.get_or_create(
            student=student,
            class_room=target_class
        )

        # 4. REORDENAÇÃO ALFABÉTICA DINÂMICA
        # Re-calcula os números de chamada de todos os alunos da turma
        all_enrollments = Enrollment.objects.filter(class_room=target_class).select_related('student').order_by('student__full_name')
        
        for index, enr in enumerate(all_enrollments, start=1):
            enr.order_number = index
            enr.save(update_fields=['order_number'])

        return target_class