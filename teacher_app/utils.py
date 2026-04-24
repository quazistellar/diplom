import threading
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class EmailThread(threading.Thread):
    """Поток для асинхронной отправки email"""
    def __init__(self, subject, message, recipient_list, html_message=None):
        self.subject = subject
        self.message = message
        self.recipient_list = recipient_list
        self.html_message = html_message
        threading.Thread.__init__(self)

    def run(self):
        try:
            send_mail(
                self.subject,
                self.message,
                settings.DEFAULT_FROM_EMAIL,
                self.recipient_list,
                html_message=self.html_message,
                fail_silently=False,
            )
            print(f"Email успешно отправлен на {', '.join(self.recipient_list)}")
        except Exception as e:
            print(f"Ошибка при отправке email на {', '.join(self.recipient_list)}: {e}")


def send_new_account_email(user, password, course_name, request):
    """Отправка email новому пользователю с логином и паролем"""
    subject = f'Добро пожаловать на курс "{course_name}" - UNIREAX'
    
    login_url = f"{'https' if request.is_secure() else 'http'}://{request.get_host()}/login/"
    
    try:
        html_message = render_to_string('emails/new_account_email.html', {
            'user': user,
            'password': password,
            'course_name': course_name,
            'login_url': login_url,
        })
        plain_message = strip_tags(html_message)
    except Exception as e:
        print(f"Ошибка при рендеринге HTML шаблона: {e}")
        plain_message = f"""
UNIREAX - Образовательная платформа
================================

Здравствуйте, {user.first_name} {user.last_name}!

🎉 Добро пожаловать! Для вас создан аккаунт на курсе "{course_name}" в системе UNIREAX.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📋 ДАННЫЕ ДЛЯ ВХОДА:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Логин: {user.email}
Пароль: {password}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔗 Ссылка для входа: {login_url}

⚠️ ВАЖНО: Рекомендуем сменить пароль после первого входа в систему.
   Для этого перейдите в личный кабинет и выберите "Смена пароля".

Если у вас возникли вопросы, пожалуйста, свяжитесь с преподавателем курса 
или администратором платформы.

С уважением,
Команда UNIREAX

---
Это письмо отправлено автоматически. Пожалуйста, не отвечайте на него.
© 2026 UNIREAX. Все права защищены.
"""
        html_message = None
    
    EmailThread(subject, plain_message, [user.email], html_message).start()


def send_existing_user_added_to_course_email(user, course_name, request):
    """Отправка email существующему пользователю о добавлении на курс"""
    subject = f'Вас добавили на курс "{course_name}" - UNIREAX'
    
    login_url = f"{'https' if request.is_secure() else 'http'}://{request.get_host()}/login/"
    
    try:
        html_message = render_to_string('emails/existing_user_added_email.html', {
            'user': user,
            'course_name': course_name,
            'login_url': login_url,
        })
        plain_message = strip_tags(html_message)
    except Exception as e:
        print(f"Ошибка при рендеринге HTML шаблона: {e}")
        plain_message = f"""
UNIREAX - Образовательная платформа
================================

Здравствуйте, {user.first_name} {user.last_name}!

📚 Вас добавили на новый курс в системе UNIREAX.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎓 ИНФОРМАЦИЯ О КУРСЕ:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Название: {course_name}
Статус: Доступ открыт
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Вы можете приступить к обучению, используя свои существующие учетные данные.

🔗 Ссылка для входа: {login_url}

💡 Совет: Курс уже доступен в вашем личном кабинете. 
   Перейдите в раздел "Мои курсы", чтобы начать обучение.

📋 Что вас ждет на курсе:
   • Лекции 
   • Практические задания
   • Тесты для проверки знаний
   • Поддержка преподавателей

Если у вас возникли вопросы по курсу, пожалуйста, обратитесь к преподавателю.

С уважением,
Команда UNIREAX

---
Это письмо отправлено автоматически. Пожалуйста, не отвечайте на него.
© 2026 UNIREAX. Все права защищены.
"""
        html_message = None
    
    EmailThread(subject, plain_message, [user.email], html_message).start()


def send_account_credentials_email(user, password, course_name, request):
    """
    Универсальная функция для обратной совместимости.
    Если передан password - отправляем письмо новому пользователю,
    иначе - существующему.
    """
    if password:
        send_new_account_email(user, password, course_name, request)
    else:
        send_existing_user_added_to_course_email(user, course_name, request)


def send_bulk_emails(users_data, course_name, request):
    """Отправка email нескольким пользователям (новым и существующим)"""
    for user, password, is_new in users_data:
        if is_new:
            send_new_account_email(user, password, course_name, request)
        else:
            send_existing_user_added_to_course_email(user, course_name, request)