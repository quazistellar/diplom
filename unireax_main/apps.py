import threading
from django.apps import AppConfig
from django.core.management import call_command
from django.db.utils import OperationalError, ProgrammingError
import os

def run_initial_setup():
    """функция, которая запускает первоначальную настройку приложения в фоновом режиме"""
    try:
        from unireax_main.models import User
        if User.objects.count() == 0:
            print(" [команда] запуск первоначальной настройки системы..")
            call_command('inital_setup')
    except (OperationalError, ProgrammingError):
        print("[команда] база данных не готова, пропускаем автоматическую настройку..")
    except Exception as e:
        print(f"[команда] ошибка автоматической настройки: {e}")

class UnireaxMainConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'unireax_main'
    verbose_name = 'Таблицы автоматизированной системы управления образовательными процессами UNIREAX'

    def ready(self):
        """запускается при готовности приложения"""

        try:
            import admin_app.logs_utils
        except ImportError as e:
            print(f"не удалось подключить логирование: {e}")
        
        try:
            import unireax_main.signals
        except ImportError as e:
            print(f"[сигналы] не удалось подключить сигналы: {e}")
        
        if os.environ.get('RUN_MAIN', None) == 'true' or not os.environ.get('RUN_MAIN'):
            thread_setup = threading.Thread(target=run_initial_setup)
            thread_setup.daemon = True
            thread_setup.start()