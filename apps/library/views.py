# apps/library/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
import pandas as pd
from apps.core.models import User
from .models import Book, Loan, LibraryConfig
from .services import LibraryEngine, LibrarySecurityService
from apps.students.models import Student
from django.http import HttpResponse
from django.db import transaction
from .utils.pdf_generator import generate_library_card_pdf
from .services_excel import LibraryDataEngine # Importação do motor Excel




from django.db.models import F # Importação necessária para comparar campos
from django.utils import timezone
from .models import Loan, Book


@login_required
def library_dashboard(request):
    """
    Dashboard SOTARQ SCHOOL: Gestão Universal de Acervo e Empréstimos.
    Otimizado com F() expressions e busca indexada de utentes.
    """
    today = timezone.now()
    
    # KPI de Mérito: Filtra devoluções no prazo (actual <= expected)
    # Cálculo de performance: 10 pontos por cada devolução pontual no mês corrente.
    total_merit_month = Loan.objects.filter(
        actual_return_date__month=today.month,
        actual_return_date__year=today.year,
        actual_return_date__lte=F('expected_return_date')
    ).count() * 10

    context = {
        'total_books': Book.objects.count(),
        'active_loans': Loan.objects.filter(status='active').count(),
        'overdue_loans': Loan.objects.filter(status='overdue').count(),
        
        # Lista de empréstimos ativos e atrasados para a tabela principal
        'active_loans_list': Loan.objects.filter(
            status__in=['active', 'overdue']
        ).select_related('book', 'borrower').order_by('expected_return_date'),
        
        'recent_books': Book.objects.all().order_by('-created_at')[:5],
        
        # INJEÇÃO DE UTENTES: Unificação de Alunos e Staff para o Datalist
        # O .only() garante que não carreguemos dados pesados (biografias, senhas, etc) na memória.
        'utentes_list': User.objects.filter(is_active=True).only(
            'id', 'first_name', 'last_name', 'username'
        ).order_by('first_name'),
        
        'total_merit_points': total_merit_month,
    }
    
    return render(request, 'library/dashboard.html', context)


@login_required
def book_list(request):
    """Catálogo de livros com busca."""
    query = request.GET.get('q')
    books = Book.objects.all()
    if query:
        books = books.filter(title__icontains=query) | books.filter(author__icontains=query)
    return render(request, 'library/book_list.html', {'books': books})


@login_required
@transaction.atomic
def book_add(request):
    """
    Cadastro manual de itens no acervo via Modal.
    """
    if request.method == "POST":
        try:
            title = request.POST.get('title')
            author = request.POST.get('author')
            barcode = request.POST.get('barcode')
            category = request.POST.get('category')
            total_copies = int(request.POST.get('total_copies', 1))

            # Verificação de integridade: Barcode Único
            if Book.objects.filter(barcode=barcode).exists():
                messages.error(request, f"ERRO: O código de barras {barcode} já está registado no acervo.")
                return redirect('library:library_dashboard')

            Book.objects.create(
                title=title,
                author=author,
                barcode=barcode,
                category=category,
                total_copies=total_copies,
                available_copies=total_copies # Inicialmente todas disponíveis
            )
            messages.success(request, f"Livro '{title}' adicionado com sucesso ao SOTARQ Library!")
            
        except Exception as e:
            messages.error(request, f"Falha no cadastro: {str(e)}")
            
    return redirect('library:library_dashboard')




@login_required
@transaction.atomic
def register_loan(request):
    """
    Regista um novo empréstimo universal (Alunos/Staff).
    Rigor: Validação de presença de dados, tratamento de tipos e integridade de estoque.
    """
    if request.method == 'POST':
        user_id = request.POST.get('student_id')
        barcode = request.POST.get('barcode')
        
        # 1. VALIDAÇÃO DE PRESENÇA (Previne o erro de campo vazio)
        if not user_id or str(user_id).strip() == "":
            messages.error(request, "ERRO SOTARQ: Nenhum utente selecionado. Selecione um nome da lista de sugestões.")
            return redirect('library:library_dashboard')

        if not barcode:
            messages.error(request, "ERRO SOTARQ: O código de barras é obrigatório para identificar o livro.")
            return redirect('library:library_dashboard')

        try:
            # 2. BUSCA SEGURA DE UTENTE E LIVRO
            # get_object_or_404 aqui lida com IDs inexistentes
            borrower = get_object_or_404(User, id=user_id)
            book = get_object_or_404(Book, barcode=barcode)
            
            # 3. VERIFICAÇÃO DE DISPONIBILIDADE FÍSICA
            if book.available_copies <= 0:
                messages.error(request, f"Rigor SOTARQ: O exemplar '{book.title}' esgotou no acervo físico.")
                return redirect('library:library_dashboard')

            # 4. MOTOR DE SEGURANÇA (Regras Académicas/Financeiras)
            # Verifica se o User (independente de ser aluno ou staff) pode requisitar
            can_borrow, security_msg = LibrarySecurityService.can_borrow(borrower)
            if not can_borrow:
                messages.error(request, security_msg)
                return redirect('library:library_dashboard')

            # 5. CONFIGURAÇÃO DE PRAZOS (Multi-Tenant)
            config = LibraryConfig.objects.first()
            duration = config.max_loan_days if config else 7
            
            # 6. CRIAÇÃO DO REGISTO
            # O model Loan fará o cálculo automático da data no método .save()
            new_loan = Loan.objects.create(
                borrower=borrower,
                book=book,
                loan_duration_days=duration,
                status=Loan.Status.ACTIVE
            )
            
            # 7. ATUALIZAÇÃO TRANSACIONAL DE STOCK
            book.available_copies -= 1
            book.save()
            
            nome_utente = borrower.get_full_name() or borrower.username
            messages.success(
                request, 
                f"Empréstimo registado: '{book.title}' para {nome_utente}. "
                f"Data limite: {new_loan.expected_return_date.strftime('%d/%m/%Y')}."
            )
            
        except (ValueError, TypeError):
            messages.error(request, "ERRO TÉCNICO: O identificador enviado não é um número válido.")
        except Exception as e:
            messages.error(request, f"FALHA INESPERADA: {str(e)}")

        return redirect('library:library_dashboard')

    # Acesso via GET não permitido para esta ação
    return redirect('library:library_dashboard')


@login_required
def process_return(request, loan_id):
    """Processa a devolução e dispara lógica de multas ou mérito."""
    loan = get_object_or_404(Loan, id=loan_id)
    
    # Usar o Engine para processar a devolução (Gera multa se atrasado)
    LibraryEngine.register_return(loan.id)
    
    # Recarregar o objeto para verificar mérito
    loan.refresh_from_db()
    merit = LibrarySecurityService.process_return_merit(loan)
    
    if merit:
        messages.success(request, "Devolução registada. O aluno ganhou 10 pontos de mérito!")
    else:
        messages.warning(request, "Devolução registada com atraso. Multa gerada no financeiro.")
        
    return redirect('library:library_dashboard')



@login_required
def download_library_card(request, student_id):
    """Gera e entrega o cartão de leitor da biblioteca em PDF."""
    student = get_object_or_404(Student, id=student_id)
    
    # 1. Gera o PDF usando o utilitário que você já importou
    pdf_content = generate_library_card_pdf(student)
    
    # 2. Prepara a resposta HTTP para download
    response = HttpResponse(pdf_content, content_type='application/pdf')
    filename = f"Cartao_Biblioteca_{student.registration_number}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    
    return response


# apps/library/views.py
import pandas as pd
from django.http import HttpResponse

@login_required
def export_overdue_excel(request):
    """Exporta lista de devedores com rigor técnico."""
    overdue_list = Loan.objects.filter(status='overdue').select_related('book', 'borrower')[:1000]
    
    data = [{
        'Livro': l.book.title,
        'SKU': l.book.barcode,
        'Utente': l.borrower.full_name,
        'Cargo': l.borrower.current_role,
        'Vencimento': l.expected_return_date,
        'Dias de Atraso': (timezone.now().date() - l.expected_return_date).days,
        'Multa Estimada': (timezone.now().date() - l.expected_return_date).days * 500 # Exemplo
    } for l in overdue_list]

    df = pd.DataFrame(data)
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=Devedores_Sotarq.xlsx'
    df.to_excel(response, index=False)
    return response



@login_required
def import_books_excel(request):
    if request.method == 'POST' and request.FILES.get('excel_file'):
        file = request.FILES['excel_file']
        try:
            # Captura os avisos do motor
            warnings = LibraryDataEngine.import_books_from_excel(file)
            
            if warnings:
                for msg in warnings:
                    messages.warning(request, msg)
                messages.info(request, "Importação concluída com as ressalvas acima.")
            else:
                messages.success(request, "Importação 100% íntegra! Acervo atualizado.")
                
        except Exception as e:
            messages.error(request, f"Falha crítica no motor Excel: {str(e)}")
            
        return redirect('library:library_dashboard')
    
    return redirect('library:library_dashboard')




@login_required
def download_import_template(request):
    """
    Gera um modelo Excel (.xlsx) para o bibliotecário preencher.
    Rigor: Garante que as colunas batam com o motor de importação.
    """
    # Definimos as colunas que o seu LibraryDataEngine espera
    columns = ['titulo', 'autor', 'barcode', 'categoria', 'quantidade_total']
    
    # Criamos uma linha de exemplo para o usuário não ter dúvidas
    example_data = [{
        'titulo': 'Dom Casmurro',
        'autor': 'Machado de Assis',
        'barcode': '9788535914849',
        'categoria': 'Literatura Brasileira',
        'quantidade_total': 5
    }]
    
    df = pd.DataFrame(example_data, columns=columns)
    
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=SOTARQ_Library_Template.xlsx'
    
    with pd.ExcelWriter(response, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Importar Livros')
        
    return response


