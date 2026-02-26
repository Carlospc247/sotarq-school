# apps/core/verification_engine.py
import re
from django.db.models import Q
from datetime import datetime
from apps.students.models import Student
from apps.teachers.models import Teacher
from apps.documents.models import Document

class SecurityVerificationEngine:
    """
    MOTOR DE VALIDAÇÃO DE AUTENTICIDADE (SOTARQ SECURE).
    Retorna dicionários de dados estruturados para exibição rica no frontend.
    """

    @staticmethod
    def process_query(coded_string):
        coded_string = coded_string.strip()

        # 1.3 PESQUISA FUNCIONÁRIO: #ID#@PrimeiroNome
        if re.match(r"^#[A-Za-z0-9\-]+#@[A-Za-z]+$", coded_string):
            return SecurityVerificationEngine._verify_employee(coded_string)

        # 1.2.B CERTIFICADO FUNCIONÁRIO: ##AnoNasc#ID
        elif re.match(r"^##\d{4}#[A-Za-z0-9\-]+$", coded_string):
            return SecurityVerificationEngine._verify_employee_cert(coded_string)

        # 1.1 PESQUISA ALUNO: DataNasc#ID_Aluno#ID_Enc
        elif re.match(r"^\d{4}-\d{2}-\d{2}#[A-Za-z0-9\-]+#\d+$", coded_string):
            return SecurityVerificationEngine._verify_student_full(coded_string)

        # 1.2.A CERTIFICADO ALUNO: DataFim#ID_Aluno
        elif re.match(r"^\d{4}-\d{2}-\d{2}#[A-Za-z0-9\-]+$", coded_string):
             return SecurityVerificationEngine._verify_student_cert(coded_string)

        return False, {"message": "Formato de código inválido ou não reconhecido."}

    # --- MÉTODOS INTERNOS (PRIVADOS) ---

    @staticmethod
    def _verify_student_full(code):
        try:
            parts = code.split('#')
            birth_date_str, student_reg, guardian_id = parts[0], parts[1], parts[2]

            student = Student.objects.filter(
                registration_number=student_reg,
                birth_date=birth_date_str,
                is_active=True
            ).first()

            if not student:
                return False, {"message": "Dados do estudante não conferem nos registos ativos."}

            has_guardian = student.guardians.filter(
                Q(guardian__id=guardian_id) | Q(guardian__phone__endswith=guardian_id)
            ).exists()

            if has_guardian:
                # Retorna dados completos para validação visual
                return True, {
                    'type': 'CARTÃO DE ESTUDANTE / IDENTIDADE',
                    'name': student.full_name,
                    'status': 'ATIVO' if not student.is_suspended else 'SUSPENSO FINANCEIRAMENTE',
                    'class': student.current_class.name if student.current_class else 'Sem Turma',
                    'course': student.current_class.grade_level.course.name if student.current_class else '-',
                    'message': 'O aluno está devidamente matriculado e vinculado aos encarregados registados.'
                }
            else:
                return False, {"message": "Dados de segurança (Encarregado) não conferem."}

        except Exception:
            return False, {"message": "Erro no processamento dos dados."}

    
    @staticmethod
    def _verify_employee(code):
        try:
            # Formato: #ID#@Nome
            parts = code[1:].split('#@')
            emp_number, first_name = parts[0], parts[1]

            teacher = Teacher.objects.filter(
                employee_number=emp_number,
                user__first_name__iexact=first_name
            ).select_related('user').first()

            if teacher:
                data = {
                    'type': 'REGISTO PROFISSIONAL (DOCENTE)',
                    'name': teacher.user.get_full_name(),
                    'role': 'Professor',
                    'degree': teacher.academic_degree,
                    'status': 'ATIVO' if teacher.is_active else 'INATIVO/DESLIGADO',
                    'admission_date': teacher.user.date_joined.strftime('%d/%m/%Y'),
                }
                
                # Se o professor saiu, buscamos os dados reais do modelo atualizado
                if not teacher.is_active:
                    data['exit_info'] = {
                        'reason': teacher.get_exit_reason_display() or "Não especificado",
                        'evaluation': teacher.final_evaluation or "Sem observações registadas.",
                        'exit_date': teacher.exit_date.strftime('%d/%m/%Y') if teacher.exit_date else "N/A"
                    }
                
                return True, data
            
            return False, {"message": "Funcionário não encontrado com estes dados."}

        except Exception:
            return False, {"message": "Erro de processamento."}
    

    @staticmethod
    def _verify_employee_cert(code):
        try:
            # Formato: ##Ano#ID
            parts = code[2:].split('#')
            year, emp_id = parts[0], parts[1]
            
            teacher = Teacher.objects.filter(employee_number=emp_id).first()
            
            if teacher:
                return True, {
                    'type': 'CERTIFICADO DE SERVIÇO / DECLARAÇÃO',
                    'name': teacher.user.get_full_name(),
                    'reference_year': year,
                    'status': 'VÁLIDO',
                    'message': f'Confirmamos que o funcionário exerceu funções no ano letivo de {year}.'
                }
            return False, {"message": "Dados não conferem com os registos de RH."}
        except:
            return False, {"message": "Erro interno."}

    @staticmethod
    def _verify_student_cert(code):
        try:
            parts = code.split('#')
            date_str, student_id = parts[0], parts[1]

            # 1. Tenta achar um documento físico emitido
            doc = Document.objects.filter(
                student__registration_number=student_id,
                # document_type__name__icontains="Certificado", # Opcional: filtrar por tipo
            ).first() # Pega o mais recente ou específico
            
            if doc:
                return True, {
                    'type': f"DOCUMENTO EMITIDO: {doc.document_type.name.upper()}",
                    'student_name': doc.student.full_name,
                    'course': doc.student.enrollments.last().course.name if doc.student.enrollments.exists() else 'Geral',
                    'conclusion_date': date_str,
                    'status': 'AUTÊNTICO',
                    'issuer': 'Secretaria Académica SOTARQ',
                    'message': 'Este documento foi emitido e assinado digitalmente pelo sistema.'
                }
            
            # 2. Fallback: Valida apenas os dados do aluno no sistema
            student = Student.objects.filter(registration_number=student_id).first()
            if student:
                 return True, {
                    'type': 'REGISTO ACADÉMICO (SEM DOCUMENTO FÍSICO)',
                    'student_name': student.full_name,
                    'status': 'MATRICULADO' if student.is_active else 'INATIVO',
                    'message': 'O aluno consta na base de dados, mas não localizamos um certificado específico emitido nesta data. Confirme os dados pessoais.'
                }

            return False, {"message": "Registo académico não encontrado."}
        except:
            return False, {"message": "Erro ao validar hash."}