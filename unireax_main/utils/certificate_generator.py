from io import BytesIO
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
    """регистрация шрифтов Arial Black для сертификата с поддержкой кириллицы"""
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


def wrap_text(canvas, text, font_name, font_size, max_width):
    """Разбивает текст на строки с переносом по словам"""
    canvas.setFont(font_name, font_size)
    words = text.split()
    lines = []
    current = ""

    for word in words:
        test = f"{current} {word}".strip() if current else word
        if canvas.stringWidth(test, font_name, font_size) <= max_width:
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


def calculate_total_course_score(user_id, course_id):
    """
    Рассчитывает общий набранный балл пользователя за курс
    """
    from unireax_main.models import PracticalAssignment, Test, UserPracticalAssignment, TestResult, Feedback
    from django.db.models import Sum
    
    total_earned = 0
    total_max = 0
    
    assignments = PracticalAssignment.objects.filter(
        lecture__course_id=course_id,
        is_active=True,
        grading_type='points'
    )
    
    for assignment in assignments:
        max_score = assignment.max_score or 0
        total_max += max_score
        
        best = UserPracticalAssignment.objects.filter(
            user_id=user_id,
            practical_assignment=assignment
        ).order_by('-attempt_number').first()
        
        if best:
            try:
                fb = Feedback.objects.get(user_practical_assignment=best)
                if fb.score:
                    total_earned += fb.score
            except:
                pass
    
    tests = Test.objects.filter(
        lecture__course_id=course_id,
        is_active=True
    )
    
    final_test_passed_with_honors = False
    
    for test in tests:
        max_score = test.question_set.aggregate(total=Sum('question_score'))['total'] or 0
        total_max += max_score
        
        best = TestResult.objects.filter(
            user_id=user_id,
            test=test
        ).order_by('-final_score').first()
        
        if best and best.final_score:
            total_earned += best.final_score
            
            if test.is_final and max_score > 0:
                if (best.final_score / max_score) * 100 >= 90:
                    final_test_passed_with_honors = True
    
    percentage = (total_earned / total_max * 100) if total_max > 0 else 0
    
    has_final_test = tests.filter(is_final=True).exists()
    
    if has_final_test:
        with_honors = percentage >= 90 and final_test_passed_with_honors
    else:
        with_honors = percentage >= 90
    
    return {
        'total_earned': round(total_earned, 2),
        'total_max': round(total_max, 2),
        'percentage': round(percentage, 2),
        'with_honors': with_honors,
    }


def generate_certificate_pdf(certificate):
    """
    функция генерирует PDF сертификата о прохождении курса (при его наличии)
    """
    cert_dir = os.path.join(settings.MEDIA_ROOT, 'certificates')
    os.makedirs(cert_dir, exist_ok=True)
    
    filename = f"certificate_{certificate.certificate_number}.pdf"
    filepath = os.path.join(cert_dir, filename)
    
    c = canvas.Canvas(filepath, pagesize=A4)
    width, height = A4

    from unireax_main.utils.certificate_generator import calculate_total_course_score
    score_data = calculate_total_course_score(certificate.user_course.user.id, certificate.user_course.course.id)

    purple = HexColor('#7B7FD5')
    dark = HexColor('#2c3e50')
    gray = HexColor('#555555')
    dark_gray = HexColor('#333333')
    dark_red = HexColor('#8B0000') 

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
    y -= 20

    c.setFont(font, 12)
    c.setFillColor(dark_gray)
    c.drawCentredString(width/2, y, f"Набрано баллов: {score_data['total_earned']} из {score_data['total_max']}")
    y -= 20
    c.drawCentredString(width/2, y, f"Процент выполнения: {score_data['percentage']}%")
    y -= 25

    if score_data['with_honors']:
        c.setFont(font, 14)
        c.setFillColor(dark_red)
        c.drawCentredString(width/2, y, "С ОТЛИЧИЕМ!")
        y -= 25
    else:
        y -= 10

    c.setFont(font, 13)
    c.setFillColor(gray)
    c.drawCentredString(width/2, y, f"Дата выдачи: {certificate.issue_date.strftime('%d.%m.%Y')}")
    y -= 25

    c.drawCentredString(width/2, y, f"№ {certificate.certificate_number}")
    y -= 80

    signature_y = y
    signature_path = os.path.join(settings.BASE_DIR, 'static', 'images', 'write.png')
    
    if os.path.exists(signature_path):
        c.drawImage(
            signature_path,
            width/2 - 130,
            signature_y - 17,
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