import csv
from io import BytesIO
from datetime import datetime
from urllib.parse import quote
from django.http import HttpResponse
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings


def get_font_path():
    """Получение пути к шрифту с поддержкой кириллицы"""
    possible_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial_black.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Arial_Black.ttf'),
        '/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf',
        '/System/Library/Fonts/Arial.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None


def register_font():
    """Регистрация шрифта"""
    font_path = get_font_path()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('ArialBlack', font_path))
            return 'ArialBlack'
        except:
            pass
    return 'Helvetica-Bold'


HAS_CUSTOM_FONT = get_font_path() is not None


def export_statistics_csv(request, data, export_type, start_date, end_date):
    """Экспорт статистики в CSV"""
    today = datetime.now().date()
    
    if export_type == 'students':
        filename = f"статистика_слушателей_{start_date}_по_{end_date}.csv"
    else:
        filename = f"статистика_оценок_{start_date}_по_{end_date}.csv"
    
    encoded_filename = quote(filename)
    
    response = HttpResponse(
        content_type='text/csv; charset=utf-8-sig',
        headers={
            'Content-Disposition': f'attachment; filename="{encoded_filename}"',
        }
    )
    
    response.write('\ufeff')
    writer = csv.writer(response)
    
    writer.writerow(["Статистика преподавателя"])
    writer.writerow([f"Период: {start_date} — {end_date}"])
    writer.writerow([f"Сгенерировано: {today}"])
    writer.writerow([])
    
    if export_type == 'students':
        writer.writerow(['Курс', 'Всего слушателей', 'Завершили курс', 'Средний прогресс (%)'])
        for item in data:
            writer.writerow([
                item['course_name'],
                item['total_students'],
                item['completed_students'],
                f"{item['avg_progress']:.1f}%"
            ])
    else:
        writer.writerow(['Курс', 'Всего оценок', 'Средний балл'])
        for item in data:
            writer.writerow([
                item['course_name'],
                item['total_grades'],
                f"{item['avg_score']:.1f}"
            ])
    
    writer.writerow([])
    writer.writerow(["Отчет сгенерирован автоматически системой управления курсами"])
    
    return response


def export_statistics_pdf(request, data, export_type, start_date, end_date):
    """Экспорт статистики в PDF"""
    today = datetime.now().date()
    
    if export_type == 'students':
        filename = f"статистика_слушателей_{start_date}_по_{end_date}.pdf"
    else:
        filename = f"статистика_оценок_{start_date}_по_{end_date}.pdf"
    
    encoded_filename = quote(filename)
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{encoded_filename}"'
    response['Content-Type'] = 'application/pdf'
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    try:
        doc = SimpleDocTemplate(
            response,
            pagesize=landscape(A4),
            topMargin=18*mm,
            leftMargin=12*mm,
            rightMargin=12*mm,
            title=filename.replace('.pdf', '')
        )
        elements = []
        
        font_name = register_font()
        title_font = font_name if HAS_CUSTOM_FONT else 'Helvetica-Bold'
        text_font = font_name if HAS_CUSTOM_FONT else 'Helvetica'
        
        styles = getSampleStyleSheet()
        
        styles.add(ParagraphStyle(
            name='BigTitle',
            fontName=title_font,
            fontSize=22,
            textColor=colors.HexColor('#8A4FFF'),
            alignment=1,
            spaceAfter=20,
            leading=26
        ))
        
        styles.add(ParagraphStyle(
            name='Info',
            fontName=text_font,
            fontSize=12,
            textColor=colors.HexColor('#6B4E9B'),
            spaceAfter=8,
            leading=14
        ))
        
        styles.add(ParagraphStyle(
            name='Cell',
            fontName=text_font,
            fontSize=9.5,
            leading=11,
            alignment=0
        ))
        
        styles.add(ParagraphStyle(
            name='CellCenter',
            fontName=text_font,
            fontSize=9.5,
            leading=11,
            alignment=1
        ))
        
        if export_type == 'students':
            elements.append(Paragraph("СТАТИСТИКА СЛУШАТЕЛЕЙ", styles['BigTitle']))
        else:
            elements.append(Paragraph("СТАТИСТИКА ОЦЕНОК", styles['BigTitle']))
        
        elements.append(Paragraph(f"<b>Период:</b> {start_date} — {end_date}", styles['Info']))
        elements.append(Paragraph(f"<b>Сгенерировано:</b> {today}", styles['Info']))
        elements.append(Spacer(1, 12))
        
        if export_type == 'students':
            data_table = [['Курс', 'Слушателей', 'Завершили', 'Прогресс']]
            col_widths = [250, 100, 100, 100]
            
            for item in data:
                data_table.append([
                    Paragraph(item['course_name'][:60], styles['Cell']),
                    Paragraph(str(item['total_students']), styles['CellCenter']),
                    Paragraph(str(item['completed_students']), styles['CellCenter']),
                    Paragraph(f"{item['avg_progress']:.1f}%", styles['CellCenter']),
                ])
        else:
            data_table = [['Курс', 'Всего оценок', 'Средний балл']]
            col_widths = [350, 150, 150]
            
            for item in data:
                data_table.append([
                    Paragraph(item['course_name'][:60], styles['Cell']),
                    Paragraph(str(item['total_grades']), styles['CellCenter']),
                    Paragraph(f"{item['avg_score']:.1f}", styles['CellCenter']),
                ])
        
        table = Table(data_table, colWidths=col_widths, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#8A4FFF')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('FONTNAME', (0, 0), (-1, 0), title_font),
            ('FONTNAME', (0, 1), (-1, -1), text_font),
            ('FONTSIZE', (0, 0), (-1, 0), 11),
            ('FONTSIZE', (0, 1), (-1, -1), 9.5),
            ('GRID', (0, 0), (-1, -1), 0.7, colors.HexColor('#D8BFD8')),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FAF5FF')),
            ('LEFTPADDING', (0, 0), (-1, -1), 6),
            ('RIGHTPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ]))
        
        elements.append(table)
        doc.build(elements)
        
    except Exception as e:
        return HttpResponse(f"Ошибка при создании PDF: {str(e)}", status=500)
    
    return response