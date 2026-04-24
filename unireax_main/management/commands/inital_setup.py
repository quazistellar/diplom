import re
from django.core.management.base import BaseCommand
from django.db import connection, transaction
from django.db.utils import OperationalError, ProgrammingError
from django.conf import settings

try:
    from unireax_main.models import User, Role
except ImportError:
    from django.contrib.auth.models import User
    Role = None
try:
    from unireax_main.models import CourseCategory, CourseType, AssignmentStatus, AnswerType
    MODELS_AVAILABLE = True
except ImportError:
    MODELS_AVAILABLE = False
    CourseCategory = None
    CourseType = None
    AssignmentStatus = None
    AnswerType = None

class Command(BaseCommand):
    help = 'данная команда выполняет первоначальную настройку приложения, ' \
    'включая создание суперпользователя если база данных пуста'

    def add_arguments(self, parser):
        """данная функция предназначена для добавления аргументов командной строки"""
        parser.add_argument(
            '--skip-users',
            action='store_true',
            help='пропустить создание суперпользователя'
        )
        parser.add_argument(
            '--skip-refs',
            action='store_true', 
            help='пропустить заполнение справочников'
        )
        parser.add_argument(
            '--only-roles',
            action='store_true',
            help='заполнить только таблицу ролей'
        )

    def handle(self, *args, **options):
        """данная функция проверяет количество пользователей в базе данных и,
          если их нет, создает суперпользователя для доступа и управления админ-панелью"""
        self.stdout.write(self.style.HTTP_INFO('[настройка] запуск проверки первоначальной настройки..'))

        try:
            user_count = User.objects.count()
            
            if not options['skip_users']:
                if user_count == 0:
                    self.stdout.write(self.style.SUCCESS('[настройка] в базе данных нет пользователей, создается суперподаватель..'))
                    self.create_superuser_if_not_exists()
                else:
                    self.stdout.write(self.style.WARNING(f'[настройка] в базе данных уже есть {user_count} пользователь(ей), создание суперпользователя не выполняется..'))
            else:
                self.stdout.write(self.style.HTTP_INFO('[настройка] пропущено создание суперпользователя (--skip-users)'))

            if not options['skip_refs']:
                if options['only_roles']:
                    self.stdout.write(self.style.HTTP_INFO('[настройка] заполнение только таблицы ролей..'))
                    self.fill_roles()
                else:
                    with transaction.atomic():
                        self.fill_reference_tables()
            else:
                self.stdout.write(self.style.HTTP_INFO('[настройка] пропущено заполнение справочников (--skip-refs)'))

        except (OperationalError, ProgrammingError) as e:
            self.stderr.write(self.style.ERROR(f'[настройка] ошибка базы данных: {e}'))
            self.stderr.write(self.style.ERROR(f'[настройка] возможно миграции не были применены'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'[настройка] произошла непредвиденная ошибка: {e}'))

        self.stdout.write(self.style.HTTP_INFO('[настройка] проверка первоначальной настройки завершена!'))

    def create_superuser_if_not_exists(self):
        """данная функция создает суперпользователя, если он еще не существует в базе данных"""

        username = getattr(settings, 'SUPERUSER_USERNAME', 'admin')
        email = getattr(settings, 'SUPERUSER_EMAIL', 'admin@example.com')
        password = getattr(settings, 'SUPERUSER_PASSWORD', None)

        if not password:
            self.stderr.write(self.style.ERROR('пароль суперпользователя не установлен!'))
            return

        password_error = self.validate_password(password, username)
        if password_error:
            self.stderr.write(self.style.ERROR(f'ненадежный пароль: {password_error}'))
            return

        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'суперпользователь {username} уже существует.'))
        else:
            try:
                superuser = User.objects.create_superuser(
                    username=username,
                    email=email,
                    password=password,
                    first_name='Администратор', 
                    last_name='Системы'         
                )
                
                superuser.is_verified = True  
                
                if Role is not None:
                    admin_role = Role.objects.filter(role_name__iexact='администратор').first()
                    if admin_role:
                        superuser.role = admin_role
                
                superuser.save()
                
                self.stdout.write(self.style.SUCCESS(f'суперпользователь {username} создан!'))
                self.stdout.write(self.style.SUCCESS(f'полное имя: {superuser.full_name}'))
                self.stdout.write(self.style.SUCCESS(f'email: {email}'))
                self.stdout.write(self.style.SUCCESS(f'роль: {superuser.role.role_name if superuser.role else "не назначена"}'))
                
            except Exception as e:
                self.stderr.write(self.style.ERROR(f'ошибка при создании суперпользователя: {e}'))
                

    def validate_password(self, password, username):
        """данная функция проверяет надежность пароля для суперпользователя и возвращает соответствующее сообщение"""

        min_length = getattr(settings, 'SUPERUSER_MIN_PASSWORD_LENGTH', 8)
        if len(password) < min_length:
            return f'пароль должен содержать минимум {min_length} символов'

        weak_passwords = getattr(settings, 'WEAK_PASSWORDS', [])
        if password.lower() in weak_passwords:
            return 'пароль слишком простой (находится в списке слабых паролей)'

        if password.lower() == username.lower():
            return 'пароль не должен совпадать с именем пользователя'

        require_strong = getattr(settings, 'SUPERUSER_REQUIRE_STRONG_PASSWORD', False)
        if require_strong:
            errors = []
            if not re.search(r'[A-ZА-Я]', password):
                errors.append('заглавную букву')
            if not re.search(r'[a-zа-я]', password):
                errors.append('строчную букву')
            if not re.search(r'\d', password):
                errors.append('цифру')
            if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
                self.stdout.write(self.style.WARNING('рекомендуется использовать специальный символ в пароле'))
            
            if errors:
                return 'пароль должен содержать хотя бы одну ' + ', '.join(errors)

        return None

    def fill_reference_tables(self):
        """функция нужна для заполнения справочных таблиц начальными данными"""
        
        if not MODELS_AVAILABLE:
            self.stdout.write(self.style.WARNING('модели справочных таблиц не доступны. пропускаем заполнение справочных данных.'))
            return
        
        try:
            self.fill_roles()
            self.fill_course_categories()
            self.fill_course_types()
            self.fill_assignment_statuses()
            self.fill_answer_types()
        except (OperationalError, ProgrammingError) as e:
            self.stderr.write(self.style.WARNING(f'ошибка при работе со справочными таблицами: {e}'))
            self.stderr.write(self.style.WARNING('возможно, таблицы еще не созданы. примените миграции.'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'непредвиденная ошибка при заполнении справочных таблиц: {e}'))

    def fill_roles(self):
        """заполнение таблицы ролей пользователей"""
        if Role is None:
            self.stdout.write(self.style.WARNING('модель Role не доступна. пропускаем заполнение ролей.'))
            return
        
        roles = ['администратор', 'методист', 'преподаватель', 'слушатель курсов']
        
        created_count = 0
        for role_name in roles:
            if not Role.objects.filter(role_name__iexact=role_name).exists():
                Role.objects.create(role_name=role_name)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'создана роль: {role_name}'))
            else:
                self.stdout.write(self.style.HTTP_INFO(f'роль уже существует: {role_name}'))
        
        total_count = Role.objects.count()
        self.stdout.write(self.style.SUCCESS(f'роли пользователей: создано {created_count} новых, всего в базе: {total_count}'))

    def fill_course_categories(self):
        """функция заполнения таблицы категорий курсов"""
        if CourseCategory is None:
            return
            
        categories = [
            'физика',
            'астрономия', 
            'математика',
            'программирование',
            'информационные технологии',
            'литература',
            'история',
            'география',
            'психология',
            'алгебра',
            'геометрия',
            'информатика',
            'музыка',
            'дизайн',
            'химия',
            'биология'
        ]
        
        created_count = 0
        for category_name in categories:
            if not CourseCategory.objects.filter(course_category_name__iexact=category_name).exists():
                CourseCategory.objects.create(course_category_name=category_name)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'создана категория: {category_name}'))
            else:
                self.stdout.write(self.style.HTTP_INFO(f'категория уже существует: {category_name}'))
        
        total_count = CourseCategory.objects.count()
        self.stdout.write(self.style.SUCCESS(f'категории курсов: создано {created_count} новых, всего в базе: {total_count}'))

    def fill_course_types(self):
        """функция заполнения таблицы типов курсов"""
        if CourseType is None:
            return
            
        course_types = [
            {
                'name': 'образовательная программа',
                'description': 'Полноценная образовательная программа с учебным планом'
            },
            {
                'name': 'профессиональная переподготовка',
                'description': 'Программа профессиональной переподготовки для получения новой квалификации'
            },
            {
                'name': 'классная комната',
                'description': 'Интерактивная классная комната для проведения занятий, преимущественн используется преподавателями для своих учебных целей'
            },
            {
                'name': 'подготовка к экзаменам',
                'description': 'Курс подготовки к экзаменам и тестированиям, например ОГЭ, ЕГЭ, ДВИ в ВУЗы или же иные виды проверки уровня знаний'
            }
        ]
        
        created_count = 0
        for course_type in course_types:
            if not CourseType.objects.filter(course_type_name__iexact=course_type['name']).exists():
                CourseType.objects.create(
                    course_type_name=course_type['name'],
                    course_type_description=course_type['description']
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'создан тип курса: {course_type["name"]}'))
            else:
                self.stdout.write(self.style.HTTP_INFO(f'тип курса уже существует: {course_type["name"]}'))
        
        total_count = CourseType.objects.count()
        self.stdout.write(self.style.SUCCESS(f'типы курсов: создано {created_count} новых, всего в базе: {total_count}'))

    def fill_assignment_statuses(self):
        """функция заполнения таблицы статусов заданий"""
        if AssignmentStatus is None:
            return
            
        statuses = [
            'завершено',
            'на доработке', 
            'отклонено',
            'просрочено',
            'на проверке'
        ]
        
        created_count = 0
        for status_name in statuses:
            if not AssignmentStatus.objects.filter(assignment_status_name__iexact=status_name).exists():
                AssignmentStatus.objects.create(assignment_status_name=status_name)
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'создан статус задания: {status_name}'))
            else:
                self.stdout.write(self.style.HTTP_INFO(f'статус задания уже существует: {status_name}'))
        
        total_count = AssignmentStatus.objects.count()
        self.stdout.write(self.style.SUCCESS(f'статусы заданий: создано {created_count} новых, всего в базе: {total_count}'))

    def fill_answer_types(self):
        """заполнение таблицы типов ответов"""
        if AnswerType is None:
            return
            
        answer_types = [
            {
                'name': 'один ответ',
                'description': 'Вопрос с одним правильным ответом'
            },
            {
                'name': 'несколько ответов',
                'description': 'Вопрос с несколькими правильными ответами'
            },
            {
                'name': 'текст',
                'description': 'Текстовый ответ'
            },
            {
                'name': 'сопоставление',
                'description': 'Вопрос на сопоставление элементов'
            }
        ]
        
        created_count = 0
        for answer_type in answer_types:
            if not AnswerType.objects.filter(answer_type_name__iexact=answer_type['name']).exists():
                AnswerType.objects.create(
                    answer_type_name=answer_type['name'],
                    answer_type_description=answer_type['description']
                )
                created_count += 1
                self.stdout.write(self.style.SUCCESS(f'создан тип ответа: {answer_type["name"]}'))
            else:
                self.stdout.write(self.style.HTTP_INFO(f'тип ответа уже существует: {answer_type["name"]}'))
        
        total_count = AnswerType.objects.count()
        self.stdout.write(self.style.SUCCESS(f'типы ответов: создано {created_count} новых, всего в базе: {total_count}'))