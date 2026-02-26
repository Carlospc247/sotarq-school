from django.db import transaction
from django.utils import timezone

from apps.core.models import User
from .models import Student, Guardian, StudentGuardian, EnrollmentRequest
from apps.portal.models import PortalProfile

def convert_candidacy_to_student(enrollment_request):
    """
    Transforma uma candidatura paga num Aluno Oficial e ativa o acesso ao Portal.
    """
    with transaction.atomic():
        # 1. Gerar credenciais
        first_name = enrollment_request.full_name.split()[0].lower()
        username = f"std_{enrollment_request.id}_{first_name}"
        password = User.objects.make_random_password()
        
        user = User.objects.create_user(
            username=username,
            email=enrollment_request.guardian_email,
            password=password,
            first_name=enrollment_request.full_name
        )

        # 2. Criar Perfil de Estudante
        student = Student.objects.create(
            user=user,
            full_name=enrollment_request.full_name,
            birth_date=enrollment_request.birth_date,
            gender=enrollment_request.gender,
            registration_number=f"MAT-{timezone.now().year}-{enrollment_request.id:04d}"
        )

        # 3. Criar Encarregado e Perfil do Portal
        guardian, _ = Guardian.objects.get_or_create(
            phone=enrollment_request.guardian_phone,
            defaults={'full_name': enrollment_request.guardian_name, 'email': enrollment_request.guardian_email, 'user': user}
        )
        
        PortalProfile.objects.create(user=user, student=student, guardian=guardian)

        StudentGuardian.objects.create(
            student=student,
            guardian=guardian,
            relationship='other',
            is_financial_responsible=True
        )

        # 4. Finalização
        enrollment_request.status = EnrollmentRequest.Status.ENROLLED
        enrollment_request.save()
        
        return student, password # Retorna a password para enviar por SMS/Email

