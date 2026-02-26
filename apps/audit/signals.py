from django.db import models, transaction, IntegrityError
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.contrib.contenttypes.models import ContentType
from django.conf import settings
from .middleware import get_current_user, get_current_ip
import json
import sys
from django.contrib.auth.signals import user_logged_in
from .models import AuditLog, SecurityAlert
from apps.core.utils import get_geo_info # Função interna que consulta a GeoIP
from django.utils import timezone





# Define which models to EXCLUDE (noise reduction)
EXCLUDED_APPS = ['admin', 'sessions', 'contenttypes', 'audit', 'migrations']

def should_audit(instance):
    """
    Determine if an instance should be audited.
    """
    # 1. Safety check for object metadata
    if not hasattr(instance, '_meta'):
        return False

    # 2. Exclude specific Apps
    if instance._meta.app_label in EXCLUDED_APPS:
        return False
        
    # 3. Exclude specific Models
    if instance._meta.model_name in ['permission', 'group', 'contenttype', 'session', 'migration']:
        return False

    # 4. SKIP AUDIT DURING TESTS
    if 'test' in sys.argv:
        return False
        
    return True

@receiver(post_save)
def audit_post_save(sender, instance, created, raw, **kwargs):
    # --- [A VACINA CRÍTICA] ---
    # Se raw=True, o Django está a carregar fixtures ou a migrar.
    # NÃO executar lógica de auditoria aqui.
    if raw:
        return

    if not should_audit(instance):
        return

    # Evitar recursão infinita (AuditLog a auditar-se a si mesmo)
    if sender == AuditLog:
        return

    user = get_current_user()
    ip = get_current_ip()
    
    action = 'CREATE' if created else 'UPDATE'
    
    try:
        # Serializar PK para string para evitar erros com UUIDs
        pk_val = str(instance.pk)
        
        # Tenta obter o ContentType. Se falhar (migrações iniciais), o except apanha.
        content_type = ContentType.objects.get_for_model(instance)
        
        # Usamos transaction.atomic para garantir integridade, 
        # mas envolvemos em try/except para não parar o sistema se falhar.
        with transaction.atomic():
            AuditLog.objects.create(
                user=user if user and user.is_authenticated else None,
                action=action,
                content_type=content_type, # Passamos o objeto ContentType explicitamente
                object_id=pk_val,
                ip_address=ip,
                details=json.dumps({'pk': pk_val}, default=str)
            )
    except (IntegrityError, Exception):
        # Se o ContentType não existir ou houver erro de banco, ignora silenciosamente.
        # Isto permite que o setup_saas_final.py corra até ao fim.
        pass

@receiver(post_delete)
def audit_post_delete(sender, instance, **kwargs):
    if not should_audit(instance):
        return

    if sender == AuditLog:
        return

    user = get_current_user()
    ip = get_current_ip()
    
    try:
        pk_val = str(instance.pk)
        content_type = ContentType.objects.get_for_model(instance)
        
        with transaction.atomic():
            AuditLog.objects.create(
                user=user if user and user.is_authenticated else None,
                action='DELETE',
                content_type=content_type,
                object_id=pk_val,
                ip_address=ip,
                details=json.dumps({'pk': pk_val}, default=str)
            )
    except (IntegrityError, Exception):
        pass



@receiver(user_logged_in)
def audit_user_login(sender, request, user, **kwargs):
    """
    Rigor SOTARQ: Captura automática de acessos.
    Funciona para Alunos, Professores e Subagentes.
    """
    ip = get_current_ip() # Captura via middleware
    
    AuditLog.objects.create(
        user=user,
        action='LOGIN',
        content_type=ContentType.objects.get_for_model(user),
        object_id=str(user.pk),
        ip_address=ip,
        details=json.dumps({
            'tenant': request.tenant.schema_name,
            'user_agent': request.META.get('HTTP_USER_AGENT', 'unknown')
        })
    )



@receiver(user_logged_in)
def monitor_access_anomalies(sender, request, user, **kwargs):
    ip = get_current_ip()
    current_geo = get_geo_info(ip) # Retorna {'city': 'Malanje', 'country': 'AO'}
    
    # Busca o último login legítimo deste usuário
    last_login_log = AuditLog.objects.filter(
        user=user, action='LOGIN'
    ).order_by('-timestamp').first()

    if last_login_log:
        last_details = json.loads(last_login_log.details)
        last_geo = last_details.get('geo_info', {})
        
        # Rigor Sênior: Verificação de "Viagem Impossível"
        if last_geo.get('city') != current_geo.get('city'):
            # Se a mudança de cidade ocorreu em menos de 1 hora
            time_diff = timezone.now() - last_login_log.timestamp
            if time_diff.total_seconds() < 3600: 
                SecurityAlert.objects.create(
                    user=user,
                    last_ip=last_login_log.ip_address,
                    current_ip=ip,
                    last_location=last_geo.get('city', 'Desconhecido'),
                    current_location=current_geo.get('city'),
                    risk_level='HIGH'
                )


