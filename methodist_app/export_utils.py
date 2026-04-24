import csv
from io import BytesIO
from datetime import datetime, timedelta
from urllib.parse import quote
from django.http import HttpResponse
from django.db.models import Count, Avg, Q
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
from django.conf import settings

from unireax_main.models import Course, UserCourse, Review


def get_font_path():
    """Получение пути к шрифту Arial Black"""
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
    """Регистрация шрифта Arial Black в reportlab"""
    font_path = get_font_path()
    if font_path:
        try:
            pdfmetrics.registerFont(TTFont('ArialBlack', font_path))
            return 'ArialBlack'
        except:
            pass
    return 'Helvetica-Bold'


HAS_CUSTOM_FONT = get_font_path() is not None


def export_statistics_csv(request, export_type, start_date, end_date):
    """Экспорт статистики в CSV"""
    today = datetime.now().date()
    
    if export_type == 'students':
        filename = f"статистика_слушателей_{start_date}_по_{end_date}.csv"
    else:
        filename = f"популярные_курсы_{start_date}_по_{end_date}.csv"
    
    encoded_filename = quote(filename)
    
    response = HttpResponse(
        content_type='text/csv; charset=utf-8-sig',
        headers={
            'Content-Disposition': f'attachment; filename="{encoded_filename}"',
        }
    )
    
    response.write('\ufeff')
    
    writer = csv.writer(response)
    
    writer.writerow(["Статистика курсов"])
    writer.writerow([f"Период: {start_date} — {end_date}"])
    writer.writerow([f"Сгенерировано: {today}"])
    writer.writerow([])
    
    if export_type == 'students':
        writer.writerow(['Курс', 'Всего записей', 'Завершено', 'В процессе', 'Процент завершения', 'Средний рейтинг'])
        
        my_courses = Course.objects.filter(created_by=request.user)
        for course in my_courses:
            enrollments = UserCourse.objects.filter(course=course)
            
            if start_date:
                enrollments = enrollments.filter(registration_date__gte=start_date)
            if end_date:
                enrollments = enrollments.filter(registration_date__lte=end_date)
            
            total = enrollments.count()
            completed = enrollments.filter(status_course=True).count()
            in_progress = total - completed
            completion_rate = (completed / total * 100) if total > 0 else 0
            avg_rating = Review.objects.filter(course=course, is_approved=True).aggregate(avg=Avg('rating'))['avg'] or 0
            
            writer.writerow([
                course.course_name,
                total,
                completed,
                in_progress,
                f"{completion_rate:.1f}%",
                f"{avg_rating:.2f}"
            ])
    else:
        writer.writerow(['Курс', 'Категория', 'Слушателей', 'Рейтинг', 'Тип курса', 'Часы'])
        
        popular_courses = Course.objects.annotate(
            total_students=Count('usercourse', filter=Q(usercourse__is_active=True)),
            avg_rating=Avg('review__rating', filter=Q(review__is_approved=True))
        ).filter(is_active=True).order_by('-total_students')[:50]
        
        for course in popular_courses:
            writer.writerow([
                course.course_name,
                course.course_category.course_category_name if course.course_category else 'Без категории',
                course.total_students,
                f"{course.avg_rating or 0:.2f}",
                course.course_type.course_type_name if course.course_type else '-',
                course.course_hours
            ])
    
    writer.writerow([])
    writer.writerow(["Отчет сгенерирован автоматически системой управления курсами"])
    
    return response


def export_statistics_pdf(request, export_type, start_date, end_date):
    """Экспорт статистики в PDF"""
    today = datetime.now().date()
    
    if export_type == 'students':
        filename = f"статистика_слушателей_{start_date}_по_{end_date}.pdf"
    else:
        filename = f"популярные_курсы_{start_date}_по_{end_date}.pdf"
    
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
            elements.append(Paragraph("ТОП ПОПУЛЯРНЫХ КУРСОВ", styles['BigTitle']))
        
        elements.append(Paragraph(f"<b>Период:</b> {start_date} — {end_date}", styles['Info']))
        elements.append(Paragraph(f"<b>Сгенерировано:</b> {today}", styles['Info']))
        elements.append(Spacer(1, 12))
        
        if export_type == 'students':
            data = [['Курс', 'Всего', 'Завершено', 'В процессе', 'Процент\nзавершения', 'Рейтинг']]
            col_widths = [180, 65, 75, 75, 85, 65]
            
            my_courses = Course.objects.filter(created_by=request.user)
            for course in my_courses:
                enrollments = UserCourse.objects.filter(course=course)
                
                if start_date:
                    enrollments = enrollments.filter(registration_date__gte=start_date)
                if end_date:
                    enrollments = enrollments.filter(registration_date__lte=end_date)
                
                total = enrollments.count()
                completed = enrollments.filter(status_course=True).count()
                in_progress = total - completed
                completion_rate = (completed / total * 100) if total > 0 else 0
                avg_rating = Review.objects.filter(course=course, is_approved=True).aggregate(avg=Avg('rating'))['avg'] or 0
                
                data.append([
                    Paragraph(course.course_name[:60], styles['Cell']),
                    Paragraph(str(total), styles['CellCenter']),
                    Paragraph(str(completed), styles['CellCenter']),
                    Paragraph(str(in_progress), styles['CellCenter']),
                    Paragraph(f"{completion_rate:.1f}%", styles['CellCenter']),
                    Paragraph(f"{avg_rating:.2f}", styles['CellCenter']),
                ])
        else:
            data = [['Курс', 'Категория', 'Слушателей', 'Рейтинг', 'Тип', 'Часы']]
            col_widths = [200, 120, 75, 70, 90, 60]
            
            popular_courses = Course.objects.annotate(
                total_students=Count('usercourse', filter=Q(usercourse__is_active=True)),
                avg_rating=Avg('review__rating', filter=Q(review__is_approved=True))
            ).filter(is_active=True).order_by('-total_students')[:50]
            
            for course in popular_courses:
                data.append([
                    Paragraph(course.course_name[:60], styles['Cell']),
                    Paragraph(course.course_category.course_category_name[:40] if course.course_category else 'Без категории', styles['Cell']),
                    Paragraph(str(course.total_students), styles['CellCenter']),
                    Paragraph(f"{course.avg_rating or 0:.2f}", styles['CellCenter']),
                    Paragraph(course.course_type.course_type_name[:30] if course.course_type else '-', styles['Cell']),
                    Paragraph(str(course.course_hours), styles['CellCenter']),
                ])
        
        table = Table(data, colWidths=col_widths, repeatRows=1)
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


def get_course_statistics_for_export(request, start_date, end_date):
    """Получение статистики курсов для экспорта"""
    my_courses = Course.objects.filter(created_by=request.user)
    course_stats = []
    
    for course in my_courses:
        enrollments = UserCourse.objects.filter(course=course)
        
        if start_date:
            enrollments = enrollments.filter(registration_date__gte=start_date)
        if end_date:
            enrollments = enrollments.filter(registration_date__lte=end_date)
        
        completed = enrollments.filter(status_course=True).count()
        in_progress = enrollments.filter(status_course=False, is_active=True).count()
        total = enrollments.count()
        completion_rate = (completed / total * 100) if total > 0 else 0
        avg_rating = Review.objects.filter(course=course, is_approved=True).aggregate(avg=Avg('rating'))['avg'] or 0
        
        course_stats.append({
            'course': course,
            'total_enrollments': total,
            'completed': completed,
            'in_progress': in_progress,
            'completion_rate': completion_rate,
            'avg_rating': avg_rating,
        })
    
    return course_stats


def get_popular_courses_for_export(request, start_date, end_date):
    """Получение популярных курсов для экспорта"""
    popular_courses = Course.objects.annotate(
        total_students=Count('usercourse', filter=Q(usercourse__is_active=True)),
        avg_rating=Avg('review__rating', filter=Q(review__is_approved=True))
    ).filter(is_active=True).order_by('-total_students')[:50]
    
    return popular_courses