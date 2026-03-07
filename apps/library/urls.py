from django.urls import path
from . import views

app_name = 'library'

urlpatterns = [
    path('', views.library_dashboard, name='library_dashboard'),
    path('books/', views.book_list, name='book_list'),
    path('book/add/', views.book_add, name='book_add'),
    path('loan/new/', views.register_loan, name='register_loan'),
    path('return/<int:loan_id>/', views.process_return, name='process_return'),
    path('card/download/<int:student_id>/', views.download_library_card, name='download_library_card'),
    path('export/overdue/', views.export_overdue_excel, name='export_overdue'),
    path('import/books/', views.import_books_excel, name='import_books'),
    path('import/template/', views.download_import_template, name='download_template'),
]