from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings


def send_password_reset_code(user, code, request=None):
    """
    Отправляет код восстановления пароля на email пользователя
    """
    subject = 'Восстановление пароля - UNIREAX'
    
    context = {
        'user': user,
        'code': code,
        'protocol': 'https' if request and request.is_secure() else 'http',
        'domain': request.get_host() if request else settings.BASE_URL,
    }
    
    html_message = render_to_string('emails/password_reset_code.html', context)
    plain_message = f"""
    Здравствуйте, {user.get_full_name() or user.username}!
    
    Вы запросили восстановление пароля на платформе UNIREAX.
    
    Ваш код для восстановления пароля: {code}
    
    Код действителен в течение 15 минут.
    
    Если вы не запрашивали восстановление пароля, просто проигнорируйте это письмо.
    
    ---
    С уважением, команда UNIREAX
    """
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


def send_password_reset_success_email(user, request=None):
    """
    Отправляет письмо об успешной смене пароля
    """
    subject = 'Пароль успешно изменен - UNIREAX'
    
    context = {
        'user': user,
        'protocol': 'https' if request and request.is_secure() else 'http',
        'domain': request.get_host() if request else settings.BASE_URL,
    }
    
    html_message = render_to_string('emails/password_reset_success.html', context)
    plain_message = f"""
    Здравствуйте, {user.get_full_name() or user.username}!
    
    Ваш пароль на платформе UNIREAX был успешно изменен.
    
    Если вы не меняли пароль, пожалуйста, свяжитесь с поддержкой.
    
    ---
    С уважением, команда UNIREAX
    """
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[user.email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )


def send_teacher_application_result_email(teacher_email, teacher_name, course_name, status, methodist_email, comment=None, request=None, course_id=None):
    """
    Отправляет уведомление преподавателю о результате рассмотрения заявки
    """
    if status == 'approved':
        subject = f'Заявка на курс "{course_name}" одобрена - UNIREAX'
        template = 'emails/teacher_application_approved.html'
        plain_message = f"""
        Здравствуйте, {teacher_name}!
        
        Рады сообщить, что ваша заявка на преподавание курса "{course_name}" была ОДОБРЕНА.
        
        Поздравляем! Вы теперь преподаватель курса "{course_name}".
        
        Что вам доступно теперь:
        - Просмотр списка слушателей курса
        - Проверка практических заданий
        - Просмотр результатов тестов слушателей
        - Выставление оценок и обратная связь
        
        По всем вопросам вы можете обратиться к методисту: {methodist_email}
        
        ---
        С уважением, команда UNIREAX
        """
    else:
        subject = f'Заявка на курс "{course_name}" отклонена - UNIREAX'
        template = 'emails/teacher_application_rejected.html'
        plain_message = f"""
        Здравствуйте, {teacher_name}!
        
        К сожалению, ваша заявка на преподавание курса "{course_name}" была ОТКЛОНЕНА.
        
        {f'Причина: {comment}' if comment else ''}
        
        Вы можете:
        - Подать заявку на другой курс
        - Связаться с методистом для уточнения деталей: {methodist_email}
        
        ---
        С уважением, команда UNIREAX
        """
    
    context = {
        'teacher_name': teacher_name,
        'teacher_email': teacher_email,
        'course_name': course_name,
        'course_id': course_id,
        'comment': comment,
        'methodist_email': methodist_email,
        'protocol': 'https' if request and request.is_secure() else 'http',
        'domain': request.get_host() if request else settings.BASE_URL,
    }
    
    html_message = render_to_string(template, context)
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[teacher_email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[teacher_email],
            fail_silently=False,
        )


def send_new_teacher_application_notification(methodist_email, methodist_name, teacher_name, teacher_email, course_name, application_id, request=None):
    """
    Отправляет уведомление методисту о новой заявке
    """
    subject = f'Новая заявка на преподавание - курс "{course_name}"'
    
    context = {
        'methodist_name': methodist_name,
        'methodist_email': methodist_email,
        'teacher_name': teacher_name,
        'teacher_email': teacher_email,
        'course_name': course_name,
        'application_id': application_id,
        'protocol': 'https' if request and request.is_secure() else 'http',
        'domain': request.get_host() if request else settings.BASE_URL,
    }
    
    html_message = render_to_string('emails/new_teacher_application_notification.html', context)
    plain_message = f"""
    Здравствуйте, {methodist_name}!
    
    Поступила новая заявка на преподавание курса "{course_name}".
    
    Информация о заявке:
    - Преподаватель: {teacher_name}
    - Email преподавателя: {teacher_email}
    - Курс: {course_name}
    
    Для обработки заявки перейдите в панель методиста.
    
    ---
    С уважением, команда UNIREAX
    """
    
    try:
        msg = EmailMultiAlternatives(
            subject=subject,
            body=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[methodist_email]
        )
        msg.attach_alternative(html_message, "text/html")
        msg.send(fail_silently=False)
    except Exception as e:
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[methodist_email],
            fail_silently=False,
        )