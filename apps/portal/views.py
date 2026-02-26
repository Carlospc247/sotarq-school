# apps/portal/views.py
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from apps.academic.models import TimetableSlot, StudentGrade
from apps.library.models import Loan
from apps.students.models import Enrollment
from apps.finance.models import Invoice, Payment
from apps.cafeteria.models import Product, Wallet
from apps.academic.models import AcademicEvent
from django.db.models import Q, Sum
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from apps.students.models import Student
from apps.transport.models import Bus, TransportEnrollment




@login_required
def student_dashboard(request):
    # 1. Obter Perfil com segurança (Lógica existente mantida)
    try:
        profile = request.user.portal_profile
    except AttributeError:
        return redirect('admin:index')

    # Lógica de seleção de aluno (Mantida)
    my_students = None
    if hasattr(profile, 'guardian') and profile.guardian:
        my_students = Student.objects.filter(guardians__guardian=profile.guardian)
        active_student_id = request.session.get('active_portal_student_id')
        if active_student_id:
            student = my_students.filter(id=active_student_id).first()
        else:
            student = my_students.first()
            if student:
                request.session['active_portal_student_id'] = student.id
    else:
        student = getattr(profile, 'student', None)
    
    if not student:
        return render(request, 'portal/no_profile.html')

    # 3. Dados Académicos
    enrollment = Enrollment.objects.filter(student=student, status='active').first()
    academic_year = enrollment.academic_year if enrollment else None
    
    # --- SAÚDE ACADÉMICA ---
    grades = StudentGrade.objects.filter(student=student, klass__academic_year=academic_year)
    critical_subjects = [g.subject.name for g in grades if (g.mt1 or 0) < 10]
    failing_count = len(critical_subjects)
    
    health_status, health_color, sotarq_tip = "Excelente", "emerald", "Excelente desempenho! Continua assim."
    if failing_count > 0:
        health_status, health_color = "Em Alerta", "orange"
        sotarq_tip = f"Atenção a {critical_subjects[0]}. Revê os conteúdos."
    if failing_count > 2:
        health_status, health_color = "Crítico", "red"
        sotarq_tip = "Risco de Reprovação. Agenda uma tutoria urgente."

    # --- FINANCEIRO (CÁLCULO DINÂMICO) ---
    total_academic_months = 10
    paid_tuition_count = Invoice.objects.filter(
        student=student,
        status='paid',
        items__description__icontains="Propina"
    ).distinct().count()

    tuition_progress = min((paid_tuition_count / total_academic_months) * 100, 100) if total_academic_months > 0 else 0

    pending_invoices = Invoice.objects.filter(student=student, status__in=['pending', 'overdue'])
    has_overdue_invoices = pending_invoices.filter(status='overdue').exists()
    receipts = Invoice.objects.filter(student=student, status='paid').prefetch_related('payments')[:5]

    # --- EVENTOS ---
    events = AcademicEvent.objects.filter(start_date__gte=timezone.now()).order_by('start_date')[:3]

    library_loans = Loan.objects.filter(
        student=student,
        status__in=['active', 'overdue']
    ).select_related('book').order_by('expected_return_date')


    context = {
        'student': student,
        'my_students': my_students,
        'health_status': health_status,
        'health_color': health_color,
        'sotarq_tip': sotarq_tip,
        'failing_count': failing_count,
        'pending_invoices': pending_invoices,
        'has_overdue_invoices': has_overdue_invoices,
        'receipts': receipts,
        'events': events,
        'tuition_progress': tuition_progress,
        'paid_months': paid_tuition_count,
        'total_months': total_academic_months,
        'library_loans': library_loans,
    }
    return render(request, 'portal/dashboard.html', context)



@login_required
def nutrition_control(request):
    try:
        student = request.user.portal_profile.student
    except AttributeError:
        return redirect('portal:dashboard')

    all_products = Product.objects.filter(is_active=True)
    # Proteção caso o campo blocked_products não esteja definido no modelo Student
    blocked_ids = student.blocked_products.values_list('id', flat=True) if hasattr(student, 'blocked_products') else []
    
    return render(request, 'portal/nutrition_control.html', {
        'student': student,
        'all_products': all_products,
        'blocked_ids': blocked_ids
    })

@login_required
def switch_student_context(request, student_id):
    """Permite ao encarregado alternar entre os seus educandos."""
    try:
        profile = request.user.portal_profile
        if hasattr(profile, 'guardian') and profile.guardian:
            student = get_object_or_404(Student, id=student_id, guardians__guardian=profile.guardian)
            request.session['active_portal_student_id'] = student.id
    except AttributeError:
        pass
    
    return redirect('portal:dashboard')

@login_required
def nutrition_control(request):
    student = request.user.portal_profile.student
    all_products = Product.objects.filter(is_active=True)
    # Assumindo que o modelo Student tem um campo ManyToMany 'blocked_products'
    blocked_ids = student.blocked_products.values_list('id', flat=True)
    
    return render(request, 'portal/nutrition_control.html', {
        'student': student,
        'all_products': all_products,
        'blocked_ids': blocked_ids
    })



@login_required
def switch_student_context(request, student_id):
    """
    Permite ao encarregado alternar entre os seus educandos.
    """
    profile = request.user.portal_profile
    
    # Segurança: Verifica se o aluno solicitado realmente pertence a este encarregado
    if profile.guardian:
        student = get_object_or_404(Student, id=student_id, guardians__guardian=profile.guardian)
        request.session['active_portal_student_id'] = student.id
    
    return redirect('portal:dashboard')


@login_required
def student_timetable(request):
    """View para exibir o horário das aulas do aluno."""
    try:
        profile = request.user.portal_profile
        # Se for encarregado, usa o aluno ativo na sessão
        if hasattr(profile, 'guardian') and profile.guardian:
            student_id = request.session.get('active_portal_student_id')
            student = get_object_or_404(Student, id=student_id, guardians__guardian=profile.guardian)
        else:
            student = profile.student
    except AttributeError:
        return redirect('admin:index')

    # Busca os slots de horário da turma atual do aluno
    if student and student.current_class:
        timetable = TimetableSlot.objects.filter(
            class_room=student.current_class
        ).order_by('day_of_week', 'start_time')
    else:
        timetable = []

    return render(request, 'portal/timetable.html', {
        'student': student,
        'timetable': timetable,
        'days': TimetableSlot.DAYS_OF_WEEK
    })




@login_required
def verification_guide(request):
    """
    Exibe os códigos de autenticidade pessoais do utilizador logado.
    """
    user = request.user
    context = {
        'student': getattr(user, 'student_profile', None),
        'teacher': getattr(user, 'teacher_profile', None),
        'user': user
    }
    return render(request, 'portal/help/verification_guide.html', context)

@login_required
def student_live_tracking(request, bus_id):
    """
    Rigor de Elite: Localização GPS em tempo real no Portal do Encarregado.
    Herda do portal_base.html.
    """
    profile = request.user.portal_profile
    bus = get_object_or_404(Bus, id=bus_id)
    
    # Validação: O encarregado só vê se o filho está no transporte
    if profile.guardian:
        active_student_id = request.session.get('active_portal_student_id')
        student = get_object_or_404(Student, id=active_student_id, guardians__guardian=profile.guardian)
        
        # Verifica se o aluno tem inscrição ativa nesta rota/bus
        has_access = TransportEnrollment.objects.filter(student=student, route__bus=bus, is_active=True).exists()
        if not has_access:
            return redirect('portal:student_dashboard')

    return render(request, 'portal/live_tracking.html', {
        'bus': bus,
        'student': student if profile.guardian else profile.student
    })

# apps/portal/views.py

@login_required
def student_payments(request):
    """
    Rigor de Transparência: Lista de faturas e geração de referências.
    """
    profile = request.user.portal_profile
    active_student_id = request.session.get('active_portal_student_id')
    student = get_object_or_404(Student, id=active_student_id, guardians__guardian=profile.guardian)

    # Faturas pendentes com cálculo de mora dinâmico
    invoices = Invoice.objects.filter(student=student).order_by('-due_date')
    
    # Injetamos o cálculo de mora para o template
    for inv in invoices:
        inv.current_total_with_mora = inv.calculate_current_total()

    return render(request, 'portal/payments.html', {
        'student': student,
        'invoices': invoices,
    })


