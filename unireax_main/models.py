from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.core.validators import (
    MinLengthValidator, RegexValidator, MaxLengthValidator, 
    EmailValidator, FileExtensionValidator, MinValueValidator, 
    MaxValueValidator, URLValidator
)
from django.utils import timezone
from django.db import connection
from datetime import timedelta
import random, os, string
from django.core.files.storage import default_storage
from .utils.additional_function import calculate_course_progress
from django.db.models import Q, F, Func

ALLOWED_EXT = [
    'pdf', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx',
    'txt', 'md', 'rtf',
    'odt', 'ods', 'odp', 
    'csv', 

    'jpg', 'jpeg', 'png', 'gif', 'svg', 'webp', 'ico',
    'tiff', 'tif', 'bmp', 
    'ai', 'eps',

    'mp3', 'wav', 'ogg', 'aac', 'flac',

    'mp4', 'avi', 'mov', 'webm', 'mkv', 'wmv', 

    'zip', 'rar', '7z', 'tar', 'gz', 'bz2', 

    'py', 'java', 'cpp', 'c', 'h', 'hpp', 'cs', 
    'dart', 'html', 'css', 'js', 'ts', 
    'php', 'rb', 'go', 'swift', 'kt', 'rs', 
    'sql',
    'json', 'xml', 'yaml', 'yml', 'toml', 

    'epub', 'mobi', 'azw',

    'dwg', 'dxf', 'stl', 'obj', 'fbx', 'gltf', 'glb', 'blend'
]

class CharLength(Func):
    function = 'LENGTH'
    output_field = models.IntegerField()


# 1. роли 
class Role(models.Model):
    """данный класс представляет собой модель роли пользователя"""
    role_name = models.CharField(max_length=40, unique=True, verbose_name='Название роли',
        validators=[
            MinLengthValidator(3, message='Роль должна содержать минимум 3 символа'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z_\- ]+$',
                message='Разрешены только буквы, пробелы, дефисы (-) и подчеркивания (_)',
                code='invalid_chars'
            )
        ],
        help_text='От 3 до 40 символов. Буквы, пробелы, дефисы (-), подчеркивания (_)',
        error_messages={
            'unique': 'Роль с таким названием уже существует!',
            'max_length': 'Максимум 40 символов!',
            'required': 'Это обязательное для заполнения поле',
        }
    )
    
    def __str__(self):
        return self.role_name
    
    def clean(self):
        super().clean()
        
        if not self.role_name or self.role_name.strip() == '':
            raise ValidationError(
                {'role_name': 'Название роли не может быть пустым или состоять только из пробелов!'}
            )
        
        if not any(c.isalpha() for c in self.role_name):
            raise ValidationError(
                {'role_name': 'Должна быть хотя бы одна буква!'}
            )
        
        self.role_name = ' '.join(self.role_name.strip().split())
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'role'
        verbose_name = 'Роль'
        verbose_name_plural = 'Роли'
        constraints = [
            models.CheckConstraint(
                condition=Q(role_name__regex=r'^.{3,40}$'),
                name='role_length_check'
            ),
            models.CheckConstraint(
                condition=Q(role_name__regex=r'^[а-яА-Яa-zA-Z_\- ]+$'),
                name='role_valid_chars'
            ),
            models.CheckConstraint(
                condition=~Q(role_name__regex=r'^\s*$'),
                name='role_not_only_spaces'
            ),
        ]

# 2. пользователи
class User(AbstractUser):
    """данный класс представляет собой модель пользователя"""
    first_name = models.CharField('Имя', max_length=50,
        validators=[
            MinLengthValidator(2, message='Имя должно содержать минимум 2 символа'),
            MaxLengthValidator(50, message='Имя должно содержать максимум 50 символов'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z\- ]+$',
                message='Имя может содержать только буквы, дефисы и пробелы!',
                code='invalid_first_name'
            )
        ]
    )
    
    last_name = models.CharField('Фамилия', max_length=50,
        validators=[
            MinLengthValidator(1, message='Фамилия должна содержать минимум 1 символ'),
            MaxLengthValidator(50, message='Фамилия должна содержать максимум 50 символов'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z\- ]+$',
                message='Фамилия может содержать только буквы, дефисы и пробелы!',
                code='invalid_last_name'
            )
        ]
    )
    
    email = models.EmailField('Почта', unique=True,
        validators=[
            EmailValidator(message='Введите корректную почту: она должна содержать точку, доменное имя, название адреса и символ @'),
            MaxLengthValidator(254, message='Почта может содержать максимум 254 символа'),
        ]
    )
    
    username = models.CharField('Имя пользователя', max_length=150, unique=True,
        validators=[
            MinLengthValidator(1, message='Имя пользователя должно содержать минимум 1 символ'),
            MaxLengthValidator(150, message='Имя пользователя должно содержать максимум 150 символов'),
            RegexValidator(
                regex=r'^[\w.@-]+$',
                message='Имя пользователя может содержать только буквы, цифры и символы: @ . - _',
                code='invalid_username'
            )
        ],
        help_text='Обязательное поле. Не более 150 символов. Только буквы, цифры и символы: @ . - _'
    )
    
    patronymic = models.CharField('Отчество', max_length=50, blank=True, null=True,
        validators=[
            MinLengthValidator(2, message='Отчество должно содержать минимум 2 символа'),
            MaxLengthValidator(50, message='Отчество должно содержать максимум 50 символов'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z\- ]*$',
                message='Отчество может содержать только буквы, дефисы и пробелы',
                code='invalid_patronymic'
            )
        ],
        help_text='Необязательное поле. Если указано, должно быть от 2 до 50 символов'
    )
    
    is_verified = models.BooleanField(default=False, verbose_name='Подтверждён')
    
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, verbose_name='Роль', null=True, blank=True,
        help_text='Роль пользователя в системе'
    )
    
    position = models.CharField('Должность', max_length=100, blank=True, null=True,
        validators=[
            MaxLengthValidator(100, message='Название должности должно содержать максимум 100 символов'),
        ],
        help_text='Полное название должности на текущем месте работы требуется для методистов и преподавателей'
    )
    
    educational_institution = models.CharField('Учебное заведение', max_length=100, blank=True, null=True,
        validators=[
            MaxLengthValidator(100, message='Название учебного заведения должно содержать максимум 100 символов'),
        ],
        help_text='Указание места работы или места получения образования (например, название ВУЗа или колледжа) требуется для методистов и преподавателей!'
    )
    
    certificate_file = models.FileField('Справка с места работы/документ об образовании', 
        upload_to='certificates/%Y/%m/%d/', blank=True, null=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png', 'pdf', 'doc', 'docx'],
                message='Поддерживаемые форматы: JPG, JPEG, PNG, PDF, DOC, DOCX'
            ),
        ],
        help_text='Подтверждение места работы или уровня образования. Максимальный размер: 10 МБ',
    )

    is_light_theme = models.BooleanField(default=True, verbose_name='Тема интерфейса',
        choices=[(True, 'Светлая'), (False, 'Тёмная')],
        help_text='Выберите цветовую тему интерфейса'
    )    
    
    def get_theme(self, request=None, default='light'):
        """функция получения темы приложения"""
        if request and 'theme' in request.COOKIES:
            theme_cookie = request.COOKIES['theme']
            if theme_cookie in ['light', 'dark']:  
                return theme_cookie
        return 'light' if self.is_light_theme else 'dark'
        
    def __str__(self):
        return f'{self.last_name} {self.first_name}'
    
    @property
    def full_name(self):
        fio = [self.last_name, self.first_name]
        if self.patronymic:
            fio.append(self.patronymic)
        return ' '.join(fio)
    
    @property
    def is_admin(self):
        return self.role and self.role.role_name.lower() == "администратор"
    
    @property
    def is_teacher_or_methodist(self):
        if not self.role:
            return False
        role_name = self.role.role_name.lower()
        return role_name in ['преподаватель', 'методист']
    
    @property
    def is_student_or_admin(self):
        if not self.role:
            return False
        role_name = self.role.role_name.lower()
        return role_name in ['слушатель курсов', 'администратор']
    
    def clean(self):
        super().clean()
        errors = {}
        
        if self.certificate_file:
            try:
                if self.certificate_file.size > 10 * 1024 * 1024:
                    errors['certificate_file'] = 'Файл слишком большой! Максимальный размер: 10 МБ'
            except (ValueError, AttributeError):
                pass
        
        if self.role:
            role_name = self.role.role_name.lower()
            
            if role_name in ['методист', 'преподаватель']:
                if not self.position or not self.position.strip():
                    errors['position'] = 'Поле "Должность" обязательно для методистов и преподавателей'
                
                if not self.educational_institution or not self.educational_institution.strip():
                    errors['educational_institution'] = 'Поле "Учебное заведение" обязательно для методистов и преподавателей'
                
                if not self.certificate_file:
                    errors['certificate_file'] = 'Справка с места работы/документ об образовании обязателен для методистов и преподавателей'
            
            elif role_name in ['слушатель курсов', 'администратор']:
                self.is_verified = True
        
        if self.patronymic and self.patronymic.strip():
            if len(self.patronymic.strip()) < 2:
                errors['patronymic'] = 'Отчество должно содержать минимум 2 символа'
            self._normalize_text_field('patronymic')
        else:
            self.patronymic = None
        
        if self.email:
            self.email = self.email.strip().lower()
        
        if errors:
            raise ValidationError(errors)
    
    def _normalize_text_field(self, field_name):
        """Нормализует текстовое поле"""
        value = getattr(self, field_name)
        if value:
            setattr(self, field_name, ' '.join(value.strip().split()))
    
    def save(self, *args, **kwargs):
        if self.role:
            role_name = self.role.role_name.lower()
            if role_name in ['слушатель курсов', 'администратор']:
                self.is_verified = True
        
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'user'
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        constraints = [
            models.CheckConstraint(
                condition=Q(email__regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'),
                name='user_email_format'
            ),
            models.CheckConstraint(
                condition=Q(username__regex=r'^[\w.@-]+$'),
                name='user_username_format'
            ),
            models.CheckConstraint(
                condition=Q(first_name__regex=r'^[а-яА-Яa-zA-Z\- ]+$'),
                name='user_first_name_format'
            ),
            models.CheckConstraint(
                condition=Q(last_name__regex=r'^[а-яА-Яa-zA-Z\- ]+$'),
                name='user_last_name_format'
            ),
        ]

# 3. категории курсов
class CourseCategory(models.Model):
    """"данный класс описывает """
    course_category_name = models.CharField('Название категории курса', max_length=100, unique=True,
        validators=[
            MinLengthValidator(2, message='Минимум 2 символа'),
            MaxLengthValidator(100, message='Максимум 100 символов'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z0-9_\- ]+$',
                message='Разрешены только буквы, цифры, пробелы, дефисы и подчёркивания'
            )
        ],
        help_text='Название категории курса (2-100 символов)',
        error_messages={
            'unique': 'Категория с таким названием уже существует',
            'required': 'Это обязательное поле'
        }
    )
    
    def __str__(self):
        return self.course_category_name
    
    def clean(self):
        super().clean()
        
        if not self.course_category_name or self.course_category_name.strip() == '':
            raise ValidationError(
                {'course_category_name': 'Название категории не может быть пустым!'}
            )
        
        self.course_category_name = ' '.join(self.course_category_name.strip().split())
        
        if not any(c.isalpha() for c in self.course_category_name):
            raise ValidationError(
                {'course_category_name': 'Должна быть хотя бы одна буква!'}
            )
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'course_category'
        verbose_name = 'Категория курса'
        verbose_name_plural = 'Категории курсов'
        constraints = [
            models.CheckConstraint(
                condition=Q(course_category_name__regex=r'^[а-яА-Яa-zA-Z0-9_\- ]+$'),
                name='course_category_name_valid_chars'
            ),
            models.CheckConstraint(
                condition=~Q(course_category_name__regex=r'^\s*$'),
                name='course_category_not_only_spaces'
            ),
        ]

# 4. типы курсов
class CourseType(models.Model):
    course_type_name = models.CharField('Название типа курса', max_length=100, unique=True,
        validators=[
            MinLengthValidator(2, message='Минимум 2 символа'),
            MaxLengthValidator(100, message='Максимум 100 символов'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z0-9_\- ]+$',
                message='Разрешены только буквы, цифры, пробелы, дефисы и подчёркивания'
            )
        ],
        help_text='Название типа курса (2-100 символов)'
    )
    
    course_type_description = models.TextField('Описание типа курса', null=True, blank=True,
        validators=[
            MaxLengthValidator(250, message='Описание не должно превышать 250 символов')
        ],
        help_text='Необязательное поле. Описание типа курса (до 250 символов)'
    )
    
    def __str__(self):
        return self.course_type_name
    
    def clean(self):
        super().clean()
        
        if not self.course_type_name or self.course_type_name.strip() == '':
            raise ValidationError(
                {'course_type_name': 'Название типа курса не может быть пустым'}
            )
        
        self.course_type_name = ' '.join(self.course_type_name.strip().split())
        
        if self.course_type_description:
            self.course_type_description = self.course_type_description.strip()
            
            if len(self.course_type_description) < 10 and self.course_type_description:
                raise ValidationError({
                    'course_type_description': 'Если указано описание, то оно должно содержать минимум 10 символов'
                })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'course_type'
        verbose_name = 'Тип курса'
        verbose_name_plural = 'Типы курсов'

# 5. статусы заданий
class AssignmentStatus(models.Model):
    assignment_status_name = models.CharField('Название статуса задания', max_length=50, unique=True,
        validators=[
            MinLengthValidator(2, message='Минимум 2 символа'),
            MaxLengthValidator(50, message='Максимум 50 символов'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z_\- ]+$',
                message='Разрешены только буквы, пробелы, дефисы и подчёркивания'
            )
        ],
        help_text='Название статуса задания (2-50 символов)'
    )
    
    def __str__(self):
        return self.assignment_status_name
    
    def clean(self):
        super().clean()
        if not self.assignment_status_name or self.assignment_status_name.strip() == '':
            raise ValidationError(
                {'assignment_status_name': 'Название статуса не может быть пустым!'}
            )
        
        self.assignment_status_name = ' '.join(self.assignment_status_name.strip().split())
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'assignment_status'
        verbose_name = 'Статус задания'
        verbose_name_plural = 'Статусы заданий'
        constraints = [
            models.CheckConstraint(
                condition=Q(assignment_status_name__regex=r'^[а-яА-Яa-zA-Z_\- ]+$'),
                name='assignment_status_valid_chars'
            ),
        ]

# 6. курсы
class Course(models.Model):
    course_name = models.CharField('Название курса', max_length=200,
        validators=[
            MinLengthValidator(3, message='Минимум 3 символа'),
            MaxLengthValidator(200, message='Максимум 200 символов'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z0-9_\- ,.!?"\'():; ]+$',
                message='Недопустимые символы в названии курса'
            )
        ],
        help_text='Название курса (3-200 символов)'
    )
    
    course_description = models.TextField('Описание курса', null=True, blank=True,
        validators=[
            MaxLengthValidator(300, message='Описание не должно превышать 300 символов')
        ],
        help_text='Необязательное поле. Описание курса (до 300 символов, необязательно)'
    )
    
    course_price = models.DecimalField('Цена курса', max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[
            MinValueValidator(0, message='Цена не может быть отрицательной'),
            MaxValueValidator(9999999.99, message='Цена курса слишком велика, такого быть не может!')
        ],
        help_text='Цена курса в рублях (если курс является платным)'
    )
    
    course_category = models.ForeignKey(CourseCategory, on_delete=models.SET_NULL, verbose_name='Категория курса', null=True, blank=True)
    
    course_photo_path = models.ImageField('Фотография курса', null=True, blank=True, upload_to='course_photos/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=['jpg', 'jpeg', 'png'],
                message='Поддерживаются только изображения форматов .jpg, .jpeg и .png'
            )
        ],
        help_text='Изображение курса (необязательно)'
    )
    
    has_certificate = models.BooleanField('Есть сертификат', default=False,
        help_text='Определяет, выдаётся ли сертификат после завершения курса'
    )
    
    course_max_places = models.IntegerField('Максимум мест', null=True, blank=True,
        validators=[
            MinValueValidator(1, message='Количество мест должно быть положительным'),
            MaxValueValidator(1000, message='Максимум 1000 мест')
        ],
        help_text='Максимальное количество участников (необязательно)'
    )
    
    course_hours = models.IntegerField('Количество часов',
        validators=[
            MinValueValidator(1, message='Курс должен длиться минимум 1 час'),
            MaxValueValidator(3000, message='Слишком большое количество часов')
        ],
        help_text='Общая продолжительность курса в часах (от 1 до 3000)'
    )
    
    is_completed = models.BooleanField('Завершён', default=True, help_text='Завершено ли наполнение курса материалами')
    
    code_link = models.CharField('Ccылка видео-встречи курса', max_length=200, null=True, blank=True,
            validators=[
                URLValidator(message='Пожалуйста, введите корректную ссылку!'),
            ],
            help_text='Ссылка для доступа к комнате видео-встречи курса, например ранее созданный Яндекс.Телемост (необязательно)'
        )
    course_type = models.ForeignKey(CourseType, on_delete=models.CASCADE, verbose_name='Тип курса')
    
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, verbose_name='Создан пользователем', 
        null=True, blank=True
    )
    
    is_active = models.BooleanField('Активность курса', default=True)
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    
    def __str__(self):
        return self.course_name
    
    def clean(self):
        super().clean()
        
        if not self.course_name or self.course_name.strip() == '':
            raise ValidationError({'course_name': 'Название курса обязательно'})
        
        self.course_name = ' '.join(self.course_name.strip().split())
        
        if self.course_description:
            self.course_description = self.course_description.strip()
            if len(self.course_description) < 20 and self.course_description:
                raise ValidationError({
                    'course_description': 'Если указано описание, оно должно содержать минимум 20 символов!'
                })
        
        if self.created_by:
            if not self.created_by.role:
                raise ValidationError({
                    'created_by': 'У создателя курса должна быть указана роль!'
                })
            role_name = self.created_by.role.role_name.lower()
            if role_name not in ['методист', 'преподаватель']:
                raise ValidationError({
                    'created_by': 'Курс может быть создан только методистом или преподавателем!'
                })
        
        if self.course_price is not None and self.course_price < 0:
            raise ValidationError({'course_price': 'Цена не может быть отрицательной!'})
        
        if self.course_max_places is not None and self.course_max_places <= 0:
            raise ValidationError({'course_max_places': 'Количество мест должно быть положительным!'})
        
        if self.course_hours <= 0:
            raise ValidationError({'course_hours': 'Количество часов должно быть положительным!'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def rating(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT calculate_course_rating(%s)", [self.id])
            return cursor.fetchone()[0] or 0
    
    def get_completion(self, user_id):
        with connection.cursor() as cursor:
            cursor.execute("SELECT calculate_course_completion(%s, %s)", [user_id, self.id])
            return cursor.fetchone()[0] or 0
    
    def total_points(self):
        with connection.cursor() as cursor:
            cursor.execute("SELECT calculate_total_course_points(%s)", [self.id])
            return cursor.fetchone()[0] or 0
    
    class Meta:
        db_table = 'course'
        verbose_name = 'Курс'
        verbose_name_plural = 'Курсы'
        constraints = [
            models.CheckConstraint(
                condition=Q(course_price__isnull=True) | 
                          Q(course_price__gte=0),
                name='course_price_non_negative_check'
            ),
            models.CheckConstraint(
                condition=Q(course_max_places__isnull=True) | 
                          Q(course_max_places__gt=0),
                name='course_max_places_positive_check'
            ),
            models.CheckConstraint(
                condition=Q(course_hours__gt=0),
                name='course_hours_positive_check'
            ),
        ]

# 7. курсы_преподаватели
class CourseTeacher(models.Model):
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, verbose_name='Курс'
    )
    
    teacher = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Преподаватель'
    )
    
    start_date = models.DateField('Дата начала работы на курсе', 
        default=timezone.now, null=True, blank=True
    )
    
    is_active = models.BooleanField('Активность преподавателя/методиста на курсе', default=True)
    
    
    def __str__(self):
        return f'{self.teacher} - {self.course}'
    
    def clean(self):
        super().clean()
        
        if self.teacher and not self.teacher.is_teacher_or_methodist:
            raise ValidationError({
                'teacher': 'Назначить можно только пользователя с ролью преподавателя или методиста'
            })
        
        if self.start_date and self.start_date < timezone.now().date():
            raise ValidationError({
                'start_date': 'Дата начала не может быть в прошлом'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'course_teacher'
        verbose_name = 'Персонал курса'
        verbose_name_plural = 'Персоналы курсов'
        unique_together = ('course', 'teacher')
        constraints = [
            models.CheckConstraint(
                condition=Q(start_date__isnull=True) | 
                          Q(start_date__gte=timezone.now().date()),
                name='course_teacher_start_date_future_check'
            ),
        ]

# 8. лекции
class Lecture(models.Model):
    lecture_name = models.CharField('Название лекции', max_length=200,
        validators=[
            MinLengthValidator(3, message='Минимум 3 символа'),
            MaxLengthValidator(200, message='Максимум 200 символов')
        ],
        help_text='Название лекции (3-200 символов)'
    )
    
    lecture_content = models.TextField('Содержание лекции',
        validators=[
            MinLengthValidator(50, message='Содержание должно содержать минимум 50 символов'),
            MaxLengthValidator(50000, message='Содержание не должно превышать 50000 символов')
        ],
        help_text='Текст лекции (50-50000 символов)'
    )
    
    lecture_document_path = models.FileField('Документ лекции', 
        upload_to='lectures/%Y/%m/%d/', null=True, blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'ppt', 'pptx', 'txt'],
                message='Поддерживаются файлы: PDF, DOC, DOCX, PPT, PPTX, TXT'
            )
        ],
        help_text='Дополнительный документ к лекции (необязательно)'
    )
    
    lecture_order = models.IntegerField('Порядок лекции',
        validators=[
            MinValueValidator(1, message='Порядок должен быть положительным числом')
        ],
        help_text='Порядковый номер лекции в курсе'
    )
    
    course = models.ForeignKey(
        Course, on_delete=models.CASCADE, verbose_name='Курс'
    )
    
    is_active = models.BooleanField('Активность лекции', default=True)
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    def __str__(self):
        return self.lecture_name
    
    def clean(self):
        super().clean()
        
        if not self.lecture_name or self.lecture_name.strip() == '':
            raise ValidationError({'lecture_name': 'Название лекции обязательно'})
        
        self.lecture_name = ' '.join(self.lecture_name.strip().split())
        
        if not self.lecture_content or len(self.lecture_content.strip()) < 50:
            raise ValidationError({
                'lecture_content': 'Содержание лекции должно содержать минимум 50 символов'
            })
        
        if self.lecture_order <= 0:
            raise ValidationError({
                'lecture_order': 'Порядок лекции должен быть положительным числом'
            })
        
        if self.lecture_document_path and self.lecture_document_path.size > 50 * 1024 * 1024:
            raise ValidationError({
                'lecture_document_path': 'Файл слишком большой. Максимальный размер: 50 МБ'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'lecture'
        verbose_name = 'Лекция'
        verbose_name_plural = 'Лекции'
        ordering = ['course', 'lecture_order']
        constraints = [
            models.CheckConstraint(
                condition=Q(lecture_order__gt=0),
                name='lecture_order_positive_check'
            ),
            models.UniqueConstraint(
                fields=['course', 'lecture_order'],
                name='unique_lecture_order_course'
            ),
        ]

# 9. практические работы
class PracticalAssignment(models.Model):
    GRADING_TYPE_CHOICES = [
        ('points', 'По баллам'),
        ('pass_fail', 'Зачёт/незачёт'),
    ]
    
    practical_assignment_name = models.CharField('Название задания', max_length=200,
        validators=[
            MinLengthValidator(3, message='Минимум 3 символа'),
            MaxLengthValidator(200, message='Максимум 200 символов')
        ],
        help_text='Название практического задания (3-200 символов)'
    )
    
    practical_assignment_description = models.TextField('Описание задания',
        validators=[
            MinLengthValidator(20, message='Описание должно содержать минимум 20 символов'),
            MaxLengthValidator(5000, message='Описание не должно превышать 5000 символов')
        ],
        help_text='Подробное описание задания (20-5000 символов)'
    )
    
    assignment_document_path = models.FileField('Документ задания', 
        upload_to='assignments/%Y/%m/%d/', null=True, blank=True,
        validators=[
            FileExtensionValidator(
                allowed_extensions=['pdf', 'doc', 'docx', 'zip', 'rar'],
                message='Поддерживаются файлы: PDF, DOC, DOCX, ZIP, RAR'
            )
        ],
        help_text='Файл с дополнительными материалами (необязательно)'
    )
    
    assignment_criteria = models.TextField('Критерии оценки', null=True, blank=True,
        validators=[
            MaxLengthValidator(2000, message='Критерии не должны превышать 2000 символов')
        ],
        help_text='Критерии оценки задания (до 2000 символов, необязательно)'
    )
    
    lecture = models.ForeignKey(
        Lecture, on_delete=models.CASCADE, verbose_name='Лекция'
    )
    
    assignment_deadline = models.DateTimeField('Срок сдачи', null=True, blank=True,
        help_text='Крайний срок сдачи задания (необязательно)'
    )
    
    grading_type = models.CharField('Тип оценки', max_length=20, choices=GRADING_TYPE_CHOICES, default='points')
    
    max_score = models.IntegerField('Максимальный балл', null=True, blank=True,
        validators=[
            MinValueValidator(1, message='Максимальный балл должен быть положительным'),
            MaxValueValidator(1000, message='Максимальный балл не должен превышать 1000')
        ],
        help_text='Максимально возможный балл за задание'
    )
    
    is_active = models.BooleanField('Активность практического задания', default=True)
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)

    is_can_pin_after_deadline = models.BooleanField('Можно ли прикреплять работу после срока сдачи')
    
    def __str__(self):
        return self.practical_assignment_name
    
    def clean(self):
        super().clean()
        
        if not self.practical_assignment_name or self.practical_assignment_name.strip() == '':
            raise ValidationError({'practical_assignment_name': 'Название задания обязательно'})
        
        self.practical_assignment_name = ' '.join(self.practical_assignment_name.strip().split())
        
        if not self.practical_assignment_description or len(self.practical_assignment_description.strip()) < 20:
            raise ValidationError({
                'practical_assignment_description': 'Описание задания должно содержать минимум 20 символов!'
            })
        
        if self.assignment_document_path and self.assignment_document_path.size > 100 * 1024 * 1024:
            raise ValidationError({
                'assignment_document_path': 'Файл слишком большой. Максимальный размер: 100 МБ'
            })
        
        if self.grading_type == 'points':
            if self.max_score is None or self.max_score <= 0:
                raise ValidationError({
                    'max_score': 'Для типа оценки "По баллам" необходимо указать положительный максимальный балл!'
                })
        
        if self.grading_type == 'pass_fail' and self.max_score is not None:
            raise ValidationError({
                'max_score': 'Для типа оценки "Зачёт/незачёт" не указывается максимальный балл!'
            })
        
        if self.assignment_deadline:
            if self.pk:
                try:
                    original = PracticalAssignment.objects.get(pk=self.pk)
                    if original.assignment_deadline != self.assignment_deadline:
                        if self.assignment_deadline <= timezone.now():
                            raise ValidationError({
                                'assignment_deadline': 'Срок сдачи должен быть в будущем!'
                            })
                except PracticalAssignment.DoesNotExist:
                    if self.assignment_deadline <= timezone.now():
                        raise ValidationError({
                            'assignment_deadline': 'Срок сдачи должен быть в будущем!'
                        })
            else:
                if self.assignment_deadline <= timezone.now():
                    raise ValidationError({
                        'assignment_deadline': 'Срок сдачи должен быть в будущем!'
                    })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'practical_assignment'
        verbose_name = 'Практическое задание'
        verbose_name_plural = 'Практические задания'
        constraints = [
            models.CheckConstraint(
                condition=Q(grading_type__in=['points', 'pass_fail']),
                name='grading_type_check'
            ),
            models.CheckConstraint(
                condition=~Q(grading_type='points') | 
                          Q(max_score__isnull=False) & Q(max_score__gt=0),
                name='max_score_required_for_points_check'
            ),
        ]

# 10. пользователи (слушатели курсов) и их прикрепленные практические работы
class UserPracticalAssignment(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Пользователь'
    )
    
    practical_assignment = models.ForeignKey(
        PracticalAssignment, on_delete=models.CASCADE, verbose_name='Практическое задание'
    )
    
    submission_date = models.DateTimeField('Дата сдачи', null=True, blank=True,
        help_text='Дата и время отправки работы'
    )
    
    submission_status = models.ForeignKey(
        AssignmentStatus, on_delete=models.PROTECT, verbose_name='Статус сдачи',
        help_text='Текущий статус выполнения задания'
    )
    
    attempt_number = models.IntegerField('Номер попытки', default=1,
        validators=[
            MinValueValidator(1, message='Номер попытки должен быть положительным')
        ],
        help_text='Номер попытки сдачи задания'
    )
    
    comment = models.TextField('Комментарий к сдаче', null=True, blank=True,
        validators=[
            MaxLengthValidator(2000, message='Комментарий не должен превышать 2000 символов')
        ],
        help_text='Комментарий студента к отправленной работе (до 2000 символов)'
    )
    
    submitted_at = models.DateTimeField('Дата отправки', auto_now_add=True)
    
    def __str__(self):
        return f'{self.user} - {self.practical_assignment} (попытка {self.attempt_number})'
    
    def clean(self):
        super().clean()
        
        if self.attempt_number <= 0:
            raise ValidationError({
                'attempt_number': 'Номер попытки должен быть положительным числом'
            })
        
        if self.submission_date and self.submission_date > timezone.now():
            raise ValidationError({
                'submission_date': 'Дата сдачи не может быть в будущем'
            })
        
        if self.comment and len(self.comment.strip()) > 2000:
            raise ValidationError({
                'comment': 'Комментарий не должен превышать 2000 символов'
            })
        
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    @property
    def files(self):
        return self.assignmentsubmissionfile_set.all()
    
    class Meta:
        db_table = 'user_practical_assignment'
        verbose_name = 'Сдача практического задания'
        verbose_name_plural = 'Сдачи практических заданий'
        constraints = [
            models.CheckConstraint(
                condition=Q(attempt_number__gt=0),
                name='user_practical_assignment_attempt_number_check'
            ),
            models.UniqueConstraint(
                fields=['user', 'practical_assignment', 'attempt_number'],
                name='unique_user_assignment_attempt'
            ),
        ]

# 11. пользователи_курсы
class UserCourse(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курс')
    
    registration_date = models.DateField('Дата регистрации', default=timezone.now,
        help_text='Дата записи пользователя на курс'
    )
    
    status_course = models.BooleanField('Курс завершён', default=False,
        help_text='Завершил ли пользователь курс'
    )
    
    payment_date = models.DateTimeField('Дата оплаты', null=True, blank=True,
        help_text='Дата и время оплаты курса (если требуется)'
    )
    
    completion_date = models.DateField('Дата завершения', null=True, blank=True,
        help_text='Дата фактического завершения курса'
    )
    
    course_price = models.DecimalField('Цена курса на момент покупки', max_digits=10, decimal_places=2, null=True, blank=True,
        validators=[
            MinValueValidator(0, message='Цена не может быть отрицательной')
        ],
        help_text='Фактическая цена, по которой был приобретён курс'
    )
    
    is_active = models.BooleanField('Активность слушателя на курсе', default=True,
        help_text='Активно ли участие пользователя в курсе'
    )
    
    enrolled_at = models.DateTimeField('Дата зачисления', auto_now_add=True)
    
    def __str__(self):
        return f'{self.user} - {self.course}'
    
    def clean(self):
        super().clean()
        
        if self.registration_date and self.registration_date > timezone.now().date():
            raise ValidationError({
                'registration_date': 'Дата регистрации не может быть в будущем'
            })
        
        if self.completion_date and self.completion_date < self.registration_date:
            raise ValidationError({
                'completion_date': 'Дата завершения не может быть раньше даты регистрации'
            })
        
        if self.payment_date and self.payment_date > timezone.now():
            raise ValidationError({
                'payment_date': 'Дата оплаты не может быть в будущем'
            })
        
        if self.course_price and self.course_price < 0:
            raise ValidationError({
                'course_price': 'Цена не может быть отрицательной'
            })
        
        if self.status_course and not self.completion_date:
            raise ValidationError({
                'completion_date': 'При завершении курса должна быть указана дата завершения'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'user_course'
        verbose_name = 'Пользователь на курсе'
        verbose_name_plural = 'Пользователи на курсах'
        unique_together = ('user', 'course')
        constraints = [
            models.CheckConstraint(
                condition=Q(registration_date__lte=timezone.now().date()),
                name='user_course_registration_date_past_check'
            ),
            models.CheckConstraint(
                condition=~Q(status_course=True) | 
                          Q(completion_date__isnull=False),
                name='user_course_completion_date_required_check'
            ),
            models.CheckConstraint(
                condition=Q(course_price__isnull=True) | 
                          Q(course_price__gte=0),
                name='user_course_price_non_negative_check'
            ),
        ]

# 12. обратная связь по практическим работам
class Feedback(models.Model):
    user_practical_assignment = models.OneToOneField(UserPracticalAssignment, on_delete=models.CASCADE, verbose_name='Сдача задания')
    
    score = models.IntegerField('Балл', null=True, blank=True,
        validators=[
            MinValueValidator(0, message='Балл не может быть отрицательным'),
            MaxValueValidator(1000, message='Балл не должен превышать 1000')
        ],
        help_text='Количество набранных баллов'
    )
    
    is_passed = models.BooleanField('Зачтено', null=True, blank=True,
        help_text='Зачтена ли работа'
    )
    
    comment_feedback = models.TextField('Комментарий преподавателя', null=True, blank=True,
        validators=[
            MaxLengthValidator(5000, message='Комментарий не должен превышать 5000 символов')
        ],
        help_text='Комментарий преподавателя к работе (до 5000 символов)'
    )
    
    given_at = models.DateTimeField('Дата оценки', auto_now_add=True)
    given_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name='Оценку выставил',
        help_text='Преподаватель, который проверил работу'
    )
    
    def __str__(self):
        return f'Обратная связь для {self.user_practical_assignment}'
    
    def clean(self):
        super().clean()
        
        grading_type = self.user_practical_assignment.practical_assignment.grading_type
        
        if grading_type == 'points':
            if self.score is None:
                raise ValidationError({
                    'score': 'Для типа оценки "По баллам" необходимо указать балл'
                })
            if self.is_passed is not None:
                raise ValidationError({
                    'is_passed': 'Для типа оценки "По баллам" поле "Зачтено" должно быть пустым'
                })
            if self.score < 0 or self.score > self.user_practical_assignment.practical_assignment.max_score:
                raise ValidationError({
                    'score': f'Балл должен быть в диапазоне от 0 до {self.user_practical_assignment.practical_assignment.max_score}'
                })
        
        elif grading_type == 'pass_fail':
            if self.is_passed is None:
                raise ValidationError({
                    'is_passed': 'Для типа оценки "Зачёт/незачёт" необходимо указать, зачтена ли работа'
                })
            if self.score is not None:
                raise ValidationError({
                    'score': 'Для типа оценки "Зачёт/незачёт" поле "Балл" должно быть пустым'
                })
        
        if self.comment_feedback and len(self.comment_feedback.strip()) > 5000:
            raise ValidationError({
                'comment_feedback': 'Комментарий не должен превышать 5000 символов'
            })
        
        if self.given_by and not self.given_by.is_teacher_or_methodist:
            raise ValidationError({
                'given_by': 'Обратную связь может оставлять только преподаватель или методист'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'feedback'
        verbose_name = 'Обратная связь'
        verbose_name_plural = 'Обратные связи'

# 13. отзывы
class Review(models.Model):
    course = models.ForeignKey(Course, on_delete=models.CASCADE, verbose_name='Курс')
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')
    
    rating = models.IntegerField('Рейтинг', choices=[(i, i) for i in range(1, 6)],
        help_text='Оценка курса от 1 до 5 звёзд'
    )
    
    publish_date = models.DateTimeField('Дата публикации', default=timezone.now)
    
    comment_review = models.TextField('Комментарий к отзыву', null=True, blank=True,
        validators=[
            MaxLengthValidator(2000, message='Комментарий не должен превышать 2000 символов')
        ],
        help_text='Дополнительный комментарий (до 2000 символов)'
    )
    
    is_approved = models.BooleanField('Одобрен', default=False,
        help_text='Проверен ли отзыв модератором'
    )
    
    def __str__(self):
        return f'Отзыв от {self.user} на {self.course}'
    
    def clean(self):
        super().clean()
        
        
        if self.comment_review and len(self.comment_review.strip()) > 2000:
            raise ValidationError({
                'comment_review': 'Комментарий не должен превышать 2000 символов'
            })
        
        if self.rating < 1 or self.rating > 5:
            raise ValidationError({
                'rating': 'Рейтинг должен быть в диапазоне от 1 до 5'
            })
        
        if self.publish_date and self.publish_date > timezone.now():
            raise ValidationError({
                'publish_date': 'Дата публикации не может быть в будущем'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'review'
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        unique_together = ('course', 'user')
        constraints = [
            models.CheckConstraint(
                condition=Q(rating__gte=1) & 
                          Q(rating__lte=5),
                name='review_rating_range_check'
            ),
        ]

# 14. типы ответов
class AnswerType(models.Model):
    answer_type_name = models.CharField('Название типа ответа', max_length=50, unique=True,
        validators=[
            MinLengthValidator(2, message='Минимум 2 символа'),
            MaxLengthValidator(50, message='Максимум 50 символов'),
            RegexValidator(
                regex=r'^[а-яА-Яa-zA-Z_\- ]+$',
                message='Разрешены только буквы, пробелы, дефисы и подчёркивания'
            )
        ],
        help_text='Название типа ответа (2-50 символов)'
    )
    
    answer_type_description = models.TextField('Описание типа ответа', null=True, blank=True,
        validators=[
            MaxLengthValidator(500, message='Описание не должно превышать 1000 символов')
        ],
        help_text='Описание типа ответа (до 500 символов)'
    )
    
    def __str__(self):
        return self.answer_type_name
    
    def clean(self):
        super().clean()
        
        if not self.answer_type_name or self.answer_type_name.strip() == '':
            raise ValidationError({
                'answer_type_name': 'Название типа ответа обязательно'
            })
        
        self.answer_type_name = ' '.join(self.answer_type_name.strip().split())
        
        if self.answer_type_description and len(self.answer_type_description.strip()) > 1000:
            raise ValidationError({
                'answer_type_description': 'Описание не должно превышать 1000 символов'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'answer_type'
        verbose_name = 'Тип ответа'
        verbose_name_plural = 'Типы ответов'

# 15. тесты
class Test(models.Model):
    GRADING_FORM_CHOICES = [
        ('points', 'По баллам'),
        ('pass_fail', 'Зачёт/незачёт'),
    ]
    
    test_name = models.CharField('Название теста', max_length=200,
        validators=[
            MinLengthValidator(3, message='Минимум 3 символа'),
            MaxLengthValidator(200, message='Максимум 200 символов')
        ],
        help_text='Название теста (3-200 символов)'
    )
    
    test_description = models.TextField('Описание теста', null=True, blank=True,
        validators=[
            MaxLengthValidator(2000, message='Описание не должно превышать 2000 символов')
        ],
        help_text='Описание теста (до 2000 символов)'
    )
    
    is_final = models.BooleanField('Финальный тест', default=False,
        help_text='Является ли тест финальным для курса'
    )
    
    lecture = models.ForeignKey(
        Lecture, on_delete=models.CASCADE, verbose_name='Лекция'
    )
    
    max_attempts = models.IntegerField('Максимум попыток', null=True, blank=True,
        validators=[
            MinValueValidator(1, message='Количество попыток должно быть положительным'),
            MaxValueValidator(100, message='Максимум 100 попыток')
        ],
        help_text='Максимальное количество попыток прохождения теста'
    )
    
    grading_form = models.CharField('Форма оценки', max_length=20, choices=GRADING_FORM_CHOICES, default='points')
    
    passing_score = models.IntegerField('Проходной балл', null=True, blank=True,
        validators=[
            MinValueValidator(0, message='Проходной балл не может быть отрицательным'),
            MaxValueValidator(3000, message='Проходной балл не должен превышать 3000')
        ],
        help_text='Минимальный балл для успешного прохождения теста'
    )
    
    is_active = models.BooleanField('Активность теста', default=True)
    
    created_at = models.DateTimeField('Дата создания', auto_now_add=True)
    updated_at = models.DateTimeField('Дата обновления', auto_now=True)
    
    def __str__(self):
        return self.test_name
    
    def clean(self):
        super().clean()
        
        if not self.test_name or self.test_name.strip() == '':
            raise ValidationError({'test_name': 'Название теста обязательно'})
        
        self.test_name = ' '.join(self.test_name.strip().split())
        
        if self.test_description and len(self.test_description.strip()) > 2000:
            raise ValidationError({
                'test_description': 'Описание не должно превышать 2000 символов'
            })
        
        if self.grading_form == 'points':
            if self.passing_score is None:
                raise ValidationError({
                    'passing_score': 'Для формы оценки "По баллам" необходимо указать проходной балл'
                })
            if self.passing_score < 0:
                raise ValidationError({
                    'passing_score': 'Проходной балл не может быть отрицательным'
                })
        
        elif self.grading_form == 'pass_fail':
            if self.passing_score is not None:
                raise ValidationError({
                    'passing_score': 'Для формы оценки "Зачёт/незачёт" не указывается проходной балл'
                })
        
        if self.max_attempts is not None and self.max_attempts <= 0:
            raise ValidationError({
                'max_attempts': 'Количество попыток должно быть положительным'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'test'
        verbose_name = 'Тест'
        verbose_name_plural = 'Тесты'
        constraints = [
            models.CheckConstraint(
                condition=Q(grading_form__in=['points', 'pass_fail']),
                name='test_grading_form_check'
            ),
            models.CheckConstraint(
                condition=Q(max_attempts__isnull=True) | 
                          Q(max_attempts__gt=0),
                name='test_max_attempts_check'
            ),
        ]

# 16. вопросы
class Question(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, verbose_name='Тест')
    
    question_text = models.TextField('Текст вопроса',
        validators=[
            MinLengthValidator(5, message='Текст вопроса должен содержать минимум 5 символов'),
            MaxLengthValidator(2000, message='Текст вопроса не должен превышать 2000 символов')
        ],
        help_text='Текст вопроса (5-2000 символов)'
    )
    
    answer_type = models.ForeignKey(AnswerType, on_delete=models.CASCADE, verbose_name='Тип ответа')
    
    question_score = models.IntegerField('Балл за вопрос', default=1,
        validators=[
            MinValueValidator(0, message='Балл за вопрос не может быть отрицательным'),
            MaxValueValidator(100, message='Балл за вопрос не должен превышать 100')
        ],
        help_text='Количество баллов за правильный ответ'
    )
    
    correct_text = models.TextField('Правильный ответ', null=True, blank=True,
        validators=[
            MaxLengthValidator(2000, message='Текст ответа не должен превышать 2000 символов')
        ],
        help_text='Правильный ответ для вопросов с текстовым ответом (до 2000 символов)'
    )
    
    question_order = models.IntegerField('Порядок вопроса',
        validators=[
            MinValueValidator(1, message='Порядок вопроса должен быть положительным')
        ],
        help_text='Порядковый номер вопроса в тесте'
    )
    
    def __str__(self):
        return self.question_text[:50] + '...' if len(self.question_text) > 50 else self.question_text
    
    def clean(self):
        super().clean()
        
        if not self.question_text or len(self.question_text.strip()) < 5:
            raise ValidationError({
                'question_text': 'Текст вопроса должен содержать минимум 5 символов'
            })
        
        self.question_text = self.question_text.strip()
        
        if self.question_score < 0:
            raise ValidationError({
                'question_score': 'Балл за вопрос не может быть отрицательным'
            })
        
        if self.question_order <= 0:
            raise ValidationError({
                'question_order': 'Порядок вопроса должен быть положительным'
            })
        
        if self.correct_text and len(self.correct_text.strip()) > 2000:
            raise ValidationError({
                'correct_text': 'Текст ответа не должен превышать 2000 символов'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'question'
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'
        constraints = [
            models.CheckConstraint(
                condition=Q(question_score__gte=0),
                name='question_score_check'
            ),
            models.CheckConstraint(
                condition=Q(question_order__gt=0),
                name='question_order_check'
            ),
            models.UniqueConstraint(
                fields=['test', 'question_order'],
                name='unique_question_order_test'
            ),
        ]

# 17. варианты ответов на вопрос
class ChoiceOption(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, verbose_name='Вопрос'
    )
    
    option_text = models.TextField('Текст варианта',
        validators=[
            MinLengthValidator(1, message='Текст варианта не может быть пустым'),
            MaxLengthValidator(1000, message='Текст варианта не должен превышать 1000 символов')
        ],
        help_text='Текст варианта ответа (1-1000 символов)'
    )
    
    is_correct = models.BooleanField('Правильный',
        help_text='Является ли этот вариант правильным ответом'
    )
    
    def __str__(self):
        return self.option_text[:50] + '...' if len(self.option_text) > 50 else self.option_text
    
    def clean(self):
        super().clean()
        
        if not self.option_text or self.option_text.strip() == '':
            raise ValidationError({
                'option_text': 'Текст варианта не может быть пустым'
            })
        
        self.option_text = self.option_text.strip()
        
        if len(self.option_text) > 1000:
            raise ValidationError({
                'option_text': 'Текст варианта не должен превышать 1000 символов'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'choice_option'
        verbose_name = 'Вариант ответа'
        verbose_name_plural = 'Варианты ответов'

# 18. пользовательские пары соответствий
class MatchingPair(models.Model):
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, verbose_name='Вопрос'
    )
    
    left_text = models.TextField('Левый текст',
        validators=[
            MinLengthValidator(1, message='Текст не может быть пустым!'),
            MaxLengthValidator(500, message='Текст не должен превышать 500 символов!')
        ],
        help_text='Текст слева для сопоставления (1-500 символов)'
    )
    
    right_text = models.TextField('Правый текст',
        validators=[
            MinLengthValidator(1, message='Текст не может быть пустым!'),
            MaxLengthValidator(500, message='Текст не должен превышать 500 символов!')
        ],
        help_text='Текст справа для сопоставления (1-500 символов)'
    )
    
    def __str__(self):
        return f'{self.left_text[:30]} -> {self.right_text[:30]}'
    
    def clean(self):
        super().clean()
        
        if not self.left_text or self.left_text.strip() == '':
            raise ValidationError({
                'left_text': 'Левый текст не может быть пустым'
            })
        
        if not self.right_text or self.right_text.strip() == '':
            raise ValidationError({
                'right_text': 'Правый текст не может быть пустым'
            })
        
        self.left_text = self.left_text.strip()
        self.right_text = self.right_text.strip()
        
        if len(self.left_text) > 500:
            raise ValidationError({
                'left_text': 'Левый текст не должен превышать 500 символов!'
            })
        
        if len(self.right_text) > 500:
            raise ValidationError({
                'right_text': 'Правый текст не должен превышать 500 символов!'
            })
        
        
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'matching_pair'
        verbose_name = 'Пара соответствия'
        verbose_name_plural = 'Пары соответствия'

# 19. ответы пользователей на тест
class UserAnswer(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Пользователь'
    )
    
    question = models.ForeignKey(
        Question, on_delete=models.CASCADE, verbose_name='Вопрос'
    )
    
    answer_text = models.TextField('Текст ответа', null=True, blank=True,
        validators=[
            MaxLengthValidator(2000, message='Текст ответа не должен превышать 2000 символов')
        ],
        help_text='Текстовый ответ пользователя (до 2000 символов)'
    )
    
    answer_date = models.DateTimeField('Дата ответа', default=timezone.now)
    
    attempt_number = models.IntegerField('Номер попытки', default=1,
        validators=[
            MinValueValidator(1, message='Номер попытки должен быть положительным')
        ],
        help_text='Номер попытки прохождения теста'
    )
    
    score = models.IntegerField('Балл', null=True, blank=True,
        validators=[
            MinValueValidator(0, message='Балл не может быть отрицательным!'),
            MaxValueValidator(1000, message='Балл не должен превышать 1000')
        ],
        help_text='Набранный балл за ответ'
    )
    
    def __str__(self):
        return f'{self.user} - {self.question}'
    
    def clean(self):
        super().clean()
        
        if self.attempt_number <= 0:
            raise ValidationError({
                'attempt_number': 'Номер попытки должен быть положительным!'
            })
        
        if self.answer_text and len(self.answer_text.strip()) > 2000:
            raise ValidationError({
                'answer_text': 'Текст ответа не должен превышать 2000 символов!'
            })
        
        if self.score is not None:
            if self.score < 0:
                raise ValidationError({
                    'score': 'Балл не может быть отрицательным'
                })
            if self.score > self.question.question_score:
                raise ValidationError({
                    'score': f'Балл не может превышать максимальный балл за вопрос ({self.question.question_score})!'
                })
        
        if self.answer_date > timezone.now():
            raise ValidationError({
                'answer_date': 'Дата ответа не может быть в будущем'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'user_answer'
        verbose_name = 'Ответ пользователя'
        verbose_name_plural = 'Ответы пользователей'
        unique_together = ('user', 'question', 'attempt_number')
        constraints = [
            models.CheckConstraint(
                condition=Q(attempt_number__gt=0),
                name='user_answer_attempt_number_check'
            ),
            models.CheckConstraint(
                condition=Q(score__isnull=True) | 
                          Q(score__gte=0),
                name='user_answer_score_check'
            ),
        ]

# 20. выбранные варианты ответов пользователей
class UserSelectedChoice(models.Model):
    user_answer = models.ForeignKey(
        UserAnswer, on_delete=models.CASCADE, verbose_name='Ответ пользователя'
    )
    
    choice_option = models.ForeignKey(
        ChoiceOption, on_delete=models.CASCADE, verbose_name='Выбранный вариант'
    )
    
    selected_at = models.DateTimeField('Дата выбора', auto_now_add=True)
    
    def __str__(self):
        return f'{self.user_answer} - {self.choice_option}'
    
    def clean(self):
        super().clean()
        
        if self.choice_option.question != self.user_answer.question:
            raise ValidationError({
                'choice_option': 'Выбранный вариант должен принадлежать тому же вопросу, что и ответ пользователя!'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'user_selected_choice'
        verbose_name = 'Выбранный вариант'
        verbose_name_plural = 'Выбранные варианты'
        unique_together = ('user_answer', 'choice_option')

# 21. пользовательские сопоставления в тестах
class UserMatchingAnswer(models.Model):
    user_answer = models.ForeignKey(
        UserAnswer, on_delete=models.CASCADE, verbose_name='Ответ пользователя'
    )
    
    matching_pair = models.ForeignKey(
        MatchingPair, on_delete=models.CASCADE, verbose_name='Пара соответствия'
    )
    
    user_selected_right_text = models.TextField('Выбранный правый текст',
        validators=[
            MinLengthValidator(1, message='Выбранный текст не может быть пустым'),
            MaxLengthValidator(500, message='Выбранный текст не должен превышать 500 символов')
        ],
        help_text='Текст, выбранный пользователем для сопоставления (1-500 символов)'
    )
    
    selected_at = models.DateTimeField('Дата выбора', auto_now_add=True)
    
    def __str__(self):
        return f'{self.user_answer} - {self.matching_pair}'
    
    def clean(self):
        super().clean()
        
        if self.matching_pair.question != self.user_answer.question:
            raise ValidationError({
                'matching_pair': 'Пара соответствия должна принадлежать тому же вопросу, что и ответ пользователя!'
            })
        
        if not self.user_selected_right_text or self.user_selected_right_text.strip() == '':
            raise ValidationError({
                'user_selected_right_text': 'Выбранный текст не может быть пустым!'
            })
        
        self.user_selected_right_text = self.user_selected_right_text.strip()
        
        if len(self.user_selected_right_text) > 500:
            raise ValidationError({
                'user_selected_right_text': 'Выбранный текст не должен превышать 500 символов!'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'user_matching_answer'
        verbose_name = 'Ответ на сопоставление'
        verbose_name_plural = 'Ответы на сопоставления'
        unique_together = ('user_answer', 'matching_pair')

# 22. результаты тестов 
class TestResult(models.Model):
    user = models.ForeignKey(
        User, on_delete=models.CASCADE, verbose_name='Пользователь'
    )
    
    test = models.ForeignKey(
        Test, on_delete=models.CASCADE, verbose_name='Тест'
    )
    
    completion_date = models.DateTimeField('Дата завершения', default=timezone.now)
    
    final_score = models.IntegerField('Итоговый балл', null=True, blank=True,
        validators=[
            MinValueValidator(0, message='Итоговый балл не может быть отрицательным'),
            MaxValueValidator(10000, message='Итоговый балл не должен превышать 10000')
        ],
        help_text='Общий набранный балл за тест'
    )
    
    is_passed = models.BooleanField('Зачтено', null=True, blank=True,
        help_text='Зачтён ли тест'
    )
    
    attempt_number = models.IntegerField('Номер попытки', default=1,
        validators=[
            MinValueValidator(1, message='Номер попытки должен быть положительным')
        ],
        help_text='Номер попытки прохождения теста'
    )
    
    time_spent = models.IntegerField('Время выполнения (секунды)', null=True, blank=True,
        validators=[
            MinValueValidator(0, message='Время не может быть отрицательным'),
            MaxValueValidator(86400, message='Время не должно превышать 24 часа')
        ],
        help_text='Время, затраченное на выполнение теста в секундах'
    )
    
    def __str__(self):
        return f'{self.user} - {self.test} (попытка {self.attempt_number})'
    
    def clean(self):
        super().clean()
        
        if self.attempt_number <= 0:
            raise ValidationError({
                'attempt_number': 'Номер попытки должен быть положительным'
            })
        
        if self.test.grading_form == 'points':
            if self.final_score is None:
                raise ValidationError({
                    'final_score': 'Для формы оценки "По баллам" необходимо указать итоговый балл за тест!'
                })
            if self.is_passed is not None:
                raise ValidationError({
                    'is_passed': 'Для формы оценки "По баллам" поле "Зачтено" должно быть пустым!'
                })
            if self.final_score < 0:
                raise ValidationError({
                    'final_score': 'Итоговый балл не может быть отрицательным!'
                })
        
        elif self.test.grading_form == 'pass_fail':
            if self.is_passed is None:
                raise ValidationError({
                    'is_passed': 'Для формы оценки "Зачёт/незачёт" необходимо указать, зачтён ли тест или нет!'
                })
            if self.final_score is not None:
                raise ValidationError({
                    'final_score': 'Для формы оценки "Зачёт/незачёт" поле "Итоговый балл" должно быть пустым!'
                })
        
        if self.time_spent is not None:
            if self.time_spent < 0:
                raise ValidationError({
                    'time_spent': 'Время выполнения не может быть отрицательным!'
                })
            if self.time_spent > 86400:
                raise ValidationError({
                    'time_spent': 'Время выполнения не должно превышать 24 часа!'
                })
        
        if self.completion_date > timezone.now():
            raise ValidationError({
                'completion_date': 'Дата завершения не может быть в будущем!'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'test_result'
        verbose_name = 'Результат теста'
        verbose_name_plural = 'Результаты тестов'
        unique_together = ('user', 'test', 'attempt_number')
        constraints = [
            models.CheckConstraint(
                condition=Q(attempt_number__gt=0),
                name='test_result_attempt_number_check'
            ),
            models.CheckConstraint(
                condition=Q(time_spent__isnull=True) | 
                          Q(time_spent__gte=0) & Q(time_spent__lte=86400),
                name='test_result_time_spent_check'
            ),
        ]

# 23. сертификаты 
class Certificate(models.Model):
    user_course = models.OneToOneField(
        UserCourse, on_delete=models.CASCADE, verbose_name='Пользователь на курсе'
    )
    
    certificate_number = models.CharField('Номер сертификата', max_length=50, unique=True,
        validators=[
            MinLengthValidator(5, message='Номер сертификата должен содержать минимум 5 символов'),
            MaxLengthValidator(50, message='Номер сертификата не должен превышать 50 символов'),
            RegexValidator(
                regex=r'^[A-Z0-9\-_]+$',
                message='Номер сертификата может содержать только заглавные латинские буквы, цифры, дефисы и подчёркивания'
            )
        ],
        help_text='Уникальный номер сертификата (5-50 символов)'
    )
    
    issue_date = models.DateField('Дата выдачи', default=timezone.now,
        help_text='Дата выдачи сертификата'
    )
    
    certificate_file_path = models.CharField('Путь к файлу сертификата', max_length=500, null=True, blank=True,
        validators=[
            MaxLengthValidator(500, message='Путь к файлу не должен превышать 500 символов')
        ],
        help_text='Путь к файлу сертификата (до 500 символов)'
    )
    
    def __str__(self):
        return f'Сертификат {self.certificate_number} - {self.user_course.user}'
    
    def clean(self):
        super().clean()
        
        if not self.user_course.status_course:
            raise ValidationError({
                'user_course': 'Сертификат не может быть выдан: курс не завершён'
            })
        
        if not self.user_course.course.has_certificate:
            raise ValidationError({
                'user_course': 'Сертификат не может быть выдан: курс не предусматривает выдачу сертификатов'
            })
        
        if not self.user_course.course.is_completed:
            raise ValidationError({
                'user_course': 'Сертификат не может быть выдан: курс ещё пополняется материалами'
            })
        
        progress = calculate_course_progress(self.user_course.user, self.user_course.course)
        if progress < 100:
            raise ValidationError({
                'user_course': f'Сертификат не может быть выдан: прогресс курса {progress}% (требуется 100%)'
            })
        
        if self.issue_date and self.issue_date > timezone.now().date():
            raise ValidationError({
                'issue_date': 'Дата выдачи сертификата не может быть в будущем'
            })
        
        if self.certificate_file_path and len(self.certificate_file_path) > 500:
            raise ValidationError({
                'certificate_file_path': 'Путь к файлу не должен превышать 500 символов'
            })
    
    def save(self, *args, **kwargs):
        if not self.certificate_number:
            self.certificate_number = self.generate_certificate_number()
        self.full_clean()
        super().save(*args, **kwargs)
    
    def generate_certificate_number(self):
        """функция для генерации уникального номера сертификата"""
        timestamp = timezone.now().strftime("%Y%m%d%H%M%S")
        random_str = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        return f"CERT-{timestamp}-{random_str}"
    
    class Meta:
        db_table = 'certificate'
        verbose_name = 'Сертификат'
        verbose_name_plural = 'Сертификаты'
        constraints = [
            models.CheckConstraint(
                condition=Q(certificate_number__regex=r'^[A-Z0-9\-_]+$'),
                name='certificate_number_format'
            ),
        ]

# 24. файлы сдачи заданий
class AssignmentSubmissionFile(models.Model):
    user_assignment = models.ForeignKey(
        UserPracticalAssignment, on_delete=models.CASCADE, verbose_name='Сдача задания'
    )
    
    file = models.FileField('Файл сдачи', upload_to='assignment_submissions/%Y/%m/%d/',
        validators=[
            FileExtensionValidator(
                allowed_extensions=ALLOWED_EXT
            )
        ],
        help_text='Файл с выполненным заданием'
    )
    
    uploaded_at = models.DateTimeField('Дата загрузки', auto_now_add=True)
    
    file_name = models.CharField('Имя файла', max_length=255,
        help_text='Оригинальное имя файла'
    )
    
    file_size = models.BigIntegerField('Размер файла',
        validators=[
            MinValueValidator(0, message='Размер файла не может быть отрицательным!'),
            MaxValueValidator(100 * 1024 * 1024, message='Размер файла не должен превышать 100 МБ!')
        ],
        help_text='Размер файла в байтах'
    )
    
    description = models.CharField('Описание файла', max_length=500, null=True, blank=True,
        help_text='Краткое описание содержимого файла (до 500 символов)'
    )
    
    def __str__(self):
        return self.file_name
    
    def clean(self):
        super().clean()
        
        if not self.file_name or self.file_name.strip() == '':
            raise ValidationError({
                'file_name': 'Имя файла обязательно'
            })
        
        self.file_name = self.file_name.strip()
        
        if len(self.file_name) > 255:
            raise ValidationError({
                'file_name': 'Имя файла не должно превышать 255 символов'
            })
        
        if self.file_size < 0:
            raise ValidationError({
                'file_size': 'Размер файла не может быть отрицательным'
            })
        
        if self.file_size > 100 * 1024 * 1024:
            raise ValidationError({
                'file_size': 'Файл слишком большой. Максимальный размер: 100 МБ'
            })
        
        if self.description and len(self.description.strip()) > 500:
            raise ValidationError({
                'description': 'Описание не должно превышать 500 символов'
            })
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    class Meta:
        db_table = 'assignment_submission_file'
        verbose_name = 'Файл сдачи задания'
        verbose_name_plural = 'Файлы сдачи заданий'
        constraints = [
            models.CheckConstraint(
                condition=Q(file_size__gte=0),
                name='assignment_file_size_check'
            ),
        ]

# 25. прикрепленные файлы к практическим работам для преподавателя или методиста
class TeacherAssignmentFile(models.Model):
    """данный класс представляет собой модель для хранения файлов методиста или преподавателя к практическим заданиям"""
    
    FILE_TYPE_CHOICES = [
        ('example', 'Пример выполнения работы'),
        ('material', 'Дополнительный материал'),
        ('correction', 'Исправление'),
        ('template', 'Шаблон'),
        ('other', 'Другое'),
    ]
    
    practical_assignment = models.ForeignKey(PracticalAssignment, on_delete=models.CASCADE, verbose_name='Практическое задание', related_name='teacher_files')
    
    file_path = models.CharField('Путь к файлу', max_length=500,
        help_text='Путь к файлу'
    )
    
    original_filename = models.CharField('Имя файла', max_length=255)
    
    file_type = models.CharField('Тип файла', max_length=20, 
        choices=FILE_TYPE_CHOICES, default='material'
    )
    
    uploaded_by = models.ForeignKey(
        User, 
        on_delete=models.SET_NULL, 
        null=True, 
        verbose_name='Загрузил',
        limit_choices_to=models.Q(role__role_name__in=['преподаватель', 'методист'])
    )
    
    uploaded_at = models.DateTimeField('Дата загрузки', auto_now_add=True)
    
    file_size = models.BigIntegerField('Размер файла',
        validators=[MinValueValidator(1)]
    )
    
    is_active = models.BooleanField('Активен', default=True)
    
    def __str__(self):
        return f'{self.original_filename} - {self.practical_assignment}'
    
    @property
    def file_extension(self):
        return os.path.splitext(self.original_filename)[1].lower().lstrip('.')
    
    @property
    def file_size_mb(self):
        """свойство для перевода размера файла в мегабайты"""
        return round(self.file_size / (1024 * 1024), 2)
    
    def clean(self):
        super().clean()
        ext = self.file_extension
        dangerous_ext = {'exe', 'bat', 'sh', 'msi', 'jar', 'apk'}
        
        if ext in dangerous_ext:
            raise ValidationError(f'Расширение .{ext} запрещено для загрузки в систему!')
        
        if ext not in ALLOWED_EXT:
            raise ValidationError(f'Расширение .{ext} не поддерживается!')
        
        if self.file_size > 100 * 1024 * 1024:  
            raise ValidationError('Максимальный размер файла: 100 МБ!')
        
        if self.uploaded_by and not self.uploaded_by.is_teacher_or_methodist:
            raise ValidationError('Файлы могут загружать только преподаватели или методисты!')
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def delete(self, *args, **kwargs):
        if self.file_path and default_storage.exists(self.file_path):
            default_storage.delete(self.file_path)
        super().delete(*args, **kwargs)
    
    class Meta:
        db_table = 'teacher_assignment_file'
        verbose_name = 'Файл преподавателя к заданию'
        verbose_name_plural = 'Файлы преподавателей к заданиям'
        ordering = ['-uploaded_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(file_type__in=['example', 'material', 'correction', 'template', 'other']),
                name='teacher_file_type_check'
            ),
        ]

# 26. коды восстановления
class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Пользователь')

    code = models.CharField('Код подтверждения', max_length=6,
        validators=[
            MinLengthValidator(6, message='Код должен содержать 6 символов!'),
            MaxLengthValidator(6, message='Код должен содержать 6 символов!'),
            RegexValidator(
                regex=r'^[0-9]+$',
                message='Код должен содержать только цифры'
            )
        ],
        help_text='6-значный код с почты для восстановления пароля'
    )
    
    created_at = models.DateTimeField('Время создания', auto_now_add=True) 
    is_used = models.BooleanField('Использован', default=False)
    
    def __str__(self):
        return f"{self.user.email} - {self.code}"
    
    def clean(self):
        super().clean()
        
        if len(self.code) != 6: raise ValidationError({'code': 'Код должен содержать ровно 6 цифр'})
        if not self.code.isdigit(): raise ValidationError({'code': 'Код должен содержать только цифры'})
    
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
    
    def is_valid(self):
        return not self.is_used and (timezone.now() - self.created_at) < timedelta(minutes=15)
    
    def mark_code_used(self):
        self.is_used = True
        self.save()
    
    @classmethod
    def generate_code(cls):
        return ''.join(random.choices(string.digits, k=6))
    
    class Meta:
        db_table = 'password_reset_code'
        verbose_name = 'Код восстановления пароля'
        verbose_name_plural = 'Коды восстановления пароля'
        constraints = [
            models.CheckConstraint(
                condition=Q(code__regex=r'^[0-9]{6}$'),
                name='password_reset_code_format_check'
            ),
        ]

# представления 
class ViewCoursePracticalAssignments(models.Model):
    course_id = models.BigIntegerField('ID курса')
    course_name = models.CharField('Название курса', max_length=255)
    lecture_id = models.BigIntegerField('ID лекции')  
    lecture_name = models.CharField('Название лекции', max_length=255)
    lecture_order = models.IntegerField('Порядок лекции')
    practical_assignment_id = models.BigIntegerField('ID задания', primary_key=True)  
    practical_assignment_name = models.CharField('Название задания', max_length=255)
    practical_assignment_description = models.TextField('Описание задания')
    assignment_document_path = models.CharField('Путь к документу', max_length=255, null=True, blank=True)
    assignment_criteria = models.TextField('Критерии оценки', null=True, blank=True)
    assignment_deadline = models.DateTimeField('Срок сдачи')
    grading_type = models.CharField('Тип оценки', max_length=20)
    max_score = models.IntegerField('Максимальный балл', null=True, blank=True)
    is_active = models.BooleanField('Активно')

    class Meta:
        managed = False
        db_table = 'view_course_practical_assignments'
        verbose_name = 'Практическая работа курса'
        verbose_name_plural = 'Практические работы курсов'

class ViewCourseLectures(models.Model):
    course_id = models.BigIntegerField('ID курса') 
    course_name = models.CharField('Название курса', max_length=255)
    lecture_id = models.BigIntegerField('ID лекции', primary_key=True) 
    lecture_name = models.CharField('Название лекции', max_length=255)
    lecture_content = models.TextField('Содержание лекции')
    lecture_document_path = models.CharField('Путь к документу', max_length=255, null=True, blank=True)
    lecture_order = models.IntegerField('Порядок лекции')
    is_active = models.BooleanField('Активно')

    class Meta:
        managed = False
        db_table = 'view_course_lectures'
        verbose_name = 'Лекция курса'
        verbose_name_plural = 'Лекции курсов'

class ViewCourseTests(models.Model):
    course_id = models.BigIntegerField('ID курса')  
    course_name = models.CharField('Название курса', max_length=255)
    lecture_id = models.BigIntegerField('ID лекции') 
    lecture_name = models.CharField('Название лекции', max_length=255)
    lecture_order = models.IntegerField('Порядок лекции')
    test_id = models.BigIntegerField('ID теста', primary_key=True)  
    test_name = models.CharField('Название теста', max_length=255)
    test_description = models.TextField('Описание теста', null=True, blank=True)
    is_final = models.BooleanField('Финальный тест')
    max_attempts = models.IntegerField('Максимум попыток', null=True, blank=True)
    grading_form = models.CharField('Форма оценки', max_length=20)
    passing_score = models.IntegerField('Проходной балл', null=True, blank=True)
    is_active = models.BooleanField('Активно')

    class Meta:
        managed = False
        db_table = 'view_course_tests'
        verbose_name = 'Тест курса'
        verbose_name_plural = 'Тесты курсов'

class ViewAssignmentSubmissions(models.Model):
    submission_id = models.BigIntegerField('ID набора прикрепленных файлов', primary_key=True)
    user_id = models.BigIntegerField('ID пользователя')
    user_name = models.CharField('Имя пользователя', max_length=255)
    practical_assignment_id = models.BigIntegerField('ID задания')
    practical_assignment_name = models.CharField('Название задания', max_length=255)
    lecture_name = models.CharField('Название лекции', max_length=255)
    course_name = models.CharField('Название курса', max_length=255)
    submission_date = models.DateTimeField('Дата сдачи', null=True, blank=True)
    attempt_number = models.IntegerField('Номер попытки')
    status = models.CharField('Статус', max_length=255)
    comment = models.TextField('Комментарий', null=True, blank=True)
    file_count = models.IntegerField('Количество файлов')
    total_size = models.BigIntegerField('Общий размер')

    class Meta:
        managed = False
        db_table = 'view_assignment_submissions'
        verbose_name = 'Сданная практическая работа'
        verbose_name_plural = 'Сданные практические работы'