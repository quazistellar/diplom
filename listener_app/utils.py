import os
import random
import string
from django.conf import settings
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


def register_certificate_fonts():
    """Регистрация шрифтов Arial Black для сертификата"""
    fonts_loaded = False
    
    font_paths = [
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial_black.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'Arial Black.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial-black.ttf'),
        os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf'),
        '/usr/share/fonts/truetype/msttcorefonts/arialbd.ttf',
        '/Windows/Fonts/arialbd.ttf',
        'C:/Windows/Fonts/arialbd.ttf',
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                pdfmetrics.registerFont(TTFont('Arial-Black', font_path))
                fonts_loaded = True
                break
            except Exception:
                continue
    
    if not fonts_loaded:
        try:
            pdfmetrics.registerFont(TTFont('Arial-Black', 'arialbd'))
            fonts_loaded = True
        except:
            pass
    
    return fonts_loaded


CERTIFICATE_FONTS_LOADED = register_certificate_fonts()


def get_certificate_font():
    """Получение имени шрифта для сертификата"""
    font_names = pdfmetrics.getRegisteredFontNames()
    
    if 'Arial-Black' in font_names:
        return 'Arial-Black'
    elif 'Arial-Bold' in font_names:
        return 'Arial-Bold'
    elif 'Arial' in font_names:
        return 'Arial'
    else:
        return 'Helvetica-Bold'


def wrap_text(canvas_obj, text, font_name, font_size, max_width):
    """Разбивает текст на строки с переносом по словам"""
    canvas_obj.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip() if current else word
        if canvas_obj.stringWidth(test, font_name, font_size) <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def generate_certificate_number():
    """Генерирует уникальный номер сертификата"""
    timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
    random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"CERT-{timestamp}-{random_str}"


def generate_certificate_pdf(certificate):
    """Генерирует PDF сертификата"""
    cert_dir = os.path.join(settings.MEDIA_ROOT, 'certificates')
    os.makedirs(cert_dir, exist_ok=True)
    
    filename = f"certificate_{certificate.certificate_number}.pdf"
    filepath = os.path.join(cert_dir, filename)
    
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    purple = HexColor('#7B7FD5')
    dark = HexColor('#2c3e50')
    gray = HexColor('#555555')

    font = get_certificate_font()

    c.setFillColor(colors.white)
    c.rect(0, 0, width, height, fill=1, stroke=0)
    
    c.setStrokeColor(purple)
    c.setLineWidth(3)
    c.rect(30, 30, width-60, height-60, stroke=1, fill=0)

    y = height - 110

    c.setFont(font, 40)
    c.setFillColor(purple)
    c.drawCentredString(width/2, y, "UNIREAX")
    y -= 65

    c.setFont(font, 32)
    c.setFillColor(dark)
    c.drawCentredString(width/2, y, "СЕРТИФИКАТ")
    y -= 80

    c.setFont(font, 16)
    c.setFillColor(gray)
    c.drawCentredString(width/2, y, "Настоящим удостоверяется, что")
    y -= 70

    user = certificate.user_course.user
    full_name = f"{user.last_name.upper()} {user.first_name.upper()}"
    if user.patronymic:
        full_name += f" {user.patronymic.upper()}"

    c.setFont(font, 32)
    c.setFillColor(purple)
    name_lines = wrap_text(c, full_name, font, 32, width - 120)
    for line in name_lines:
        c.drawCentredString(width/2, y, line)
        y -= 40
    y -= 35

    c.setFont(font, 16)
    c.setFillColor(gray)
    c.drawCentredString(width/2, y, "успешно завершил(а) курс")
    y -= 55

    course_name = certificate.user_course.course.course_name.upper()
    c.setFont(font, 24)
    c.setFillColor(dark)
    course_lines = wrap_text(c, course_name, font, 24, width - 100)
    for line in course_lines:
        c.drawCentredString(width/2, y, line)
        y -= 38
    y -= 30

    c.setFont(font, 13)
    c.setFillColor(gray)
    c.drawCentredString(width/2, y, f"Продолжительность: {certificate.user_course.course.course_hours} часов")
    y -= 28

    c.drawCentredString(width/2, y, f"Дата выдачи: {certificate.issue_date.strftime('%d.%m.%Y')}")
    y -= 28

    c.drawCentredString(width/2, y, f"№ {certificate.certificate_number}")
    y -= 80
    signature_y = y

    signature_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'write.png')
    if os.path.exists(signature_path):
        c.drawImage(
            signature_path,
            width/2 - 130,
            signature_y + 1,
            width=260,
            height=80,
            preserveAspectRatio=True,
            mask='auto'
        )
        line_y = signature_y + 8
        c.setStrokeColor(HexColor('#333333'))
        c.setLineWidth(1.2)
        c.line(width/2 - 130, line_y, width/2 + 130, line_y)
    else:
        line_y = signature_y + 25
        c.setStrokeColor(HexColor('#333333'))
        c.setLineWidth(1.2)
        c.line(width/2 - 130, line_y, width/2 + 130, line_y)

    c.setFont(font, 16)
    c.setFillColor(HexColor('#333333'))
    c.drawCentredString(width/2, signature_y - 28, "Директор UNIREAX")

    c.save()
    
    return f'certificates/{filename}'


def calculate_course_progress(user_id, course_id):
    """Расчет прогресса прохождения курса для пользователя"""
    from unireax_main.models import (
        Lecture, PracticalAssignment, Test, 
        UserPracticalAssignment, TestResult
    )
    
    try:
        lectures_count = Lecture.objects.filter(
            course_id=course_id,
            is_active=True
        ).count()
        
        assignments_count = PracticalAssignment.objects.filter(
            lecture__course_id=course_id,
            is_active=True
        ).count()
        
        tests_count = Test.objects.filter(
            lecture__course_id=course_id,
            is_active=True
        ).count()
        
        total_items = lectures_count + assignments_count + tests_count
        
        if total_items == 0:
            return 0.0
        
        completed_assignments = UserPracticalAssignment.objects.filter(
            user_id=user_id,
            practical_assignment__lecture__course_id=course_id,
            submission_status__assignment_status_name='завершен'
        ).values('practical_assignment').distinct().count()
        
        passed_tests = TestResult.objects.filter(
            user_id=user_id,
            test__lecture__course_id=course_id,
            is_passed=True
        ).values('test').distinct().count()
        
        completed_items = completed_assignments + passed_tests
        
        progress = (completed_items / total_items) * 100
        return round(progress, 2)
        
    except Exception:
        return 0.0


def get_favorite_courses(request):
    """Получение списка ID избранных курсов из cookies"""
    favorite_courses = request.COOKIES.get('favorite_courses', '')
    if favorite_courses:
        return [int(course_id) for course_id in favorite_courses.split(',') if course_id]
    return []


def set_favorite_cookies(response, favorite_ids):
    """Установка cookies с избранными курсами"""
    response.set_cookie('favorite_courses', ','.join(map(str, favorite_ids)), max_age=31536000)
    return response