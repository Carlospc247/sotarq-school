# apps/library/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from .models import Book, Loan, LibraryConfig
from .services import LibraryEngine, LibrarySecurityService
from apps.students.models import Student
from django.http import HttpResponse
from .utils.pdf_generator import generate_library_card_pdf
from .services_excel import LibraryDataEngine # Importação do motor Excel



@login_required
def library_dashboard(request):
    """Resumo da biblioteca: livros mais lidos, atrasos e stock."""
    context = {
        'total_books': Book.objects.count(),
        'active_loans': Loan.objects.filter(status='active').count(),
        'overdue_loans': Loan.objects.filter(status='overdue').count(),
        'active_loans_list': Loan.objects.filter(status__in=['active', 'overdue']).order_by('expected_return_date'),
        'recent_books': Book.objects.all().order_by('-created_at')[:5],
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
def register_loan(request):
    """Regista um novo empréstimo com verificação de segurança."""
    if request.method == 'POST':
        student_id = request.POST.get('student_id')
        barcode = request.POST.get('barcode')
        
        student = get_object_or_404(Student, id=student_id)
        book = get_object_or_404(Book, barcode=barcode)
        
        # 1. Verificar disponibilidade do livro
        if book.available_copies <= 0:
            messages.error(request, f"O livro '{book.title}' não tem cópias disponíveis.")
            return redirect('library:register_loan')
            
        # 2. Verificar restrições do aluno (Financeiras/Suspensão) via Service
        can_borrow, message = LibrarySecurityService.can_borrow(student)
        if not can_borrow:
            messages.error(request, message)
            return redirect('library:register_loan')

        # 3. Criar o Empréstimo
        config = LibraryConfig.objects.first()
        Loan.objects.create(
            student=student,
            book=book,
            expected_return_date=timezone.now().date() + timezone.timedelta(days=config.max_loan_days)
        )
        
        # Atualizar Stock
        book.available_copies -= 1
        book.save()
        
        messages.success(request, f"Empréstimo de '{book.title}' registado com sucesso para {student.full_name}.")
        return redirect('library:library_dashboard')

        context = {
            'students': Student.objects.filter(is_active=True).only('id', 'full_name', 'process_number')
        }

    return render(request, 'library/loan_form.html')

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
    """
    Interface para importação massiva de livros.
    Rigor: Apenas Staff/Admin podem popular o acervo.
    """
    if request.method == 'POST' and request.FILES.get('excel_file'):
        file = request.FILES['excel_file']
        try:
            # Chama o motor de dados baseado em Pandas
            LibraryDataEngine.import_books_from_excel(file)
            messages.success(request, "Importação concluída com sucesso! Acervo atualizado.")
        except Exception as e:
            messages.error(request, f"Erro técnico na leitura do Excel: {str(e)}")
        return redirect('library:book_list')
    
    return render(request, 'library/import_form.html')

