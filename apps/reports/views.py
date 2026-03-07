# apps/reports/views.py
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.db.models import Count, Case, When, IntegerField
from apps.academic.views import is_manager_check, is_secretary_directors, is_teacher_pedagogic
from apps.reports.services.kpi_engine import AcademicKPIEngine
from django.http import JsonResponse

from apps.teachers.models import TeacherSubject
from .models import ReportDefinition, ReportExecution, ReportCategory
from apps.academic.models import AcademicYear, Class, StudentGrade
from django.contrib.admin.views.decorators import staff_member_required


# Acesso apenas para Administradores da Escola ou Diretores
@user_passes_test(is_manager_check)
def report_list(request):
    """Lista todos os tipos de relatórios e KPIs disponíveis."""
    categories = ReportCategory.objects.all().prefetch_related('reportdefinition_set')
    
    # RIGOR SOTARQ: Busca turmas que não foram deletadas (soft delete) 
    # e que pertencem ao ano letivo ativo no momento.
    classes = Class.objects.filter(
        deleted_at__isnull=True, 
        academic_year__is_active=True
    ).order_by('name')
    
    return render(request, 'reports/report_catalog.html', {
        'categories': categories,
        'classes': classes
    })

@user_passes_test(is_manager_check)
def execution_history(request):
    """Logs de auditoria de quem gerou o quê e quando."""
    executions = ReportExecution.objects.all().order_by('-started_at')[:50]
    return render(request, 'reports/execution_history.html', {
        'executions': executions
    })

@user_passes_test(is_secretary_directors)
def trigger_bulk_bulletins(request, class_id):
    """Dispara a tarefa Celery para gerar boletins da turma inteira."""
    klass = get_object_or_404(Class, id=class_id)
    
    # Busca a definição de boletim (deve estar criada no banco via Seed)
    definition, _ = ReportDefinition.objects.get_or_create(
        code='BULK_BULLETIN',
        defaults={'name': 'Emissão de Boletins em Massa', 'category_id': 1}
    )
    
    execution = ReportExecution.objects.create(
        report_definition=definition,
        executed_by=request.user,
        parameters={'class_id': class_id, 'class_name': klass.name},
        status='pending'
    )

    # Chamada assíncrona para não travar a UI
    from .tasks import task_bulk_generate_bulletins
    task_bulk_generate_bulletins.delay(
        request.tenant.schema_name, 
        execution.id, 
        class_id
    )

    messages.success(request, f"O processamento para a turma {klass.name} foi iniciado. Pode acompanhar o progresso no histórico.")
    return redirect('reports:execution_history')


@user_passes_test(is_teacher_pedagogic)
def pedagogical_quality_dashboard(request):
    """Dashboard de BI para análise de aproveitamento escolar."""
    current_year = AcademicYear.objects.filter(is_active=True).first()
    
    if not current_year:
        messages.warning(request, "Defina um Ano Letivo activo para ver as métricas.")
        return redirect('reports:report_catalog')

    engine = AcademicKPIEngine()
    teacher_stats = engine.calculate_teacher_performance(current_year.id)
    
    # Ordenar por menor taxa de aprovação para dar prioridade aos problemas
    alerts = sorted(teacher_stats, key=lambda x: x['pass_rate'])

    grade_distribution = StudentGrade.objects.filter(
        klass__academic_year=current_year
    ).aggregate(
        muito_mau=Count(Case(When(mt1__lt=5, then=1), output_field=IntegerField())),
        insuficiente=Count(Case(When(mt1__range=(5, 9.4), then=1), output_field=IntegerField())),
        satisfaz=Count(Case(When(mt1__range=(9.5, 13.4), then=1), output_field=IntegerField())),
        bom=Count(Case(When(mt1__range=(13.5, 17.4), then=1), output_field=IntegerField())),
        muito_bom=Count(Case(When(mt1__gte=17.5, then=1), output_field=IntegerField())),
    )

    # Convertemos para JSON para o Chart.js
    chart_data = json.dumps(list(grade_distribution.values()))

    return render(request, 'reports/pedagogical_dashboard.html', {
        'alerts': alerts,
        'year': current_year,
        'chart_data': chart_data
    })


def search_allocation_ajax(request):
    class_id = request.GET.get('class_id')
    if not class_id:
        return JsonResponse({'error': 'ID da turma não fornecido'}, status=400)

    # Rigor de Segurança: Filtramos pela turma e pelo Tenant do usuário logado
    query = TeacherSubject.objects.filter(
        class_room_id=class_id,
        class_room__academic_year__is_active=True
    )

    # Se não for gestor/diretor, filtra apenas as disciplinas do próprio professor
    if not (is_manager_check(request.user) or is_secretary_directors(request.user)):
        query = query.filter(teacher__user=request.user)

    allocations = query.select_related('subject').values(
        'id', 
        'subject__name', 
        'subject__code'
    )

    data = [
        {
            'id': a['id'], 
            'name': f"{a['subject__name']} ({a['subject__code']})"
        } for a in allocations
    ]
    
    return JsonResponse(data, safe=False)

