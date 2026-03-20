# apps/academic/analytics.py
from django.db.models import Count, Sum, F
from datetime import datetime, timedelta
from .models import TimetableSlot, Classroom

class EfficiencyAnalytics:
    """
    Analisa a utilização de recursos (Salas e Professores).
    Objetivo: Reduzir janelas e identificar espaços monetizáveis.
    """

    @staticmethod
    def get_teacher_windows(teacher, academic_year):
        """
        Deteta intervalos (janelas) entre aulas no mesmo dia.
        """
        slots = TimetableSlot.objects.filter(
            teacher=teacher, 
            class_room__academic_year=academic_year
        ).order_by('day_of_week', 'start_time')

        windows = []
        for day in range(1, 7): # Segunda a Sábado
            day_slots = [s for s in slots if s.day_of_week == day]
            for i in range(len(day_slots) - 1):
                # Se o fim de uma aula e o início da outra tiverem um gap
                if day_slots[i].end_time < day_slots[i+1].start_time:
                    gap_start = day_slots[i].end_time
                    gap_end = day_slots[i+1].start_time
                    windows.append({
                        'day': day,
                        'start': gap_start,
                        'end': gap_end,
                        'duration': datetime.combine(datetime.today(), gap_end) - 
                                   datetime.combine(datetime.today(), gap_start)
                    })
        return windows

   
    @staticmethod
    def get_room_occupancy_rate(classroom, academic_year):
        daily_capacity_minutes = 12 * 60 * 6 
        
        # RIGOR: Filtramos pela Sala Física e pelo Ano Letivo da Turma
        slots = TimetableSlot.objects.filter(
            classroom=classroom,                  # Sala física (objeto Classroom)
            class_room__academic_year=academic_year # Turma (objeto Class -> academic_year)
        )
        
        total_minutes = 0
        for s in slots:
            # Cálculo de duração
            duration = datetime.combine(datetime.today(), s.end_time) - \
                    datetime.combine(datetime.today(), s.start_time)
            total_minutes += duration.seconds // 60
            
        occupancy_rate = (total_minutes / daily_capacity_minutes) * 100 if daily_capacity_minutes > 0 else 0
        return round(occupancy_rate, 2)