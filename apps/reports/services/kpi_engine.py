# apps/reports/services/kpi_engine.py

from django.db.models import Count, Q
from django.db import transaction
from apps.academic.models import StudentGrade
from apps.teachers.models import TeacherSubject
from apps.students.models import Enrollment
from apps.reports.models import KPI, KPIResult

class AcademicKPIEngine:
    @staticmethod
    def calculate_teacher_performance(academic_year_id):
        """
        Analisa a taxa de aprovação por disciplina/professor.
        """
        kpi, _ = KPI.objects.get_or_create(
            code='TEACHER_PASS_RATE',
            defaults={
                'name': 'Taxa de Aprovação por Professor',
                'target_value': 75.0 
            }
        )

        allocations = TeacherSubject.objects.filter(
            class_room__academic_year_id=academic_year_id
        ).select_related('teacher__user', 'subject', 'class_room')

        results = []
        
        with transaction.atomic():
            for allocation in allocations:
                total_students = Enrollment.objects.filter(
                    klass=allocation.class_room, status='active'
                ).count()

                approvals = StudentGrade.objects.filter(
                    klass=allocation.class_room,
                    subject=allocation.subject,
                    mt1__gte=10
                ).count()

                pass_rate = (approvals / total_students * 100) if total_students > 0 else 0.0
                
                # Salvar histórico
                KPIResult.objects.create(
                    kpi=kpi,
                    period=f"{allocation.class_room.academic_year.name}-Actual",
                    value=pass_rate
                )
                
                results.append({
                    'teacher': allocation.teacher.user.get_full_name(),
                    'subject': allocation.subject.name,
                    'class': allocation.class_room.name,
                    'pass_rate': round(pass_rate, 2),
                    'is_below_target': pass_rate < 75.0
                })
                
        return sorted(results, key=lambda x: x['pass_rate'])



