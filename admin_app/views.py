from django.contrib.admin.models import LogEntry
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import render
from django.utils import timezone
from .logs_utils import is_duplicate_log_entry
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils.decorators import method_decorator
from django.http import JsonResponse
from django.views import View
import os
import subprocess
from django.conf import settings
from datetime import datetime
import logging
import glob
import platform
import json
import gzip
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import user_passes_test
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from unireax_main.models import User, Role
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.db.models import Count
from django.utils import timezone
from datetime import timedelta
from unireax_main.models import User, Course, UserCourse
from unireax_main.forms import ProfilePasswordChangeForm, ProfileInfoForm
from django.db.models.functions import TruncDate
from collections import Counter
import json

from django.contrib.admin.models import LogEntry
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.contrib import messages

from unireax_main.models import *  
from .logs_utils import is_duplicate_log_entry
from .forms import (
    CourseCategoryForm, UserCreateForm, UserUpdateForm,
    CourseForm, UserCourseForm, CourseTeacherForm,
    UserFilterForm, CourseFilterForm, UserCourseFilterForm, CourseTeacherFilterForm
)

from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages


def is_admin(user):
    if not user.is_authenticated:
        return False
    return user.is_staff or (hasattr(user, 'is_admin') and user.is_admin)


@user_passes_test(is_admin)
@login_required
def logs_page(request):
    """Страница просмотра логов"""
    if not request.user.is_staff:
        return render(request, '403.html', status=403)
    
    logs_list = LogEntry.objects.all()
    
    logs_list = logs_list.exclude(
        Q(change_message__startswith='[{"added":') |
        Q(change_message__startswith='[{"changed":') |
        Q(change_message__startswith='[{"deleted":') |
        Q(change_message='')
    ).exclude(
        Q(content_type__app_label='sessions') |
        Q(content_type__app_label='admin', content_type__model='logentry')
    )

    action_filter = request.GET.get('action_filter', 'all')
    time_sort = request.GET.get('time_sort', 'newest')
    date_filter = request.GET.get('date_filter', '')

    if action_filter and action_filter != 'all':
        logs_list = logs_list.filter(action_flag=action_filter)

    if time_sort == 'oldest':
        logs_list = logs_list.order_by('action_time')
    else:
        logs_list = logs_list.order_by('-action_time')

    if date_filter:
        try:
            date_obj = timezone.datetime.strptime(date_filter, '%Y-%m-%d').date()
            logs_list = logs_list.filter(action_time__date=date_obj)
        except ValueError:
            pass
    
    paginator = Paginator(logs_list, 15)
    page_number = request.GET.get('page')
    logs = paginator.get_page(page_number)

    params = {
        'action_filter': action_filter if action_filter != 'all' else '',
        'time_sort': time_sort,
        'date_filter': date_filter,
    }

    return render(request, 'logs_page.html', {
        'logs': logs,
        'params': params,
        'action_filter': action_filter,
        'time_sort': time_sort,
        'date_filter': date_filter,
    })


logger = logging.getLogger(__name__)

@method_decorator(login_required, name='dispatch')
@method_decorator(user_passes_test(is_admin), name='dispatch')
class BackupDatabaseView(View):
    def get(self, request):
        """Функция для получения списка существующих бэкапов"""
        backup_dir = self.get_backup_dir()
        backups = []
        
        if os.path.exists(backup_dir):
            backup_files = glob.glob(os.path.join(backup_dir, "*.sql")) + \
                          glob.glob(os.path.join(backup_dir, "*.json")) + \
                          glob.glob(os.path.join(backup_dir, "*.gz"))
            
            for file_path in backup_files:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                file_ext = os.path.splitext(file_name)[1].lower()
                
                backups.append({
                    'name': file_name,
                    'path': file_path,
                    'size': file_size,
                    'time': file_time,
                    'formatted_size': self.format_size(file_size),
                    'formatted_time': file_time.strftime("%d.%m.%Y %H:%M:%S"),
                    'type': self.get_backup_type(file_ext)
                })

        backups.sort(key=lambda x: x['time'], reverse=True)
        
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'backups': backups})
            
        return render(request, 'backup.html', {'backups': backups})

    def post(self, request):
        """Обработка POST запросов через AJAX"""
        action = request.POST.get('action')
        
        if request.headers.get('X-Requested-With') != 'XMLHttpRequest':
            return JsonResponse({
                'status': 'error',
                'message': 'Некорректный тип запроса'
            }, status=400)
        
        if action == 'backup':
            return self.create_backup(request)
        elif action == 'restore':
            backup_file = request.POST.get('backup_file')
            return self.restore_backup(request, backup_file)
        else:
            return JsonResponse({
                'status': 'error',
                'message': 'Неизвестное действие'
            }, status=400)

    def get_backup_dir(self):
        """Автоматическое определение папки для бэкапов в зависимости от ОС"""
        local_dir = os.path.join(settings.BASE_DIR, 'backups')
        
        linux_dirs = [
            local_dir,
            '/var/data/backups',
            '/tmp/backups',
        ]
        
        windows_dirs = [
            local_dir,
            os.path.join(os.environ.get('TEMP', ''), 'backups'),
        ]
        
        system = platform.system().lower()
        if system == 'windows':
            possible_dirs = windows_dirs
        else:
            possible_dirs = linux_dirs
        
        for directory in possible_dirs:
            try:
                os.makedirs(directory, exist_ok=True)
                test_file = os.path.join(directory, 'test.tmp')
                with open(test_file, 'w') as f:
                    f.write('test')
                os.remove(test_file)
                logger.info(f"Using backup directory: {directory}")
                return directory
            except:
                continue
        
        os.makedirs(local_dir, exist_ok=True)
        return local_dir

    def find_postgres_utils(self):
        """Автоматический поиск утилит PostgreSQL для любой ОС"""
        system = platform.system().lower()

        if system == 'windows':
            pg_dump_paths = [
                r"C:\Program Files\PostgreSQL\16\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\15\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\14\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\13\bin\pg_dump.exe",
                r"C:\Program Files\PostgreSQL\12\bin\pg_dump.exe",
                "pg_dump.exe",
            ]
            psql_paths = [
                r"C:\Program Files\PostgreSQL\16\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\15\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\14\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\13\bin\psql.exe",
                r"C:\Program Files\PostgreSQL\12\bin\psql.exe",
                "psql.exe",
            ]
        else:
            pg_dump_paths = [
                '/usr/bin/pg_dump',
                '/usr/local/bin/pg_dump',
                '/bin/pg_dump',
                'pg_dump',
            ]
            psql_paths = [
                '/usr/bin/psql',
                '/usr/local/bin/psql',
                '/bin/psql',
                'psql',
            ]
        
        result = {
            'pg_dump': {'found': False, 'path': None},
            'psql': {'found': False, 'path': None}
        }

        for path in pg_dump_paths:
            try:
                cmd = [path, '--version'] if os.path.exists(path) or path in ['pg_dump', 'pg_dump.exe'] else [path, '--version']
                output = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if output.returncode == 0:
                    result['pg_dump']['found'] = True
                    result['pg_dump']['path'] = path
                    result['pg_dump']['version'] = output.stdout.strip()
                    logger.info(f"Found pg_dump at: {path}")
                    break
            except:
                continue
        
        for path in psql_paths:
            try:
                cmd = [path, '--version'] if os.path.exists(path) or path in ['psql', 'psql.exe'] else [path, '--version']
                output = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if output.returncode == 0:
                    result['psql']['found'] = True
                    result['psql']['path'] = path
                    result['psql']['version'] = output.stdout.strip()
                    logger.info(f"Found psql at: {path}")
                    break
            except:
                continue
        
        return result

    def format_size(self, size_bytes):
        """Форматирование размера файла"""
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} ТБ"

    def get_backup_type(self, extension):
        """Определение типа бэкапа по расширению"""
        if extension == '.sql':
            return 'pg_dump'
        elif extension == '.json':
            return 'dumpdata_json'
        elif extension == '.gz':
            return 'dumpdata_gz'
        else:
            return 'unknown'

    def read_file_safe(self, file_path):
        """Безопасное чтение файла с автоматическим определением кодировки"""
        encodings = ['utf-8', 'cp1251', 'latin-1', 'cp866', 'koi8-r']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                logger.info(f"Successfully read file with {encoding} encoding")
                return content, encoding
            except UnicodeDecodeError:
                continue
            except Exception as e:
                logger.error(f"Error reading file with {encoding}: {e}")
                continue
        
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
        
        return content, 'utf-8 (with ignore)'

    def create_backup(self, request):
        """Создание бэкапа с автоопределением доступных методов"""
        utils = self.find_postgres_utils()
        
        if utils['pg_dump']['found']:
            return self.create_backup_pg_dump(request, utils['pg_dump']['path'])
        else:
            logger.warning("pg_dump not found, using dumpdata as fallback")
            return self.create_backup_dumpdata(request)

    def create_backup_pg_dump(self, request, pg_dump_path):
        """Создание бэкапа через pg_dump"""
        try:
            db_config = settings.DATABASES['default']
            db_name = db_config['NAME']
            
            db_password = os.environ.get('DB_PASSWORD', db_config.get('PASSWORD', ''))
            
            backup_dir = self.get_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_file = f"{db_name}_backup_{timestamp}.sql"
            backup_path = os.path.join(backup_dir, backup_file)

            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password
            
            env['PGCLIENTENCODING'] = 'UTF8'

            command = [
                pg_dump_path,
                '-U', db_config['USER'],
                '-h', db_config.get('HOST', 'localhost'),
                '-p', str(db_config.get('PORT', '5432')),
                '-d', db_config['NAME'],
                '-f', backup_path,
                '-v',
                '--encoding=UTF8'
            ]

            logger.info(f"Starting backup with pg_dump: {backup_file}")
            
            timeout = 300
            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                file_size = os.path.getsize(backup_path)
                backups = self.get_backups_list()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Бэкап базы данных успешно создан',
                    'backup_file': backup_file,
                    'backup_size': self.format_size(file_size),
                    'backup_time': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    'backups': backups,
                    'method': 'pg_dump'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ошибка: файл бэкапа пуст',
                    'details': result.stderr
                }, status=500)
                
        except subprocess.TimeoutExpired:
            return JsonResponse({
                'status': 'error',
                'message': 'Превышено время создания бэкапа'
            }, status=500)
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при создании бэкапа: {str(e)}'
            }, status=500)

    def create_backup_dumpdata(self, request):
        """Запасной метод создания бэкапа через dumpdata"""
        try:
            from django.core.management import call_command
            from io import StringIO
            
            db_config = settings.DATABASES['default']
            db_name = db_config['NAME']
            
            backup_dir = self.get_backup_dir()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            backup_file = f"{db_name}_dumpdata_{timestamp}.json"
            backup_path = os.path.join(backup_dir, backup_file)

            output = StringIO()
            call_command('dumpdata', stdout=output, format='json', indent=2, 
                        natural_foreign=True, natural_primary=True, exclude=['contenttypes'])
            
            with open(backup_path, 'w', encoding='utf-8') as f:
                f.write(output.getvalue())
            
            if os.path.exists(backup_path) and os.path.getsize(backup_path) > 0:
                file_size = os.path.getsize(backup_path)
                backups = self.get_backups_list()
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Бэкап создан (метод dumpdata)',
                    'backup_file': backup_file,
                    'backup_size': self.format_size(file_size),
                    'backup_time': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    'backups': backups,
                    'method': 'dumpdata',
                    'note': 'Использован встроенный метод Django (pg_dump не найден)'
                })
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ошибка при создании бэкапа через dumpdata'
                }, status=500)
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка: {str(e)}'
            }, status=500)

    def restore_backup(self, request, backup_file):
        """Восстановление из бэкапа с автоопределением типа"""
        try:
            backup_dir = self.get_backup_dir()
            backup_path = os.path.join(backup_dir, backup_file)

            if not os.path.exists(backup_path):
                return JsonResponse({
                    'status': 'error',
                    'message': f'Файл бэкапа не найден: {backup_file}'
                }, status=404)

            file_ext = os.path.splitext(backup_file)[1].lower()
            backup_type = self.get_backup_type(file_ext)
            
            if backup_type == 'pg_dump':
                utils = self.find_postgres_utils()
                if utils['psql']['found']:
                    return self.restore_from_sql(request, backup_path, utils['psql']['path'])
                else:
                    return JsonResponse({
                        'status': 'error',
                        'message': 'psql не найден. Невозможно восстановить SQL бэкап.',
                        'suggestion': 'Попробуйте восстановить вручную через pgAdmin'
                    }, status=500)
            
            elif backup_type in ['dumpdata_json', 'dumpdata_gz']:
                return self.restore_from_dumpdata(request, backup_path)
            else:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Неподдерживаемый формат бэкапа'
                }, status=400)
                
        except Exception as e:
            logger.error(f"Restore failed: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при восстановлении: {str(e)}'
            }, status=500)

    def restore_from_sql(self, request, backup_path, psql_path):
        """Восстановление из SQL файла с правильной обработкой кодировки"""
        try:
            db_config = settings.DATABASES['default']
            db_password = os.environ.get('DB_PASSWORD', db_config.get('PASSWORD', ''))

            env = os.environ.copy()
            if db_password:
                env['PGPASSWORD'] = db_password
            
            env['PGCLIENTENCODING'] = 'UTF8'

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            pre_restore_backup = os.path.join(self.get_backup_dir(), f"pre_restore_{timestamp}.sql")
            
            utils = self.find_postgres_utils()
            if utils['pg_dump']['found']:
                try:
                    subprocess.run([
                        utils['pg_dump']['path'],
                        '-U', db_config['USER'],
                        '-h', db_config.get('HOST', 'localhost'),
                        '-d', db_config['NAME'],
                        '-f', pre_restore_backup,
                        '--encoding=UTF8'
                    ], env=env, capture_output=True, timeout=60)
                except:
                    pass

            sql_content, used_encoding = self.read_file_safe(backup_path)
            logger.info(f"Reading backup file with encoding: {used_encoding}")
            modified_content = self.prepare_backup_for_restore(sql_content)
            temp_restore_file = backup_path + ".temp_restore.sql"
            with open(temp_restore_file, 'w', encoding='utf-8') as f:
                f.write(modified_content)

            command = [
                psql_path,
                '-U', db_config['USER'],
                '-h', db_config.get('HOST', 'localhost'),
                '-p', str(db_config.get('PORT', '5432')),
                '-d', db_config['NAME'],
                '-f', temp_restore_file,
                '-v', 'ON_ERROR_STOP=1'
            ]

            result = subprocess.run(
                command,
                env=env,
                capture_output=True,
                text=True,
                timeout=600
            )

            if os.path.exists(temp_restore_file):
                os.remove(temp_restore_file)

            if result.returncode == 0:
                backups = self.get_backups_list()
                return JsonResponse({
                    'status': 'success',
                    'message': 'База данных успешно восстановлена',
                    'backup_file': os.path.basename(backup_path),
                    'restore_time': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                    'backups': backups
                })
            else:
                warning = ''
                if os.path.exists(pre_restore_backup):
                    warning = f'Создан предварительный бэкап: {os.path.basename(pre_restore_backup)}'
                
                return JsonResponse({
                    'status': 'error',
                    'message': 'Ошибка при восстановлении',
                    'details': result.stderr,
                    'warning': warning
                }, status=500)

        except subprocess.TimeoutExpired:
            return JsonResponse({
                'status': 'error',
                'message': 'Превышено время восстановления'
            }, status=500)
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': str(e)
            }, status=500)

    def restore_from_dumpdata(self, request, backup_path):
        """Восстановление из dumpdata JSON с правильной обработкой кодировки"""
        try:
            from django.core.management import call_command
            
            if backup_path.endswith('.gz'):
                with gzip.open(backup_path, 'rt', encoding='utf-8') as f:
                    content = f.read()
                temp_file = backup_path + ".temp.json"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                restore_path = temp_file
            else:
                content, encoding = self.read_file_safe(backup_path)
                temp_file = backup_path + ".temp.json"
                with open(temp_file, 'w', encoding='utf-8') as f:
                    f.write(content)
                restore_path = temp_file

            try:
                json.loads(content)
            except json.JSONDecodeError as e:
                if os.path.exists(temp_file):
                    os.remove(temp_file)
                return JsonResponse({
                    'status': 'error',
                    'message': 'Файл бэкапа поврежден (невалидный JSON)',
                    'details': str(e)
                }, status=500)

            try:
                call_command('loaddata', restore_path, format='json', verbosity=0)
            finally:
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            backups = self.get_backups_list()
            return JsonResponse({
                'status': 'success',
                'message': 'Данные восстановлены из JSON бэкапа',
                'backup_file': os.path.basename(backup_path),
                'restore_time': datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
                'backups': backups,
                'method': 'dumpdata'
            })

        except Exception as e:
            logger.error(f"Restore from dumpdata failed: {e}")
            return JsonResponse({
                'status': 'error',
                'message': f'Ошибка при восстановлении: {str(e)}'
            }, status=500)

    def get_backups_list(self):
        """Получение актуального списка бэкапов"""
        backup_dir = self.get_backup_dir()
        backups = []
        
        if os.path.exists(backup_dir):
            backup_files = glob.glob(os.path.join(backup_dir, "*.sql")) + \
                          glob.glob(os.path.join(backup_dir, "*.json")) + \
                          glob.glob(os.path.join(backup_dir, "*.gz"))
            
            for file_path in backup_files:
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                file_time = datetime.fromtimestamp(os.path.getctime(file_path))
                file_ext = os.path.splitext(file_name)[1].lower()
                
                backups.append({
                    'name': file_name,
                    'path': file_path,
                    'size': file_size,
                    'time': file_time,
                    'formatted_size': self.format_size(file_size),
                    'formatted_time': file_time.strftime("%d.%m.%Y %H:%M:%S"),
                    'type': self.get_backup_type(file_ext)
                })
        
        backups.sort(key=lambda x: x['time'], reverse=True)
        return backups

    def prepare_backup_for_restore(self, backup_content):
        """Подготавливает бэкап для безопасного восстановления"""
        lines = backup_content.split('\n')
        modified_lines = []
        
        i = 0
        while i < len(lines):
            line = lines[i]
            
            if line.strip().startswith('SET ') and any(param in line for param in [
                'statement_timeout', 'lock_timeout', 'idle_in_transaction_session_timeout'
            ]):
                i += 1
                continue
                
            if line.strip().startswith('CREATE TABLE'):
                table_name = self.extract_table_name(line)
                if table_name:
                    modified_lines.append(f'DROP TABLE IF EXISTS {table_name} CASCADE;')
            
            elif line.strip().startswith('CREATE FUNCTION'):
                func_name = self.extract_function_name(line)
                if func_name:
                    modified_lines.append(f'DROP FUNCTION IF EXISTS {func_name} CASCADE;')
            
            elif line.strip().startswith('CREATE PROCEDURE'):
                proc_name = self.extract_procedure_name(line)
                if proc_name:
                    modified_lines.append(f'DROP PROCEDURE IF EXISTS {proc_name} CASCADE;')
            
            elif line.strip().startswith('CREATE VIEW'):
                view_name = self.extract_view_name(line)
                if view_name:
                    modified_lines.append(f'DROP VIEW IF EXISTS {view_name} CASCADE;')
            
            elif line.strip().startswith('CREATE TRIGGER'):
                trigger_info = self.extract_trigger_info(line, lines[i:min(i+10, len(lines))])
                if trigger_info:
                    modified_lines.append(f'DROP TRIGGER IF EXISTS {trigger_info} CASCADE;')
            
            modified_lines.append(line)
            i += 1
        
        return '\n'.join(modified_lines)

    def extract_table_name(self, create_table_line):
        """Извлекает имя таблицы из строки CREATE TABLE"""
        try:
            parts = create_table_line.split()
            if len(parts) >= 3:
                table_name = parts[2].strip()
                if '(' in table_name:
                    table_name = table_name.split('(')[0]
                return table_name
        except:
            pass
        return None

    def extract_function_name(self, create_function_line):
        """Извлекает имя функции из строки CREATE FUNCTION"""
        try:
            parts = create_function_line.split()
            if len(parts) >= 3:
                func_name = parts[2].strip()
                if '(' in func_name:
                    func_name = func_name.split('(')[0]
                return func_name
        except:
            pass
        return None

    def extract_procedure_name(self, create_procedure_line):
        """Извлекает имя процедуры из строки CREATE PROCEDURE"""
        try:
            parts = create_procedure_line.split()
            if len(parts) >= 3:
                proc_name = parts[2].strip()
                if '(' in proc_name:
                    proc_name = proc_name.split('(')[0]
                return proc_name
        except:
            pass
        return None

    def extract_view_name(self, create_view_line):
        """Извлекает имя представления из строки CREATE VIEW"""
        try:
            parts = create_view_line.split()
            if len(parts) >= 3:
                view_name = parts[2].strip()
                return view_name
        except:
            pass
        return None

    def extract_trigger_info(self, create_trigger_line, next_lines):
        """Извлекает информацию о триггере"""
        try:
            parts = create_trigger_line.split()
            if len(parts) >= 4:
                trigger_name = parts[2].strip()
                full_text = ' '.join([create_trigger_line] + next_lines[:5])
                if 'ON' in full_text:
                    on_index = full_text.index('ON')
                    table_part = full_text[on_index:].split()[1]
                    table_name = table_part.strip()
                    if '.' in table_name:
                        return f'{trigger_name} ON {table_name}'
                    else:
                        return f'{trigger_name} ON public.{table_name}'
        except:
            pass
        return None
    

def is_admin(user):
    return user.is_authenticated and hasattr(user, 'is_admin') and user.is_admin

@login_required
@user_passes_test(is_admin)
def dashboard(request):
    context = {
        'title': 'Панель управления',
        'icon': 'fas fa-tachometer-alt',
        'total_users': User.objects.count(),
        'total_courses': Course.objects.count(),
        'total_categories': CourseCategory.objects.count(),
        'total_enrollments': UserCourse.objects.count(),
        'active_courses': Course.objects.filter(is_active=True).count(),
        'active_users': User.objects.filter(is_active=True).count(),
    }
    return render(request, 'dashboard.html', context)


@login_required
@user_passes_test(is_admin)
def category_list(request):
    categories = CourseCategory.objects.all().order_by('-id')
    
    search = request.GET.get('search')
    if search:
        categories = categories.filter(course_category_name__icontains=search)
    
    paginator = Paginator(categories, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Категории курсов',
        'icon': 'fas fa-folder',
        'categories': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
    }
    return render(request, 'categories/category_list.html', context)


@login_required
@user_passes_test(is_admin)
def category_create(request):
    if request.method == 'POST':
        form = CourseCategoryForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория успешно создана')
            return redirect('admin_app:category_list')
    else:
        form = CourseCategoryForm()
    
    context = {
        'title': 'Создание категории',
        'icon': 'fas fa-plus-circle',
        'form': form,
    }
    return render(request, 'categories/category_form.html', context)


@login_required
@user_passes_test(is_admin)
def category_detail(request, pk):
    category = get_object_or_404(CourseCategory, pk=pk)
    courses = Course.objects.filter(course_category=category)[:10]
    
    context = {
        'title': category.course_category_name,
        'icon': 'fas fa-folder',
        'category': category,
        'courses': courses,
    }
    return render(request, 'categories/category_detail.html', context)


@login_required
@user_passes_test(is_admin)
def category_edit(request, pk):
    category = get_object_or_404(CourseCategory, pk=pk)
    
    if request.method == 'POST':
        form = CourseCategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, 'Категория успешно обновлена')
            return redirect('admin_app:category_detail', pk=category.pk)
    else:
        form = CourseCategoryForm(instance=category)
    
    context = {
        'title': f'Редактирование: {category.course_category_name}',
        'icon': 'fas fa-edit',
        'form': form,
        'category': category,
    }
    return render(request, 'categories/category_form.html', context)


@login_required
@user_passes_test(is_admin)
def category_delete(request, pk):
    category = get_object_or_404(CourseCategory, pk=pk)
    
    if request.method == 'POST':
        category.delete()
        messages.success(request, 'Категория успешно удалена')
        return redirect('admin_app:category_list')
    
    context = {
        'title': f'Удаление: {category.course_category_name}',
        'icon': 'fas fa-trash',
        'object': category,
    }
    return render(request, 'categories/category_delete.html', context)


@login_required
@user_passes_test(is_admin)
def user_list(request):
    users = User.objects.all().order_by('-date_joined').select_related('role')
    
    filter_form = UserFilterForm(request.GET)
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        role = filter_form.cleaned_data.get('role')
        is_active = filter_form.cleaned_data.get('is_active')
        is_verified = filter_form.cleaned_data.get('is_verified')
        
        if search:
            users = users.filter(
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search)
            )
        
        if role:
            users = users.filter(role=role)
        
        if is_active:
            users = users.filter(is_active=(is_active == 'true'))
        
        if is_verified:
            users = users.filter(is_verified=(is_verified == 'true'))
    
    paginator = Paginator(users, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Пользователи',
        'icon': 'fas fa-users',
        'users': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'filter_form': filter_form,
    }
    return render(request, 'users/user_list.html', context)


@login_required
@user_passes_test(is_admin)
def user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, 'Пользователь успешно создан')
            return redirect('admin_app:user_list')
    else:
        form = UserCreateForm()
    
    context = {
        'title': 'Создание пользователя',
        'icon': 'fas fa-user-plus',
        'form': form,
    }
    return render(request, 'users/user_form.html', context)


@login_required
@user_passes_test(is_admin)
def user_detail(request, pk):
    user = get_object_or_404(User, pk=pk)
    enrolled_courses = UserCourse.objects.filter(user=user).select_related('course')[:10]
    teaching_courses = CourseTeacher.objects.filter(teacher=user).select_related('course')[:10]
    
    context = {
        'title': user.get_full_name() or user.username,
        'icon': 'fas fa-user',
        'user_obj': user,
        'enrolled_courses': enrolled_courses,
        'teaching_courses': teaching_courses,
    }
    return render(request, 'users/user_detail.html', context)


@login_required
@user_passes_test(is_admin)
def user_edit(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        form = UserUpdateForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Пользователь успешно обновлён')
            return redirect('admin_app:user_detail', pk=user.pk)
    else:
        form = UserUpdateForm(instance=user)
    
    context = {
        'title': f'Редактирование: {user.get_full_name() or user.username}',
        'icon': 'fas fa-user-edit',
        'form': form,
        'user_obj': user,
    }
    return render(request, 'users/user_form.html', context)


@login_required
@user_passes_test(is_admin)
def user_delete(request, pk):
    user = get_object_or_404(User, pk=pk)
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'Пользователь {username} успешно удалён')
        return redirect('admin_app:user_list')
    
    context = {
        'title': f'Удаление: {user.get_full_name() or user.username}',
        'icon': 'fas fa-user-minus',
        'object': user,
    }
    return render(request, 'users/user_delete.html', context)


@login_required
@user_passes_test(is_admin)
def course_list(request):
    courses = Course.objects.all().order_by('-created_at').select_related('course_category', 'course_type', 'created_by')
    
    filter_form = CourseFilterForm(request.GET)
    if filter_form.is_valid():
        search = filter_form.cleaned_data.get('search')
        category = filter_form.cleaned_data.get('course_category')
        course_type = filter_form.cleaned_data.get('course_type')
        is_active = filter_form.cleaned_data.get('is_active')
        has_certificate = filter_form.cleaned_data.get('has_certificate')
        
        if search:
            courses = courses.filter(course_name__icontains=search)
        
        if category:
            courses = courses.filter(course_category=category)
        
        if course_type:
            courses = courses.filter(course_type=course_type)
        
        if is_active:
            courses = courses.filter(is_active=(is_active == 'true'))
        
        if has_certificate:
            courses = courses.filter(has_certificate=(has_certificate == 'true'))
    
    paginator = Paginator(courses, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Курсы',
        'icon': 'fas fa-book',
        'courses': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'filter_form': filter_form,
    }
    return render(request, 'courses/course_list.html', context)


@login_required
@user_passes_test(is_admin)
def course_create(request):
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES)
        if form.is_valid():
            course = form.save()
            messages.success(request, 'Курс успешно создан')
            return redirect('admin_app:course_detail', pk=course.pk)
    else:
        form = CourseForm()
    
    context = {
        'title': 'Создание курса',
        'icon': 'fas fa-plus-circle',
        'form': form,
    }
    return render(request, 'courses/course_form.html', context)


@login_required
@user_passes_test(is_admin)
def course_detail(request, pk):
    course = get_object_or_404(Course, pk=pk)
    enrolled_users = UserCourse.objects.filter(course=course).select_related('user')[:10]
    teachers = CourseTeacher.objects.filter(course=course).select_related('teacher')[:10]
    enrolled_count = UserCourse.objects.filter(course=course).count()
    teachers_count = CourseTeacher.objects.filter(course=course).count()
    
    context = {
        'title': course.course_name,
        'icon': 'fas fa-book-open',
        'course': course,
        'enrolled_users': enrolled_users,
        'teachers': teachers,
        'enrolled_count': enrolled_count,
        'teachers_count': teachers_count,
    }
    return render(request, 'courses/course_detail.html', context)


@login_required
@user_passes_test(is_admin)
def course_edit(request, pk):
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Курс успешно обновлён')
            return redirect('admin_app:course_detail', pk=course.pk)
    else:
        form = CourseForm(instance=course)
    
    context = {
        'title': f'Редактирование: {course.course_name}',
        'icon': 'fas fa-edit',
        'form': form,
        'course': course,
    }
    return render(request, 'courses/course_form.html', context)


@login_required
@user_passes_test(is_admin)
def course_delete(request, pk):
    course = get_object_or_404(Course, pk=pk)
    
    if request.method == 'POST':
        course_name = course.course_name
        course.delete()
        messages.success(request, f'Курс "{course_name}" успешно удалён')
        return redirect('admin_app:course_list')
    
    context = {
        'title': f'Удаление: {course.course_name}',
        'icon': 'fas fa-trash',
        'object': course,
    }
    return render(request, 'courses/course_delete.html', context)

@login_required
@user_passes_test(is_admin)
def user_course_list(request):
    user_courses = UserCourse.objects.all().order_by('-enrolled_at').select_related('user', 'course')
    
    filter_form = UserCourseFilterForm(request.GET)
    if filter_form.is_valid():
        user = filter_form.cleaned_data.get('user')
        course = filter_form.cleaned_data.get('course')
        status_course = filter_form.cleaned_data.get('status_course')
        is_active = filter_form.cleaned_data.get('is_active')
        
        if user:
            user_courses = user_courses.filter(user=user)
        
        if course:
            user_courses = user_courses.filter(course=course)
        
        if status_course:
            user_courses = user_courses.filter(status_course=(status_course == 'true'))
        
        if is_active:
            user_courses = user_courses.filter(is_active=(is_active == 'true'))
    
    paginator = Paginator(user_courses, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Записи на курсы',
        'icon': 'fas fa-user-graduate',
        'user_courses': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'filter_form': filter_form,
    }
    return render(request, 'user_courses/usercourse_list.html', context)


@login_required
@user_passes_test(is_admin)
def user_course_create(request):
    if request.method == 'POST':
        form = UserCourseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Запись на курс успешно создана')
            return redirect('admin_app:user_course_list')
    else:
        initial = {}
        if 'user' in request.GET:
            initial['user'] = request.GET.get('user')
        if 'course' in request.GET:
            initial['course'] = request.GET.get('course')
        form = UserCourseForm(initial=initial)
    
    context = {
        'title': 'Создание записи на курс',
        'icon': 'fas fa-plus-circle',
        'form': form,
    }
    return render(request, 'user_courses/usercourse_form.html', context)


@login_required
@user_passes_test(is_admin)
def user_course_detail(request, pk):
    user_course = get_object_or_404(UserCourse, pk=pk)
    
    context = {
        'title': f'Запись #{user_course.pk}',
        'icon': 'fas fa-user-graduate',
        'user_course': user_course,
    }
    return render(request, 'user_courses/usercourse_detail.html', context)


@login_required
@user_passes_test(is_admin)
def user_course_edit(request, pk):
    user_course = get_object_or_404(UserCourse, pk=pk)
    
    if request.method == 'POST':
        form = UserCourseForm(request.POST, instance=user_course)
        if form.is_valid():
            form.save()
            messages.success(request, 'Запись на курс успешно обновлена')
            return redirect('admin_app:user_course_detail', pk=user_course.pk)
    else:
        form = UserCourseForm(instance=user_course)
    
    context = {
        'title': f'Редактирование записи #{user_course.pk}',
        'icon': 'fas fa-edit',
        'form': form,
        'user_course': user_course,
    }
    return render(request, 'user_courses/usercourse_form.html', context)


@login_required
@user_passes_test(is_admin)
def user_course_delete(request, pk):
    user_course = get_object_or_404(UserCourse, pk=pk)
    
    if request.method == 'POST':
        user_course.delete()
        messages.success(request, 'Запись на курс успешно удалена')
        return redirect('admin_app:user_course_list')
    
    context = {
        'title': f'Удаление записи #{user_course.pk}',
        'icon': 'fas fa-trash',
        'object': user_course,
    }
    return render(request, 'user_courses/usercourse_delete.html', context)


@login_required
@user_passes_test(is_admin)
def course_teacher_list(request):
    course_teachers = CourseTeacher.objects.all().order_by('-id').select_related('course', 'teacher')
    
    filter_form = CourseTeacherFilterForm(request.GET)
    if filter_form.is_valid():
        course = filter_form.cleaned_data.get('course')
        teacher = filter_form.cleaned_data.get('teacher')
        is_active = filter_form.cleaned_data.get('is_active')
        
        if course:
            course_teachers = course_teachers.filter(course=course)
        
        if teacher:
            course_teachers = course_teachers.filter(teacher=teacher)
        
        if is_active:
            course_teachers = course_teachers.filter(is_active=(is_active == 'true'))
    
    paginator = Paginator(course_teachers, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'title': 'Преподаватели курсов',
        'icon': 'fas fa-chalkboard-teacher',
        'course_teachers': page_obj,
        'page_obj': page_obj,
        'is_paginated': paginator.num_pages > 1,
        'filter_form': filter_form,
    }
    return render(request, 'course_teachers/courseteacher_list.html', context)


@login_required
@user_passes_test(is_admin)
def course_teacher_create(request):
    if request.method == 'POST':
        form = CourseTeacherForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Преподаватель успешно назначен на курс')
            return redirect('admin_app:course_teacher_list')
    else:
        initial = {}
        if 'course' in request.GET:
            initial['course'] = request.GET.get('course')
        if 'teacher' in request.GET:
            initial['teacher'] = request.GET.get('teacher')
        form = CourseTeacherForm(initial=initial)
    
    context = {
        'title': 'Назначение преподавателя на курс',
        'icon': 'fas fa-plus-circle',
        'form': form,
    }
    return render(request, 'course_teachers/courseteacher_form.html', context)


@login_required
@user_passes_test(is_admin)
def course_teacher_detail(request, pk):
    course_teacher = get_object_or_404(CourseTeacher, pk=pk)
    
    context = {
        'title': f'Назначение #{course_teacher.pk}',
        'icon': 'fas fa-chalkboard-teacher',
        'course_teacher': course_teacher,
    }
    return render(request, 'course_teachers/courseteacher_detail.html', context)


@login_required
@user_passes_test(is_admin)
def course_teacher_edit(request, pk):
    course_teacher = get_object_or_404(CourseTeacher, pk=pk)
    
    if request.method == 'POST':
        form = CourseTeacherForm(request.POST, instance=course_teacher)
        if form.is_valid():
            form.save()
            messages.success(request, 'Назначение преподавателя успешно обновлено')
            return redirect('admin_app:course_teacher_detail', pk=course_teacher.pk)
    else:
        form = CourseTeacherForm(instance=course_teacher)
    
    context = {
        'title': f'Редактирование назначения #{course_teacher.pk}',
        'icon': 'fas fa-edit',
        'form': form,
        'course_teacher': course_teacher,
    }
    return render(request, 'course_teachers/courseteacher_form.html', context)


@login_required
@user_passes_test(is_admin)
def course_teacher_delete(request, pk):
    course_teacher = get_object_or_404(CourseTeacher, pk=pk)
    
    if request.method == 'POST':
        course_teacher.delete()
        messages.success(request, 'Назначение преподавателя успешно удалено')
        return redirect('admin_app:course_teacher_list')
    
    context = {
        'title': f'Удаление назначения #{course_teacher.pk}',
        'icon': 'fas fa-trash',
        'object': course_teacher,
    }
    return render(request, 'course_teachers/courseteacher_delete.html', context)


@login_required
@user_passes_test(is_admin)
def admin_profile_view(request):
    """Страница профиля администратора с аналитикой"""
    
    user = request.user

    if request.method == 'POST' and 'update_profile' in request.POST:
        form = ProfileInfoForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Личная информация успешно обновлена!')
            return redirect('admin_app:admin_profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label}: {error}')
    else:
        form = ProfileInfoForm(instance=user)

    password_form = ProfilePasswordChangeForm(user)
    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = ProfilePasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменен!')
            return redirect('admin_app:admin_profile')
        else:
            for field, errors in password_form.errors.items():
                for error in errors:
                    messages.error(request, error)
    
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    total_courses = Course.objects.count()
    active_courses = Course.objects.filter(is_active=True).count()
    total_enrollments = UserCourse.objects.count()
    completed_enrollments = UserCourse.objects.filter(status_course=True).count()
    completion_rate = (completed_enrollments / total_enrollments * 100) if total_enrollments > 0 else 0
    
    analytics = {
        'total_users': total_users,
        'active_users': active_users,
        'total_courses': total_courses,
        'active_courses': active_courses,
        'total_enrollments': total_enrollments,
        'completed_enrollments': completed_enrollments,
        'completion_rate': completion_rate,
    }
    
    role_names = []
    for u in User.objects.filter(role__isnull=False):
        if u.role:
            role_names.append(u.role.role_name)
    role_counts = Counter(role_names)
    total_with_roles = sum(role_counts.values())
    role_distribution = []
    for name, count in role_counts.items():
        role_distribution.append({
            'name': name,
            'count': count,
        })
    
    last_30_days = timezone.now() - timedelta(days=30)
    daily_activity = UserCourse.objects.filter(
        enrolled_at__gte=last_30_days
    ).annotate(
        date=TruncDate('enrolled_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    activity_labels = [item['date'].strftime('%d.%m') for item in daily_activity]
    activity_data = [item['count'] for item in daily_activity]
    
    last_7_days = timezone.now() - timedelta(days=7)
    
    users_with_login = User.objects.filter(
        last_login__gte=last_7_days,
        last_login__isnull=False
    )
    
    all_dates = []
    for i in range(6, -1, -1):
        date = (timezone.now() - timedelta(days=i)).date()
        all_dates.append(date)
    
    login_dict = {}
    for user_login in users_with_login:
        login_date = user_login.last_login.date()
        if login_date >= all_dates[0] and login_date <= all_dates[-1]:
            login_dict[login_date] = login_dict.get(login_date, 0) + 1
    
    login_labels = []
    login_data = []
    for date in all_dates:
        login_labels.append(date.strftime('%d.%m'))
        login_data.append(login_dict.get(date, 0))
    
    popular_courses = Course.objects.annotate(
        enrollment_count=Count('usercourse')
    ).order_by('-enrollment_count')[:5].values('course_name', 'enrollment_count')
    
    registrations = User.objects.filter(
        date_joined__gte=last_7_days
    ).annotate(
        date=TruncDate('date_joined')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    reg_dict = {r['date']: r['count'] for r in registrations}
    
    registration_list = []
    for date in all_dates:
        count = reg_dict.get(date, 0)
        registration_list.append({
            'date': date,
            'count': count,
        })
    
    context = {
        'user': user,
        'full_name': user.get_full_name() or user.username,
        'role_name': user.role.role_name if user.role else 'Администратор',
        'date_joined': user.date_joined.strftime('%d.%m.%Y'),
        'is_verified': user.is_verified,
        'form': form,  
        'password_form': password_form, 
        'analytics': analytics,
        'role_distribution': role_distribution,
        'activity_labels': json.dumps(activity_labels),
        'activity_data': json.dumps(activity_data),
        'login_labels': json.dumps(login_labels),
        'login_data': json.dumps(login_data),
        'popular_courses': list(popular_courses),
        'registrations': registration_list,
    }
    
    return render(request, 'admin_profile.html', context)



@user_passes_test(is_admin)
def admin_user_verification_list(request):
    """Список пользователей для подтверждения"""
    
    metodist_role = Role.objects.filter(role_name="методист").first()
    teacher_role = Role.objects.filter(role_name="преподаватель").first()
    
    if not metodist_role:
        metodist_role = Role.objects.create(role_name="методист")
    if not teacher_role:
        teacher_role = Role.objects.create(role_name="преподаватель")
    
    users = User.objects.filter(
        Q(role=metodist_role) | Q(role=teacher_role)
    ).select_related('role').order_by('-date_joined')
    
    status_filter = request.GET.get('status_filter', '')
    if status_filter == 'verified':
        users = users.filter(is_verified=True)
    elif status_filter == 'not_verified':
        users = users.filter(is_verified=False)
    
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(patronymic__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(position__icontains=search_query) |
            Q(educational_institution__icontains=search_query)
        )
    
    role_filter = request.GET.get('role_filter', '')
    if role_filter == 'metodist':
        users = users.filter(role=metodist_role)
    elif role_filter == 'teacher':
        users = users.filter(role=teacher_role)
    
    paginator = Paginator(users, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'users': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'role_filter': role_filter,
    }
    
    return render(request, 'admin_user_verification_list.html', context)

@user_passes_test(is_admin)
def admin_user_verification_detail(request, user_id):
    """Детальная информация о пользователе"""
    
    user = get_object_or_404(User, id=user_id)
    
    metodist_role = Role.objects.filter(role_name="методист").first()
    teacher_role = Role.objects.filter(role_name="преподаватель").first()
    
    if user.role not in [metodist_role, teacher_role]:
        messages.error(request, 'У пользователя неподходящая роль для подтверждения')
        return redirect('admin_app:admin_user_verification_list')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '').strip()
        
        if action == 'approve':
            user.is_verified = True
            user.save()
            
            email_sent = send_account_approved_email(user, comment)
            
            if email_sent:
                messages.success(request, f'Аккаунт пользователя {user.get_full_name()} подтвержден. Уведомление отправлено на почту.')
            else:
                messages.warning(request, f'Аккаунт пользователя {user.get_full_name()} подтвержден, но не удалось отправить уведомление на почту.')
            
        elif action == 'reject':
            user.is_verified = False
            user.save()
            
            email_sent = send_account_rejected_email(user, comment)
            
            if email_sent:
                messages.success(request, f'Аккаунт пользователя {user.get_full_name()} отклонен. Уведомление отправлено на почту.')
            else:
                messages.warning(request, f'Аккаунт пользователя {user.get_full_name()} отклонен, но не удалось отправить уведомление на почту.')
        
        return redirect('admin_app:admin_user_verification_list')
    
    context = {
        'user_obj': user,
    }
    
    return render(request, 'admin_user_verification_detail.html', context)

def send_account_approved_email(user, comment=None):
    """
    Отправка письма о подтверждении аккаунта 
    
    Args:
        user: объект пользователя
        comment: комментарий администратора (необязательно)
    
    Returns:
        bool: True если письмо отправлено успешно, иначе False
    """
    try:
        if not user.email:
            print(f"Ошибка: у пользователя {user.id} нет email")
            return False
        
        subject = 'Ваш аккаунт на UNIREAX подтвержден!'
        
        login_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'
        login_url = f"{login_url}"
        
        html_message = None
        try:
            html_message = render_to_string('account_approved.html', {
                'user_obj': user,
                'admin_comment': comment,
                'site_url': login_url,
            })
        except Exception as e:
            print(f"HTML шаблон не найден, отправляем только текстовое письмо: {e}")
        
        text_message = f"""
Здравствуйте, {user.last_name} {user.first_name}!

Ваш аккаунт на платформе UNIREAX подтвержден администрацией.

Ваша роль: {user.role.role_name}
Email для входа: {user.email}

{f'Комментарий администратора: {comment}' if comment else ''}

Для входа в систему перейдите по ссылке: {login_url}

С уважением,
Команда UNIREAX
"""
        
        result = send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=html_message
        )
        
        print(f"Письмо подтверждения отправлено на {user.email}. Результат: {result}")
        return result > 0
        
    except Exception as e:
        print(f"Ошибка при отправке письма о подтверждении: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_account_rejected_email(user, comment=None):
    """
    Отправка письма об отказе в регистрации (синхронная версия)
    
    Args:
        user: объект пользователя
        comment: комментарий администратора с причиной отказа (необязательно)
    
    Returns:
        bool: True если письмо отправлено успешно, иначе False
    """
    try:
        if not user.email:
            print(f"Ошибка: у пользователя {user.id} нет email")
            return False
        
        subject = 'Решение по вашей регистрации на UNIREAX'
        
        register_url = settings.SITE_URL if hasattr(settings, 'SITE_URL') else 'http://127.0.0.1:8000'
        register_url = f"{register_url}/auth/register/"
        
        html_message = None
        try:
            html_message = render_to_string('account_rejected.html', {
                'user_obj': user,
                'admin_comment': comment,
                'site_url': register_url,
            })
        except Exception as e:
            print(f"HTML шаблон не найден, отправляем только текстовое письмо: {e}")
        
        text_message = f"""
Здравствуйте, {user.last_name} {user.first_name}!

К сожалению, ваша регистрация на платформе UNIREAX не была подтверждена администрацией.

Запрошенная роль: {user.role.role_name}

{f'Причина отказа: {comment}' if comment else 'Для уточнения причины отказа, пожалуйста, свяжитесь с нашей поддержкой.'}

Вы можете повторно подать заявку на регистрацию после устранения указанных замечаний.

Контактная информация службы поддержки:
Email: unireax@mail.ru
Телефон: 8-875-385-81-54 или 8-834-321-77-89

С уважением,
Команда UNIREAX
"""
        
        result = send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=html_message
        )
        
        print(f"Письмо отказа отправлено на {user.email}. Результат: {result}")
        return result > 0
        
    except Exception as e:
        print(f"Ошибка при отправке письма об отказе: {e}")
        import traceback
        traceback.print_exc()
        return False


def send_user_verification_email(user, is_approved, comment=None):
    """
    Универсальная функция для отправки уведомления о результате проверки
    
    Args:
        user: объект пользователя
        is_approved: bool - одобрена ли регистрация
        comment: комментарий администратора (необязательно)
    
    Returns:
        bool: True если письмо отправлено успешно, иначе False
    """
    if is_approved:
        return send_account_approved_email(user, comment)
    else:
        return send_account_rejected_email(user, comment)