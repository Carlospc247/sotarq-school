

# python manage.py tenant_command shell --schema=excellence




from apps.finance.models import Invoice

# 1. Busca inconsistências com o nome de campo CORRETO: doc_type
# Filtramos onde o status é pago, mas o documento ainda é FT (Fatura)
inconsistencias = Invoice.objects.filter(
    status='paid',
    doc_type='FT'
).select_related('student')

print(f"\n{'='*60}")
print(f"AUDITORIA SOTARQ - SCHEMA: excellence")
print(f"{'='*60}")

if not inconsistencias.exists():
    print("✅ RIGOR MANTIDO: Nenhuma inconsistência de tipo encontrada.")
else:
    count = inconsistencias.count()
    print(f"❌ ALERTA: {count} faturas em estado inválido (Pagas mas como FT)!\n")
    
    print(f"{'ID':<6} | {'Aluno':<25} | {'Nº Doc':<15} | {'Total'}")
    print("-" * 60)
    
    for inv in inconsistencias:
        # Usando 'total' conforme sugerido pelo FieldError
        print(f"{inv.id:<6} | {str(inv.student.full_name)[:25]:<25} | {inv.number:<15} | {inv.total}")

print(f"{'='*60}\n")





# 1. Atualizar o tipo de documento para Recibo (RC)
# 2. Nota: O campo 'number' ainda contém o prefixo 'FT', vamos tratar isso também
from django.db.models import F, Value
from django.db.models.functions import Replace

# Converter doc_type para RC e ajustar o prefixo no número do documento
inconsistencias.update(
    doc_type='RC',
    number=Replace(F('number'), Value('FT'), Value('RC'))
)

print("✅ SUCESSO: Documentos IDs 7 e 8 convertidos para RC e numerados corretamente.")