# apps/library/services_excel.py

import pandas as pd
from django.db import transaction
from .models import Book, Loan

class LibraryDataEngine:
    @staticmethod
    def import_books_from_excel(file):
        df = pd.read_excel(file)
        warnings = []
        
        with transaction.atomic():
            for index, row in df.iterrows():
                barcode = str(row['barcode']).strip()
                novo_total = int(row['quantidade_total'])
                
                # Validação de Título (Anti-Dirty Data)
                livro_existente = Book.objects.filter(barcode=barcode).first()
                if livro_existente and livro_existente.title.lower() != str(row['titulo']).strip().lower():
                    warnings.append(f"Linha {index+2}: Conflito de Barcode. '{row['titulo']}' ignorado.")
                    continue

                # Cálculo de Disponibilidade Real
                loans_out = Loan.objects.filter(
                    book__barcode=barcode, 
                    status__in=['active', 'overdue']
                ).count()

                # Se o novo total for menor que os livros na rua, a disponibilidade é 0
                nova_disponibilidade = max(0, novo_total - loans_out)
                
                Book.objects.update_or_create(
                    barcode=barcode,
                    defaults={
                        'title': row['titulo'],
                        'author': row['autor'],
                        'category': row['categoria'],
                        'total_copies': novo_total,
                        'available_copies': nova_disponibilidade
                    }
                )
        return warnings

