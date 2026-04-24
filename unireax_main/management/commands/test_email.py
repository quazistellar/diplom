from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings

class Command(BaseCommand):
    help = 'Test email configuration'

    def handle(self, *args, **options):
        self.stdout.write("=== ТЕСТ EMAIL НАСТРОЕК ===")
        self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        self.stdout.write(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        self.stdout.write(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        self.stdout.write(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        self.stdout.write(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        
        try:
            self.stdout.write("\nПопытка отправки...")
            result = send_mail(
                'Тестовое письмо от Django',
                'Если вы видите это письмо, то настройки почты работают правильно!',
                settings.DEFAULT_FROM_EMAIL,
                [settings.EMAIL_HOST_USER],  # Отправляем на тот же email для проверки
                fail_silently=False,
            )
            self.stdout.write(self.style.SUCCESS(f'✓ Письмо успешно отправлено! Результат: {result}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Ошибка: {e}'))
            import traceback
            traceback.print_exc()