



class SOTARQExporter:
    """
    Motor Supremo v5.0 - Production Ready.
    Design System: Indigo + Orange + AGT Compliance
    """

    @staticmethod
    def _get_tenant_colors(tenant):
        """Retorna as cores do tenant ou defaults indigo/laranja."""
        if tenant and hasattr(tenant, 'primary_color') and tenant.primary_color:
            primary = colors.HexColor(tenant.primary_color)
        else:
            primary = colors.HexColor("#4338ca")  # Indigo-700

        if tenant and hasattr(tenant, 'secondary_color') and tenant.secondary_color:
            secondary = colors.HexColor(tenant.secondary_color)
        else:
            secondary = colors.HexColor("#f97316")  # Orange-500

        return {
            'primary': primary,
            'secondary': secondary,
            'primary_dark': colors.HexColor("#3730a3"),  # Indigo-800
            'secondary_dark': colors.HexColor("#ea580c"),  # Orange-600
            'black': colors.HexColor("#000000"),
            'white': colors.HexColor("#ffffff"),
            'gray_50': colors.HexColor("#f9fafb"),
            'gray_100': colors.HexColor("#f3f4f6"),
            'gray_200': colors.HexColor("#e5e7eb"),
            'gray_400': colors.HexColor("#9ca3af"),
            'gray_600': colors.HexColor("#4b5563"),
            'gray_800': colors.HexColor("#1f2937"),
            'success': colors.HexColor("#10b981"),
            'danger': colors.HexColor("#ef4444"),
        }

    @staticmethod
    def _get_agt_footer_text():
        """Retorna texto do rodapé AGT baseado no .env"""
        software_id = getattr(settings, 'AGT_ID_SISTEMA', 'SOTARQ-SCHOOL')
        cert_number = getattr(settings, 'AGT_CERTIFICATE_NUMBER', '000/AGT/2026')
        return f"{software_id} - Processado por Programa validado número {cert_number}"

    @staticmethod
    def _get_bank_info(tenant):
        """Retorna informações bancárias ativas do tenant."""
        try:
            # Busca a primeira conta bancária ativa
            account = BankAccount.objects.filter(is_active=True).first()
            if account:
                # AJUSTADO: Usando account_number em vez de account_holder
                #return f"Banco: {account.bank_name} | Conta: {account.account_number} | IBAN: {account.iban}"
                return f"{account.bank_name} | {account.account_number} | {account.iban}"
        except Exception:
            pass
        return "Dados bancários não configurados"

    @staticmethod
    def _get_tenant_logo(tenant):
        """Retorna path do logo ou None."""
        if tenant and hasattr(tenant, 'logo') and tenant.logo:
            try:
                return tenant.logo.path
            except Exception:
                pass
        return None

    @staticmethod
    def _get_tenant_contact_info(tenant):
        """Retorna informações de contato do tenant."""
        info = {
            'address': getattr(tenant, 'address', 'Endereço não configurado'),
            'phone': getattr(tenant, 'phone', 'N/A'),
            'email': getattr(tenant, 'email', 'N/A'),
            'website': getattr(tenant, 'website', 'N/A'),
            'nif': getattr(tenant, 'nif', 'N/A')
        }
        return info

    @staticmethod
    def generate_fiscal_document(instance, doc_type_code, is_copy=False, page_format='A4'):
        """
        Gera documento fiscal unificado com design enterprise.
        """
        buffer = BytesIO()

        if page_format == '80mm':
            page_size = (8.0 * cm, 28.0 * cm)  # Aumentado para caber logo e info extra
            margin = 0.4 * cm
        else:
            page_size = A4
            margin = 2.0 * cm

        p = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size

        data = SOTARQExporter._extract_document_data(instance)
        C = SOTARQExporter._get_tenant_colors(data['tenant'])

        if page_format == 'A4':
            SOTARQExporter._draw_a4_production(p, data, width, height, margin, is_copy, C)
        else:
            SOTARQExporter._draw_80mm_production(p, data, width, height, margin, is_copy, C)

        p.showPage()
        p.save()
        return buffer.getvalue()

    @staticmethod
    def _extract_document_data(instance):
        """Extrai e normaliza dados do documento."""
        tenant = getattr(instance, 'tenant', None)

        # Se não tiver tenant direto, tenta pegar via student
        if not tenant and hasattr(instance, 'student') and instance.student:
            if hasattr(instance.student, 'user') and instance.student.user:
                tenant = getattr(instance.student.user, 'tenant', None)

        # Cliente/Aluno
        client_info = {
            'name': "CONSUMIDOR FINAL",
            'nif': "999999999",
            'id': "N/A",
            'address': "N/A"
        }

        if hasattr(instance, 'student') and instance.student:
            student = instance.student
            client_info.update({
                'name': student.full_name.upper(),
                'nif': getattr(student, 'nif', "999999999"),
                'id': f"PROC: {student.registration_number}",
                'address': getattr(student, 'address', 'N/A')
            })

        # Número do documento
        doc_number = getattr(instance, 'number',
                           getattr(instance, 'numero_documento',
                                  getattr(instance, 'invoice', {}).get('number', 'S/N')))

        # Status exato do Invoice
        #status_display = instance.get_status_display() if hasattr(instance, 'get_status_display') else instance.status
        #agt_status = "NORMAL" if instance.status in ['paid', 'confirmed'] else "ANULADO"

        issue_date = getattr(instance, 'issue_date', None)
        date_str = issue_date.strftime('%d/%m/%Y') if issue_date else 'N/A'

        tax_pct = instance.tax_type.tax_percentage if getattr(instance, 'tax_type', None) else 0

        return {
            'tenant': tenant,
            'client': client_info,
            'doc_number': doc_number,
            'doc_type': getattr(instance, 'get_doc_type_display', lambda: 'DOCUMENTO')().upper(), # get_doc_type_display vai chamar o DocType (código) e transformar FT em Fatura em Maiúscula
            'date': date_str,
            'items': list(getattr(instance, 'items', []).all()) if hasattr(instance, 'items') else [],
            'subtotal': getattr(instance, 'subtotal', 0),
            'discount': getattr(instance, 'discount_amount', 0),
            'tax_amount': getattr(instance, 'tax_amount', 0),
            'total': getattr(instance, 'total', 0),
            'tax_percentage': tax_pct,
            'instance': instance,
        }

    @staticmethod
    def _draw_80mm_production(p, data, width, height, margin, is_copy, C):
        """Layout térmico 80mm com logo e cores do tenant."""
        y = height - 0.5 * cm

        # 1. LOGO DO TENANT
        logo_path = SOTARQExporter._get_tenant_logo(data['tenant'])
        if logo_path:
            try:
                # Logo centralizado, tamanho máximo 3cm de largura
                logo_w = 3.0 * cm
                logo_h = 1.5 * cm
                logo_x = (width - logo_w) / 2
                p.drawImage(logo_path, logo_x, y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True)
                y -= logo_h + 0.3 * cm
            except Exception:
                y -= 0.2 * cm
        else:
            y -= 0.2 * cm

        # 2. NOME DO TENANT (dinâmico)
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 10)
        tenant_name = data['tenant'].name.upper() if data['tenant'] else "SOTARQ SYSTEM"
        p.drawCentredString(width / 2, y, tenant_name)

        # 3. INFO DO TENANT (endereço, telefone)
        y -= 0.4 * cm
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 7)
        contact = SOTARQExporter._get_tenant_contact_info(data['tenant'])
        info_line = f"{contact['address'][:40]} | Tel: {contact['phone']}"
        p.drawCentredString(width / 2, y, info_line)

        y -= 0.3 * cm
        p.drawCentredString(width / 2, y, f"Site: {contact['website']}")

        # 4. NIF DO TENANT
        y -= 0.4 * cm
        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica", 8)
        nif = getattr(data['tenant'], 'nif', '999999999') if data['tenant'] else '999999999'
        p.drawCentredString(width / 2, y, f"NIF: {nif}")

        # Linha decorativa indigo
        y -= 0.5 * cm
        p.setStrokeColor(C['primary'])
        p.setLineWidth(1)
        p.line(margin, y, width - margin, y)

        # 5. TIPO E NÚMERO DO DOCUMENTO
        y -= 0.6 * cm
        #p.setFillColor(C['secondary']) # pega a cor secundária do tenant
        p.setFillColor(C['black'])
        p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(width / 2, y, f"{data['doc_type']}")

        y -= 0.4 * cm
        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica-Bold", 9)
        p.drawCentredString(width / 2, y, f"Nº {data['doc_number']}")

        # 6. STATUS EXATO DO INVOICE
        y -= 0.4 * cm
        #status_color = C['success'] if data['status'] == 'paid' else C['danger'] if data['status'] == 'cancelled' else C['secondary']
        #p.setFillColor(status_color)
        pill_w = 3.0 * cm
        pill_x = (width - pill_w) / 2
        p.roundRect(pill_x, y - 0.1 * cm, pill_w, 0.5 * cm, 0.15 * cm, fill=1, stroke=0)
        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 8)
        #p.drawCentredString(width / 2, y, data['status_display'].upper())

        # Indicador de segunda via
        if is_copy:
            y -= 0.6 * cm
            p.setFillColor(C['danger'])
            p.setFont("Helvetica-Bold", 8)
            p.drawCentredString(width / 2, y, ">>> 2ª VIA <<<")

        # Linha decorativa laranja
        y -= 0.5 * cm
        p.setStrokeColor(C['secondary'])
        p.setLineWidth(0.8)
        p.line(margin, y, width - margin, y)

        # 7. DADOS DO CLIENTE COM ENDEREÇO
        y -= 0.6 * cm
        p.setFillColor(C['black'])  # AJUSTADO: Cor preta conforme solicitado
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin, y, "CLIENTE")

        y -= 0.35 * cm
        p.setFillColor(C['gray_50'])
        p.setFont("Helvetica-Bold", 9)
        name = data['client']['name'][:32] + '..' if len(data['client']['name']) > 32 else data['client']['name']
        p.drawString(margin, y, name)

        y -= 0.3 * cm
        p.setFont("Helvetica", 7)
        p.setFillColor(C['gray_600'])
        p.drawString(margin, y, f"NIF: {data['client']['nif']}")

        y -= 0.25 * cm
        p.drawString(margin, y, data['client']['id'])

        # ENDEREÇO DO CLIENTE
        y -= 0.25 * cm
        p.drawString(margin, y, f"End: {data['client']['address'][:35]}")

        y -= 0.4 * cm
        p.setStrokeColor(C['gray_200'])
        p.setLineWidth(0.5)
        p.line(margin, y, width - margin, y)

        # 8. TABELA DE ITENS
        y -= 0.5 * cm
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 8)
        p.drawString(margin, y, "DESCRIÇÃO")
        p.drawRightString(width - margin, y, "TOTAL")

        y -= 0.2 * cm
        p.setStrokeColor(C['primary'])
        p.setLineWidth(0.6)
        p.line(margin, y, width - margin, y)

        p.setFont("Helvetica", 8)
        item_y = y - 0.35 * cm

        for idx, item in enumerate(data['items']):
            # Zebra striping
            if idx % 2 == 0:
                p.setFillColor(C['gray_50'])
                p.rect(margin, item_y - 0.08 * cm, width - 2 * margin, 0.4 * cm, fill=1, stroke=0)

            p.setFillColor(C['gray_800'])
            desc = item.description[:30] + '..' if len(item.description) > 30 else item.description
            p.drawString(margin + 0.05 * cm, item_y, desc)
            p.drawRightString(width - margin, item_y, f"{item.amount:,.2f}")
            item_y -= 0.45 * cm

        y = item_y - 0.3 * cm
        p.setStrokeColor(C['gray_200'])
        p.line(margin, y, width - margin, y)

        # 9. TOTAIS
        y -= 0.6 * cm
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 8)
        p.drawString(2.5 * cm, y, "Valor Base:")
        p.drawRightString(width - margin, y, f"{data['subtotal']:,.2f} Kz")

        if data['discount'] > 0:
            y -= 0.4 * cm
            p.setFillColor(C['danger'])
            p.drawString(2.5 * cm, y, "Desconto:")
            p.drawRightString(width - margin, y, f"- {data['discount']:,.2f} Kz")

        y -= 0.4 * cm
        p.setFillColor(C['gray_600'])
        p.drawString(2.5 * cm, y, f"IVA ({data['tax_percentage']:g}%):")
        p.drawRightString(width - margin, y, f"{data['tax_amount']:,.2f} Kz")

        # Linha antes do total
        y -= 0.5 * cm
        p.setStrokeColor(C['secondary'])
        p.setLineWidth(1.2)
        p.line(2 * cm, y, width - margin, y)

        # TOTAL DESTACADO
        y -= 0.7 * cm
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 11)
        p.drawString(margin, y, "TOTAL A PAGAR")
        p.setFillColor(C['secondary'])
        p.drawRightString(width - margin, y, f"{data['total']:,.2f} Kz")

        # 10. QR CODE COM FALLBACK VISUAL
        y -= 2.0 * cm
        qr_size = 2.5 * cm
        qr_x = (width - qr_size) / 2

        # Fundo branco para QR
        p.setFillColor(C['white'])
        p.rect(qr_x - 0.15 * cm, y - qr_size - 0.15 * cm, qr_size + 0.3 * cm, qr_size + 0.3 * cm,
               fill=1, stroke=0)
        p.setStrokeColor(C['gray_200'])
        p.rect(qr_x - 0.15 * cm, y - qr_size - 0.15 * cm, qr_size + 0.3 * cm, qr_size + 0.3 * cm,
               fill=0, stroke=1)

        qr_drawn = False
        try:
            # Tentativa de gerar QR code AGT
            qr_img = generate_agt_qrcode_image(data['instance'])
            if qr_img:
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                p.drawImage(ImageReader(qr_buffer), qr_x, y - qr_size,
                           width=qr_size, height=qr_size, preserveAspectRatio=True)
                qr_drawn = True
        except Exception as e:
            print(f"QR Error: {e}")

        if not qr_drawn:
            # Visual fallback se QR falhar
            p.setFillColor(C['gray_400'])
            p.setFont("Helvetica", 6)
            p.drawCentredString(width / 2, y - qr_size / 2, "[QR AGT]")
            p.drawCentredString(width / 2, y - qr_size / 2 - 0.4 * cm, "Verificação")

        # Label AGT
        y -= qr_size + 0.5 * cm
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 7)
        p.drawCentredString(width / 2, y, "AGT - Autoridade Geral Tributária")

        # 11. DADOS BANCÁRIOS DINÂMICOS
        y -= 0.6 * cm
        bank_info = SOTARQExporter._get_bank_info(data['tenant'])
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 3)
        # Quebra linha se for muito longo
        if len(bank_info) > 45:
            p.drawCentredString(width / 2, y, bank_info[:45])
            y -= 0.25 * cm
            p.drawCentredString(width / 2, y, bank_info[45:])
        else:
            p.drawCentredString(width / 2, y, bank_info)

        # 12. TEXTO DO .ENV CENTRALIZADO
        y -= 0.6 * cm
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 6)
        agt_text = SOTARQExporter._get_agt_footer_text()
        p.drawCentredString(width / 2, y, agt_text)

        # 13. MENSAGEM FISCAL OBRIGATÓRIA
        y -= 0.5 * cm
        p.setFillColor(C['gray_400'])
        p.setFont("Helvetica", 6)
        p.drawCentredString(width / 2, y, "Os bens/Serviços foram colocados à disposição")
        y -= 0.2 * cm
        p.drawCentredString(width / 2, y, "do cliente no local e data do documento.")

    @staticmethod
    def _draw_a4_production(p, data, width, height, margin, is_copy, C):
        #"""Layout A4 production com indigo/laranja e dados dinâmicos."""
        content_w = width - 2 * margin

        def draw_line(y_pos, color=C['gray_200'], width_line=content_w, x_start=margin, thickness=0.5):
            p.setStrokeColor(color)
            p.setLineWidth(thickness)
            p.line(x_start, y_pos, x_start + width_line, y_pos)

        # =========================================================================
        # 1. HEADER COM LOGO E CORES INDIGO/LARANJA
        # =========================================================================
        header_h = 5.0 * cm
        header_y = height - margin - header_h

        # Fundo indigo claro
        p.setFillColor(colors.HexColor("#e0e7ff"))  # Indigo-100
        p.rect(margin, header_y, content_w, header_h, fill=1, stroke=0)

        # Barra superior indigo
        p.setFillColor(C['primary'])
        p.rect(margin, height - margin - 0.4 * cm, content_w, 0.4 * cm, fill=1, stroke=0)

        # Barra inferior laranja (destaque)
        p.setFillColor(C['secondary'])
        p.rect(margin, header_y, content_w, 0.3 * cm, fill=1, stroke=0)

        left_x = margin + 0.8 * cm
        top_y = height - margin - 0.8 * cm

        # LOGO DO TENANT (esquerda)
        logo_path = SOTARQExporter._get_tenant_logo(data['tenant'])
        if logo_path:
            try:
                logo_w = 2.5 * cm
                logo_h = 2.0 * cm
                p.drawImage(logo_path, left_x, top_y - logo_h, width=logo_w, height=logo_h, preserveAspectRatio=True)
                text_start_y = top_y - logo_h - 0.3 * cm
            except Exception:
                text_start_y = top_y - 0.5 * cm
        else:
            text_start_y = top_y - 0.5 * cm

        # NOME DO TENANT
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 18)
        tenant_name = data['tenant'].name.upper() if data['tenant'] else "SOTARQ SYSTEM"
        p.drawString(left_x, text_start_y, tenant_name)

        # INFO DO TENANT (endereço, telefone, site)
        text_start_y -= 0.6 * cm
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 9)
        contact = SOTARQExporter._get_tenant_contact_info(data['tenant'])
        p.drawString(left_x, text_start_y, f"{contact['address']}")

        text_start_y -= 0.4 * cm
        p.drawString(left_x, text_start_y, f"Tel: {contact['phone']} | {contact['website']}")

        text_start_y -= 0.4 * cm
        p.setFillColor(C['gray_800'])
        p.setFont("Helvetica-Bold", 9)
        nif = getattr(data['tenant'], 'nif', '999999999') if data['tenant'] else '999999999'
        p.drawString(left_x, text_start_y, f"NIF: {nif}")

        # TIPO DE DOCUMENTO (direita, laranja)
        right_x = margin + content_w - 0.8 * cm
        doc_y = height - margin - 1.2 * cm

        p.setFillColor(C['secondary'])
        p.setFont("Helvetica-Bold", 28)
        p.drawRightString(right_x, doc_y, data['doc_type'])

        p.setFillColor(C['primary_dark'])
        p.setFont("Helvetica-Bold", 14)
        p.drawRightString(right_x, doc_y - 0.9 * cm, f"Nº {data['doc_number']}")

        # STATUS EXATO DO INVOICE (pill colorido)
        
        pill_w = 3.5 * cm
        pill_h = 0.9 * cm
        pill_x = right_x - pill_w
        pill_y = doc_y - 2.0 * cm

        #p.setFillColor(status_color)
        p.roundRect(pill_x, pill_y, pill_w, pill_h, 0.25 * cm, fill=1, stroke=0)
        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 11)


        # Data e 2ª via
        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 10)
        p.drawRightString(right_x, pill_y - 0.5 * cm, f"Data: {data['date']}")

        if is_copy:
            p.setFillColor(C['danger'])
            p.setFont("Helvetica-Bold", 12)
            p.drawRightString(right_x, pill_y - 1.0 * cm, "2ª VIA")

        current_y = header_y - 1.0 * cm

        # =========================================================================
        # 2. DADOS DO CLIENTE COM ENDEREÇO
        # =========================================================================
        client_h = 3.2 * cm

        # Fundo cinza claro com borda indigo à esquerda
        p.setFillColor(C['gray_50'])
        p.rect(margin, current_y - client_h, content_w, client_h, fill=1, stroke=0)

        p.setFillColor(C['primary'])
        p.rect(margin, current_y - client_h, 0.2 * cm, client_h, fill=1, stroke=0)

        p.setFillColor(C['black'])
        p.setFont("Helvetica-Bold", 11)
        p.drawString(left_x, current_y - 0.8 * cm, "CLIENTE / CUSTOMER")

        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica-Bold", 12)
        p.drawString(left_x, current_y - 1.5 * cm, data['client']['name'])

        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 10)
        p.drawString(left_x, current_y - 2.2 * cm, f"NIF: {data['client']['nif']}  |  {data['client']['id']}")

        # ENDEREÇO DO CLIENTE
        p.drawString(left_x, current_y - 2.8 * cm, f"Endereço: {data['client']['address']}")

        current_y -= client_h + 1.0 * cm

        # =========================================================================
        # 3. TABELA DE ITENS - DESIGN INDIGO/LARANJA
        # =========================================================================
        table_data = [["Descrição", "Qtd", "Preço Unit.", "Desconto", "Total"]]

        for item in data['items']:
            table_data.append([
                item.description,
                "1",
                f"{item.amount:,.2f}",
                "0,00",
                f"{item.amount:,.2f}"
            ])

        if not data['items']:
            table_data.append([
                f"Pagamento - {data['doc_type']} {data['doc_number']}",
                "1",
                f"{data['total']:,.2f}",
                "0,00",
                f"{data['total']:,.2f}"
            ])

        col_widths = [
            content_w * 0.45,
            content_w * 0.10,
            content_w * 0.15,
            content_w * 0.15,
            content_w * 0.15,
        ]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)

        style = TableStyle([
            # Cabeçalho indigo
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('TEXTCOLOR', (0, 0), (-1, 0), C['white']),
            ('BACKGROUND', (0, 0), (-1, 0), C['primary']),
            ('ALIGN', (0, 0), (0, 0), 'LEFT'),
            ('ALIGN', (1, 0), (-1, 0), 'RIGHT'),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('LEFTPADDING', (0, 0), (0, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),

            # Corpo
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('TEXTCOLOR', (0, 1), (-1, -1), C['gray_800']),
            ('ALIGN', (0, 1), (0, -1), 'LEFT'),
            ('ALIGN', (1, 1), (-1, -1), 'RIGHT'),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 10),
            ('TOPPADDING', (0, 1), (-1, -1), 10),

            # Linhas
            ('LINEBELOW', (0, 0), (-1, 0), 2, C['secondary']),  # Linha laranja após header
            ('LINEBELOW', (0, 1), (-1, -2), 0.5, C['gray_200']),
            ('LINEBELOW', (0, -1), (-1, -1), 1.5, C['primary']),
        ])

        # Zebra striping
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                style.add('BACKGROUND', (0, i), (-1, i), C['gray_50'])

        table.setStyle(style)

        tw, th = table.wrapOn(p, content_w, current_y - margin)
        table.drawOn(p, margin, current_y - th)

        table_bottom = current_y - th
        current_y = table_bottom - 1.0 * cm

        # =========================================================================
        # 4. TOTAIS - Card com destaque laranja
        # =========================================================================
        totals_w = 8.5 * cm
        totals_h = 4.5 * cm
        totals_x = margin + content_w - totals_w
        totals_y = current_y - totals_h

        # Fundo cinza claro
        p.setFillColor(C['gray_50'])
        p.rect(totals_x, totals_y, totals_w, totals_h, fill=1, stroke=0)

        # Barra superior laranja
        p.setFillColor(C['secondary'])
        p.rect(totals_x, totals_y + totals_h - 0.25 * cm, totals_w, 0.25 * cm, fill=1, stroke=0)

        line_x_left = totals_x + 0.8 * cm
        line_x_right = totals_x + totals_w - 0.8 * cm
        line_y = totals_y + totals_h - 0.9 * cm

        p.setFillColor(C['gray_600'])
        p.setFont("Helvetica", 10)

        p.drawString(line_x_left, line_y, "Subtotal")
        p.drawRightString(line_x_right, line_y, f"{data['subtotal']:,.2f} Kz")
        line_y -= 0.8 * cm

        if data['discount'] > 0:
            p.setFillColor(C['danger'])
            p.drawString(line_x_left, line_y, "Desconto")
            p.drawRightString(line_x_right, line_y, f"- {data['discount']:,.2f} Kz")
            p.setFillColor(C['gray_600'])
            line_y -= 0.8 * cm

        p.drawString(line_x_left, line_y, f"IVA ({data['tax_percentage']:g}%)")
        p.drawRightString(line_x_right, line_y, f"{data['tax_amount']:,.2f} Kz")
        line_y -= 1.0 * cm

        # Linha antes do total
        draw_line(line_y + 0.4 * cm, color=C['secondary'], width_line=totals_w - 1.6 * cm,
                 x_start=totals_x + 0.8 * cm, thickness=1.5)

        # TOTAL em indigo
        p.setFillColor(C['primary'])
        p.setFont("Helvetica-Bold", 16)
        p.drawString(line_x_left, line_y, "TOTAL")
        p.drawRightString(line_x_right, line_y, f"{data['total']:,.2f} Kz")

        line_y -= 0.7 * cm
        p.setFillColor(C['gray_400'])
        p.setFont("Helvetica", 8)
        p.drawString(line_x_left, line_y, "Taxas incluídas")

        current_y = totals_y - 1.5 * cm


        
        # =========================================================================
        # 5. RODAPÉ - Dados dinâmicos do .env e banco
        # =========================================================================
        footer_h = 4.0 * cm
        footer_y = margin

        # Fundo indigo escuro
        p.setFillColor(C['primary_dark'])
        p.rect(margin, footer_y, content_w, footer_h, fill=1, stroke=0)

        # Info à esquerda (branco)
        info_x = margin + 0.8 * cm
        info_y = footer_y + footer_h - 1.0 * cm

        p.setFillColor(C['white'])
        p.setFont("Helvetica-Bold", 10)
        p.drawString(info_x, info_y, "Dados para Pagamento")

        # Dados bancários dinâmicos
        p.setFont("Helvetica", 9)
        info_y -= 0.6 * cm
        bank_info = SOTARQExporter._get_bank_info(data['tenant'])
        # Quebra em duas linhas se necessário
        if len(bank_info) > 60:
            p.drawString(info_x, info_y, bank_info[:60])
            info_y -= 0.5 * cm
            p.drawString(info_x, info_y, bank_info[60:])
        else:
            p.drawString(info_x, info_y, bank_info)

        # Texto do .env centralizado no rodapé
        p.setFont("Helvetica-Bold", 8)
        agt_text = SOTARQExporter._get_agt_footer_text()
        p.drawString(info_x, footer_y + 0.8 * cm, agt_text)

        # Mensagem fiscal obrigatória
        p.setFont("Helvetica", 8)
        p.drawString(info_x, footer_y + 0.4 * cm, "Os bens/Serviços foram colocados à disposição do cliente no local e data do documento.")

        # QR Code à direita
        qr_size = 3.0 * cm
        qr_x = margin + content_w - qr_size - 0.8 * cm
        qr_y = footer_y + 0.5 * cm

        # Fundo branco para QR
        p.setFillColor(C['white'])
        p.rect(qr_x - 0.2 * cm, qr_y - 0.2 * cm, qr_size + 0.4 * cm, qr_size + 0.4 * cm,
               fill=1, stroke=0)
        p.setStrokeColor(C['gray_200'])
        p.rect(qr_x - 0.2 * cm, qr_y - 0.2 * cm, qr_size + 0.4 * cm, qr_size + 0.4 * cm,
               fill=0, stroke=1)

        qr_drawn = False
        try:
            #from apps.fiscal.utils import generate_agt_qrcode_image
            qr_img = generate_agt_qrcode_image(data['instance'])
            if qr_img:
                qr_buffer = BytesIO()
                qr_img.save(qr_buffer, format='PNG')
                qr_buffer.seek(0)
                p.drawImage(ImageReader(qr_buffer), qr_x, qr_y,
                           width=qr_size, height=qr_size, preserveAspectRatio=True)
                qr_drawn = True
        except Exception as e:
            print(f"QR Error A4: {e}")

        if not qr_drawn:
            p.setFillColor(C['gray_400'])
            p.setFont("Helvetica", 7)
            p.drawCentredString(qr_x + qr_size/2, qr_y + qr_size/2, "[QR AGT]")
            p.drawCentredString(qr_x + qr_size/2, qr_y + qr_size/2 - 0.4 * cm, "Indisponível")

        # Label AGT ao lado do QR
        
        #p.setFillColor(C['white'])
        #p.setFont("Helvetica-Bold", 9)
        #p.drawRightString(qr_x - 0.5 * cm, qr_y + qr_size - 0.3 * cm, "AGT")
        #p.setFont("Helvetica", 8)
        #p.drawRightString(qr_x - 0.5 * cm, qr_y + qr_size - 0.8 * cm, "QR Code")        

