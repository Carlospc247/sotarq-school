get_<field>_display() é automático do Django

Se você tem algo assim no seu DocumentoFiscal:

class DocumentoFiscal(models.Model):

    class DocType(models.TextChoices):
        FT = "FT", "Fatura"
        FR = "FR", "Fatura-Recibo"
        NC = "NC", "Nota de Crédito"

    tipo_documento = models.CharField(
        max_length=2,
        choices=DocType.choices
    )

O Django automaticamente cria:

instance.get_tipo_documento_display()



Usando class DocType(models.TextChoices): vai ficar get_doc_type_display




📌 O que ele realmente faz?

Ele retorna o label legível, não o valor armazenado.

Exemplo:

doc.tipo_documento  # "FT"
doc.get_tipo_documento_display()  # "Fatura"


⚠️ Agora vem a parte importante (SOTARQExporter)

Se o seu SOTARQExporter estiver usando:

doc.get_tipo_documento_display()

Ele vai receber:

"Fatura"

E NÃO:

"FT"
🎯 Para SAF-T / SOTARQ

Normalmente o que o exportador precisa é o código técnico:

FT

FR

NC

ND

Ou seja:

doc.tipo_documento

E não o display.

🧠 Quando usar cada um?
Método	Uso correto
tipo_documento	Exportação fiscal / XML / SAF-T
get_tipo_documento_display()	Interface, relatórios humanos
🔎 Então sua pergunta:

Isto deve ser indicado ou definido em alguma parte do código ou é por default?

Resposta:

✔ É automático por causa do choices.
❌ Você não precisa declarar nada.
⚠ Mas precisa decidir qual dos dois o exportador deve usar.

🚨 Possível erro arquitetural

Se você estiver usando o display() dentro do XML fiscal, isso pode quebrar conformidade.

Exportação fiscal deve usar:

doc.tipo_documento

Interface pode usar:

doc.get_tipo_documento_display()