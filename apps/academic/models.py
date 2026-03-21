# apps/academic/models.py
from decimal import Decimal
import math
from django.db import models
from django.forms import ValidationError
from django.utils.translation import gettext_lazy as _
from apps.core.models import BaseModel # Herança para Auditoria e Soft Delete
from django.utils import timezone
import datetime



# --- Modelos Existentes (Mantidos e Refinados) ---



def get_default_start_date():
    """Retorna 2 de Setembro do ano atual"""
    return datetime.date(datetime.date.today().year, 9, 2)

def get_default_end_date():
    """Retorna 31 de Julho do PRÓXIMO ano"""
    return datetime.date(datetime.date.today().year + 1, 7, 31)

    

class AcademicYear(BaseModel):
    #tenant = models.ForeignKey('customers.Client', on_delete=models.CASCADE, related_name='academic_years')
    name = models.CharField(max_length=20, help_text="Ex: 2025/2026")
    start_date = models.DateField()
    end_date = models.DateField()
    is_active = models.BooleanField(default=False)

    class Meta:
        ordering = ['-start_date']

    def __str__(self):
        return self.name


class Course(BaseModel):
    class Level(models.TextChoices):
        BASE = 'BASE', _('Ensino de Base (primario, I e II)')
        HIGH_SCHOOL = 'HIGH_SCHOOL', _('Ensino Médio (Puniv)')
        TECHNICAL = 'TECHNICAL', _('Médio Técnico (Vocational-Politécnico)')
        PROFESSIONAL = 'PROFESSIONAL', _('Formação Profissional (Training)')
    
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, unique=True)
    level = models.CharField(max_length=20, choices=Level.choices, default=Level.HIGH_SCHOOL)
    duration_years = models.DecimalField(max_digits=5, decimal_places=2, default=3.00, help_text="Anos totais. Use 0.08 para ~1 mês, 0.25 para 3 meses, etc.")
    coordinator = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='coordinated_courses')
    
    taxa_iva = models.ForeignKey(
        'fiscal.TaxaIVAAGT', 
        on_delete=models.PROTECT, 
        null=True, 
        blank=True,
        verbose_name="Taxa de IVA Aplicável"
    )
 
    # RIGOR: O curso agora aponta para os TIPOS de taxa, não para valores fixos
    default_monthly_fee_type = models.ForeignKey(
        'finance.FeeType', 
        on_delete=models.PROTECT, 
        related_name='courses_monthly',
        null=True, blank=True,
        verbose_name="Tipo de Mensalidade Padrão"
    )
    default_enrollment_fee_type = models.ForeignKey(
        'finance.FeeType', 
        on_delete=models.PROTECT, 
        related_name='courses_enrollment',
        null=True, blank=True,
        verbose_name="Tipo de Matrícula Padrão"
    )

    taxa_iva = models.ForeignKey(
        'fiscal.TaxaIVAAGT', 
        on_delete=models.PROTECT, 
        null=True, blank=True,
        verbose_name="Taxa de IVA Aplicável"
    )

    # Propriedades para manter a compatibilidade com o resto do sistema
    @property
    def monthly_fee(self):
        return self.default_monthly_fee_type.amount if self.default_monthly_fee_type else Decimal('0.00')

    @property
    def enrollment_fee(self):
        return self.default_enrollment_fee_type.amount if self.default_enrollment_fee_type else Decimal('0.00')
    
    def __str__(self):
        return f"{self.name} ({self.get_level_display()})"
    
    @property
    def get_duration_display(self):
        val = float(self.duration_years)
        if val >= 1.0:
            return f"{int(val)} Ano(s)" if val % 1 == 0 else f"{val} Anos"
        
        # 0.0833 é aproximadamente 1/12 (1 mês)
        if val >= 0.08:
            months = round(val * 12)
            return f"{months} Mês(es)"
        
        weeks = round(val * 52)
        return f"{weeks} Semana(s)"


class GradeLevel(BaseModel): # Renomeado de Grade para evitar confusão com 'Notas'
    name = models.CharField(max_length=50, help_text="Ex: 10ª Classe")
    course = models.ForeignKey(Course, on_delete=models.CASCADE, related_name='grade_levels')
    level_index = models.PositiveIntegerField(help_text="Sequence number (1, 2, 3...)")
    
    
    fee_percentage_increase = models.DecimalField(
        max_digits=5, decimal_places=2, default=0.00, 
        help_text="Ex: 10.00 para cobrar 10% a mais que o valor base do curso no FeeType"
    )

    total_monthly_fee = models.DecimalField(
        max_digits=12, decimal_places=2, default=0.00,
        help_text="Preço final calculado (Base + % + IVA) para esta classe."
    )

    def save(self, *args, **kwargs):
        # Lógica de negócio no servidor para garantir integridade
        # 1. Busca o preço base do curso (via FeeType associado)
        base_fee = self.course.default_monthly_fee_type.amount if self.course.default_monthly_fee_type else 0
        
        # 2. Calcula o acréscimo da classe
        increase = Decimal(str(self.fee_percentage_increase)) / 100
        price_before_tax = base_fee + (base_fee * increase)
        
        # 3. Aplica o IVA do curso
        tax_pct = Decimal('0.00')
        if self.course.taxa_iva:
            # Extração da percentagem do nome ou campo específico do seu TaxaIVAAGT
            # Assumindo que seu modelo TaxaIVAAGT tem um campo 'valor' ou similar
            tax_pct = Decimal(str(self.course.taxa_iva.tax_percentage)) / 100
        
        self.total_monthly_fee = price_before_tax + (price_before_tax * tax_pct)
        
        super().save(*args, **kwargs)
        

    @property
    def calculated_monthly_fee(self):
        base_fee = self.course.monthly_fee # Puxa do FeeType via property
        if self.fee_percentage_increase > 0:
            return base_fee * (1 + (self.fee_percentage_increase / 100))
        return base_fee

    def next_level(self):
        """Retorna a próxima classe dentro do mesmo curso."""
        return GradeLevel.objects.filter(
            course=self.course, 
            level_index=self.level_index + 1
        ).first()
    
    class Meta:
        ordering = ['course', 'level_index']
        unique_together = ('course', 'level_index')

    def __str__(self):
        return f"{self.name} - {self.course.name}"


class Subject(BaseModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=20, blank=True)
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.CASCADE, related_name='subjects')
    workload_hours = models.PositiveIntegerField(help_text="Carga horária anual")
    
    def __str__(self):
        return f"{self.name} ({self.grade_level})"


class Class(BaseModel):
    name = models.CharField(max_length=50, help_text="Ex: 10ª A")
    academic_year = models.ForeignKey(AcademicYear, on_delete=models.PROTECT)
    grade_level = models.ForeignKey(GradeLevel, on_delete=models.PROTECT)
    main_teacher = models.ForeignKey('teachers.Teacher', on_delete=models.SET_NULL, null=True, blank=True, related_name='homeroom_classes')
    capacity = models.PositiveIntegerField(default=30, help_text="Limite definido pelo Admin")
    period = models.CharField(max_length=20, choices=[('AM', 'Manhã'), ('PM', 'Tarde'), ('NIGHT', 'Noite')])
    room_number = models.CharField(max_length=10)

    @property
    def current_occupancy(self):
        try:
            return self.enrollments_records.all().count()
        except Exception:
            return 0

    @property
    def has_vacancy(self):
        return self.current_occupancy < self.capacity
    
    def validate_vacancy(self):
        """Método utilitário para validar lotação"""
        if not self.has_vacancy:
            raise ValidationError(
                _(f"A turma {self.name} atingiu a capacidade máxima de {self.capacity} alunos.")
            )
    
    class Meta:
        verbose_name = "Class (Turma)"
        verbose_name_plural = "Classes (Turmas)"

    def __str__(self):
        # Usar .name explicitamente evita que o Django tente resolver 
        # o objeto completo caso ele esteja em estado lazy ou corrompido
        return f"{self.name} - {self.academic_year.name if self.academic_year else 'Sem Ano'}"


class VacancyRequest(BaseModel):
    """Solicitação quando a sala está cheia"""
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE)
    target_grade = models.ForeignKey(GradeLevel, on_delete=models.CASCADE)
    message = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=[('pending', 'Pendente'), ('approved', 'Aprovado'), ('denied', 'Negado')], default='pending')
    is_resolved = models.BooleanField(default=False)

    

class AttendanceLimit(models.IntegerChoices):
    """Limites rigorosos do Artigo 25º, ponto 8 do Decreto 424/25"""
    ONE_PERIOD = 3, "3 Faltas (p/ disciplinas de 1 tempo/semana)"
    TWO_PERIODS = 4, "4 Faltas (p/ disciplinas de 2 tempos/semana)"
    MANY_PERIODS = 5, "5 Faltas (p/ disciplinas de +2 tempos/semana)"
# --- MODELOS Obrigatórios para Pautas ---


class StudentGrade(BaseModel):
    """
    Onde as notas residem. Segue o padrão Angolano/Internacional de 3 Trimestres.
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='academic_grades')
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE)
    klass = models.ForeignKey(Class, on_delete=models.CASCADE)
    
    unjustified_absences = models.PositiveIntegerField(default=0, verbose_name="Faltas Injustificadas")
    is_failed_by_attendance = models.BooleanField(default=False, verbose_name="Retido por Faltas")

    # 1º Trimestre
    mac1 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="MAC 1")
    npp1 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="NPP 1")
    npt1 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="NPT 1")
    mt1 = models.DecimalField(max_digits=4, decimal_places=1, editable=False, default=0.0, verbose_name="MT 1")

    # 2º Trimestre
    mac2 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="MAC 2")
    npp2 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="NPP 2")
    npt2 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="NPT 2")
    mt2 = models.DecimalField(max_digits=4, decimal_places=1, editable=False, default=0.0, verbose_name="MT 2")

    # 3º Trimestre
    mac3 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="MAC 3")
    npp3 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="NPP 3")
    npt3 = models.DecimalField(max_digits=4, decimal_places=1, default=0.0, verbose_name="NPT 3")
    mt3 = models.DecimalField(max_digits=4, decimal_places=1, editable=False, default=0.0, verbose_name="MT 3")

    # Resultado Final
    mf = models.DecimalField(max_digits=4, decimal_places=1, editable=False, default=0.0, verbose_name="Média Final")


    exame_nacional = models.DecimalField(max_digits=4, decimal_places=1, null=True, blank=True)

    def get_qualitative_classification(self, value, grade_level_index):
        """
        Mapeamento OBRIGATÓRIO conforme Decreto 424/25 e 167/23.
        grade_level_index: número da classe (ex: 1, 5, 10, 12)
        """
        val = float(value)
        
        # --- REGIME A: ENSINO PRIMÁRIO (1ª à 6ª Classe) - ANEXO I ---
        # Escala de 0 a 10 valores
        if grade_level_index <= 6:
            if val >= 9.0: return "Excelente"
            if val >= 7.0: return "Bom"
            if val >= 5.0: return "Suficiente"
            return "Insuficiente" # 1 a 4 valores

        # --- REGIME B: ENSINO SECUNDÁRIO (7ª à 12ª/13ª Classe) - ANEXO II ---
        # Escala de 0 a 20 valores
        else:
            if val >= 17.0: return "Excelente"
            if val >= 14.0: return "Bom"
            if val >= 10.0: return "Suficiente"
            if val >= 6.0:  return "Insuficiente"
            return "Mau" # Até 5 valores


    class Meta:
        unique_together = ('student', 'subject', 'klass')
        verbose_name = "Nota do Aluno"
        verbose_name_plural = "Notas dos Alunos"

    def _calculate_term_average(self, mac, npp, npt, config):
        """Calcula a média do trimestre com arredondamento de 1 casa decimal."""
        if config:
            w_mac = float(config.weight_mac)
            w_npp = float(config.weight_npp)
            w_npt = float(config.weight_npt)
            total_weight = w_mac + w_npp + w_npt
            
            if total_weight > 0:
                raw_average = ((float(mac) * w_mac) + (float(npp) * w_npp) + (float(npt) * w_npt)) / total_weight
                return round(raw_average, 1) # Arredonda 9.45 para 9.5
        
        # Fallback padrão
        raw_average = (float(mac) + float(npp) + float(npt)) / 3
        return round(raw_average, 1)

    def save(self, *args, **kwargs):
        # 1. Cálculo das Médias Trimestrais (Aritmética Simples - Art 5º)
        self.mt1 = (float(self.mac1) + float(self.npp1) + float(self.npt1)) / 3
        self.mt2 = (float(self.mac2) + float(self.npp2) + float(self.npt2)) / 3
        self.mt3 = (float(self.mac3) + float(self.npp3) + float(self.npt3)) / 3

        # 2. Média Final (MF)
        raw_mf = (float(self.mt1) + float(self.mt2) + float(self.mt3)) / 3
        
        # 3. RIGOR LEGAL DE ARREDONDAMENTO (Artigo 16.º, ponto 2)
        # 9.5 vira 10. Usamos a lógica: se a parte decimal >= 0.5, arredonda para cima.
        decimal_part = raw_mf - math.floor(raw_mf)
        if decimal_part >= 0.5:
            self.mf = math.ceil(raw_mf)
        else:
            self.mf = math.floor(raw_mf)

        super().save(*args, **kwargs)
    

    def check_attendance_failure(self, weekly_periods):
        """
        Executa o algoritmo de retenção do Artigo 25º.
        Retorna True se o aluno excedeu o limite.
        """
        limit = 5 # Default para mais de 2 tempos
        if weekly_periods == 1:
            limit = 3
        elif weekly_periods == 2:
            limit = 4
            
        if self.unjustified_absences >= limit:
            self.is_failed_by_attendance = True
            return True
        return False

    def get_final_display_grade(self, grade_level_index):
        """
        Lógica de Exibição OBRIGATÓRIA:
        1ª-6ª: Palavra (Até 10v)
        7ª-13ª: Número (Até 20v)
        """
        val = float(self.mf)
        
        # ENSINO PRIMÁRIO: Exclusivamente Qualitativa (Regra do Chefe)
        if grade_level_index <= 6:
            if val >= 9.0: return "Excelente"
            if val >= 7.0: return "Bom"
            if val >= 5.0: return "Suficiente"
            return "Insuficiente"

        # ENSINO SECUNDÁRIO/MÉDIO/TÉCNICO: Apenas Número (Tomei Nota!)
        return f"{val:.0f}" # Arredondado para unidade mais próxima conforme Art. 16º

    def __str__(self):
        return f"{self.student.full_name} | {self.subject.name} | MF: {self.mf}"


class AcademicGlobal(BaseModel):
    """
    Configurações globais da escola/tenant.
    """
    #tenant = models.OneToOneField('customers.Client', null=True, blank=True, on_delete=models.CASCADE, related_name='academic_config')
    is_pedagogical_break = models.BooleanField(
        default=False,
        verbose_name="Pausa Pedagógica (Bloquear Notas)"
    )
    break_exceptions = models.ManyToManyField(
        'teachers.Teacher',
        blank=True,
        related_name='pedagogical_break_overrides'
    )

    class Meta:
        verbose_name = "Configuração Académica Global"
        verbose_name_plural = "Configurações Académicas Globais"


class AcademicEvent(BaseModel):
    class Category(models.TextChoices):
        EXAM = 'EXAM', 'Prova/Exame'
        HOLIDAY = 'HOLIDAY', 'Feriado/Pausa'
        EVENT = 'EVENT', 'Evento/Actividade'
        MEETING = 'MEETING', 'Reunião de Pais'

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=Category.choices)
    start_date = models.DateTimeField()
    end_date = models.DateTimeField(null=True, blank=True)
    klass = models.ForeignKey('Class', on_delete=models.SET_NULL, null=True, blank=True, help_text="Vazio para toda a escola")

    executive_report_emails = models.TextField(
        blank=True, 
        help_text="E-mails que receberão o BI mensal (separe por vírgula)."
    )

    class Meta:
        ordering = ['start_date']


class Classroom(BaseModel):
    """Representa a sala física na unidade escolar."""
    name = models.CharField(max_length=50) # Ex: Sala 12, Laboratório A
    capacity = models.PositiveIntegerField()
    
    def __str__(self):
        return f"{self.name})"

class TimetableSlot(BaseModel):
    """
    Onde o tempo, espaço, professor e alunos se cruzam.
    """
    DAYS_OF_WEEK = (
        (1, 'Segunda-feira'), (2, 'Terça-feira'), (3, 'Quarta-feira'),
        (4, 'Quinta-feira'), (5, 'Sexta-feira'), (6, 'Sábado'),
    )

    class_room = models.ForeignKey('Class', on_delete=models.CASCADE, related_name='slots')
    subject = models.ForeignKey('Subject', on_delete=models.CASCADE)
    teacher = models.ForeignKey('teachers.Teacher', on_delete=models.CASCADE)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE)
    
    day_of_week = models.PositiveSmallIntegerField(choices=DAYS_OF_WEEK)
    start_time = models.TimeField()
    end_time = models.TimeField()

    def clean(self):
        """
        ALGORITMO DE DETECÇÃO DE CONFLITOS (Enterprise Logic).
        Evita sobreposição de Professor, Sala ou Turma no mesmo horário.
        """
        conflicts = TimetableSlot.objects.filter(
            day_of_week=self.day_of_week,
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exclude(pk=self.pk)

        # 1. Conflito de Professor
        if conflicts.filter(teacher=self.teacher).exists():
            raise ValidationError(f"Conflito: O professor {self.teacher} já tem aula neste horário.")

        # 2. Conflito de Sala Física
        if conflicts.filter(classroom=self.classroom).exists():
            raise ValidationError(f"Conflito: A sala {self.classroom} já está ocupada.")

        # 3. Conflito de Turma
        if conflicts.filter(class_room=self.class_room).exists():
            raise ValidationError(f"Conflito: A turma {self.class_room} já tem outra disciplina neste horário.")

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)




class LessonPlan(BaseModel):
    """
    O plano de aula que o professor cria ("Ir para a aula").
    Gera notificações para o diretor.
    """
    allocation = models.ForeignKey('teachers.TeacherSubject', on_delete=models.CASCADE)
    date = models.DateField(default=timezone.now)
    topic = models.CharField(max_length=255, verbose_name="Sumário/Tema")
    content = models.TextField(verbose_name="Conteúdo Programático")
    
    started_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    
    is_signed = models.BooleanField(default=False, help_text="Assinatura eletrónica do professor")

    def __str__(self):
        return f"Aula: {self.topic} - {self.allocation.teacher}"

class StudentAuditLog(BaseModel):
    """
    Regra: "O aluno vai ver no histórico tudo o que o diretor editou".
    """
    student = models.ForeignKey('students.Student', on_delete=models.CASCADE, related_name='audit_logs')
    changed_by = models.ForeignKey('core.User', on_delete=models.SET_NULL, null=True)
    field_changed = models.CharField(max_length=100)
    old_value = models.TextField(blank=True, null=True)
    new_value = models.TextField(blank=True, null=True)
    
    def __str__(self):
        return f"Alteração em {self.student}: {self.field_changed}"
    


