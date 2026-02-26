# apps/library/services_excel.py
import pandas as pd
from .models import Book, Loan

class LibraryDataEngine:
    @staticmethod
    def import_books_from_excel(file_ptr):
        """Processa até 1000 linhas de livros via Excel."""
        df = pd.read_excel(file_ptr)
        books_to_create = []
        for index, row in df.head(1000).iterrows():
            books_to_create.append(Book(
                title=row['titulo'],
                author=row['autor'],
                barcode=row['barcode'],
                category=row['categoria'],
                total_copies=row['quantidade'],
                available_copies=row['quantidade']
            ))
        Book.objects.bulk_create(books_to_create, ignore_conflicts=True)

    @staticmethod
    def export_overdue_report():
        """Gera lista de devedores e atrasados para Excel."""
        overdue = Loan.objects.filter(status='overdue').values(
            'borrower__full_name', 'book__title', 'expected_return_date'
        )
        return pd.DataFrame(list(overdue))


