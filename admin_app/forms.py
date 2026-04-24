from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone
from unireax_main.models import *
import re

class DateInput(forms.DateInput):
    input_type = 'date'


class DateTimeInput(forms.DateTimeInput):
    input_type = 'datetime-local'

class CourseCategoryForm(forms.ModelForm):
    """Форма для создания и редактирования категорий курсов"""
    class Meta:
        model = CourseCategory
        fields = ['course_category_name']
        widgets = {
            'course_category_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Программирование, Дизайн, Маркетинг'
            })
        }
        labels = {
            'course_category_name': 'Название категории'
        }

    def clean_course_category_name(self):
        name = self.cleaned_data.get('course_category_name')
        if name:
            name = ' '.join(name.strip().split())
            if len(name) < 2:
                raise ValidationError('Название категории должно содержать минимум 2 символа')
            if not re.match(r'^[а-яА-Яa-zA-Z0-9_\- ]+$', name):
                raise ValidationError('Разрешены только буквы, цифры, пробелы, дефисы и подчёркивания')
            if CourseCategory.objects.filter(course_category_name__iexact=name).exists():
                raise ValidationError('Категория с таким названием уже существует')
        return name

class UserCreateForm(forms.ModelForm):
    """Форма для создания пользователя администратором"""
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={'class': 'form-control'}),
        help_text='Минимум 8 символов'
    )
    password_confirm = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'patronymic',
            'email', 'role', 'position', 'educational_institution',
            'certificate_file', 'is_light_theme', 'is_verified', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'patronymic': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'educational_institution': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_light_theme': forms.RadioSelect(
                choices=[(True, 'Светлая тема'), (False, 'Тёмная тема')],
                attrs={'class': 'form-radio'}
            ),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'username': 'Имя пользователя',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'patronymic': 'Отчество',
            'email': 'Электронная почта',
            'role': 'Роль',
            'position': 'Должность',
            'educational_institution': 'Учебное заведение',
            'certificate_file': 'Справка/документ об образовании',
            'is_light_theme': 'Тема интерфейса',
            'is_verified': 'Подтверждён',
            'is_active': 'Активен',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = Role.objects.all().order_by('role_name')
        self.fields['role'].empty_label = "--- Выберите роль ---"

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            if not re.match(r'^[\w.@-]+$', username):
                raise ValidationError('Имя пользователя может содержать только буквы, цифры и символы: @ . - _')
            if User.objects.filter(username=username).exists():
                raise ValidationError('Пользователь с таким именем уже существует')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            if User.objects.filter(email=email).exists():
                raise ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if first_name:
            if not re.match(r'^[а-яА-Яa-zA-Z\- ]+$', first_name):
                raise ValidationError('Имя может содержать только буквы, дефисы и пробелы')
            if len(first_name) < 2:
                raise ValidationError('Имя должно содержать минимум 2 символа')
        return first_name

    def clean_last_name(self):
        last_name = self.cleaned_data.get('last_name')
        if last_name:
            if not re.match(r'^[а-яА-Яa-zA-Z\- ]+$', last_name):
                raise ValidationError('Фамилия может содержать только буквы, дефисы и пробелы')
            if len(last_name) < 1:
                raise ValidationError('Фамилия должна содержать минимум 1 символ')
        return last_name

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get('password')
        password_confirm = cleaned_data.get('password_confirm')
        role = cleaned_data.get('role')
        position = cleaned_data.get('position')
        educational_institution = cleaned_data.get('educational_institution')
        certificate_file = cleaned_data.get('certificate_file')

        if password and password_confirm and password != password_confirm:
            raise ValidationError({'password_confirm': 'Пароли не совпадают'})

        if password and len(password) < 8:
            raise ValidationError({'password': 'Пароль должен содержать минимум 8 символов'})

        if role:
            role_name = role.role_name.lower() if role.role_name else ''
            if role_name in ['методист', 'преподаватель']:
                if not position:
                    raise ValidationError({'position': 'Поле "Должность" обязательно для методистов и преподавателей'})
                if not educational_institution:
                    raise ValidationError({'educational_institution': 'Поле "Учебное заведение" обязательно для методистов и преподавателей'})
                if not certificate_file:
                    raise ValidationError({'certificate_file': 'Справка с места работы обязательна для методистов и преподавателей'})

        return cleaned_data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user


class UserUpdateForm(forms.ModelForm):
    """Форма для редактирования пользователя"""
    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'patronymic',
            'email', 'role', 'position', 'educational_institution',
            'certificate_file', 'is_light_theme', 'is_verified', 'is_active'
        ]
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control'}),
            'patronymic': forms.TextInput(attrs={'class': 'form-control'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'position': forms.TextInput(attrs={'class': 'form-control'}),
            'educational_institution': forms.TextInput(attrs={'class': 'form-control'}),
            'certificate_file': forms.FileInput(attrs={'class': 'form-control'}),
            'is_light_theme': forms.RadioSelect(
                choices=[(True, 'Светлая тема'), (False, 'Тёмная тема')],
                attrs={'class': 'form-radio'}
            ),
            'is_verified': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'username': 'Имя пользователя',
            'first_name': 'Имя',
            'last_name': 'Фамилия',
            'patronymic': 'Отчество',
            'email': 'Электронная почта',
            'role': 'Роль',
            'position': 'Должность',
            'educational_institution': 'Учебное заведение',
            'certificate_file': 'Справка/документ об образовании',
            'is_light_theme': 'Тема интерфейса',
            'is_verified': 'Подтверждён',
            'is_active': 'Активен',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['role'].queryset = Role.objects.all().order_by('role_name')
        self.fields['role'].empty_label = "--- Выберите роль ---"

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if username:
            if not re.match(r'^[\w.@-]+$', username):
                raise ValidationError('Имя пользователя может содержать только буквы, цифры и символы: @ . - _')
            if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
                raise ValidationError('Пользователь с таким именем уже существует')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email:
            email = email.strip().lower()
            if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
                raise ValidationError('Пользователь с таким email уже существует')
        return email

    def clean(self):
        cleaned_data = super().clean()
        role = cleaned_data.get('role')
        position = cleaned_data.get('position')
        educational_institution = cleaned_data.get('educational_institution')

        if role:
            role_name = role.role_name.lower() if role.role_name else ''
            if role_name in ['методист', 'преподаватель']:
                if not position:
                    raise ValidationError({'position': 'Поле "Должность" обязательно для методистов и преподавателей'})
                if not educational_institution:
                    raise ValidationError({'educational_institution': 'Поле "Учебное заведение" обязательно для методистов и преподавателей'})

        return cleaned_data

class CourseForm(forms.ModelForm):
    """Форма для создания и редактирования курсов"""
    
    class Meta:
        model = Course
        fields = [
            'course_name', 'course_description', 'course_price',
            'course_category', 'course_type', 'course_photo_path',
            'has_certificate', 'course_max_places', 'course_hours',
            'is_completed', 'code_link', 'is_active', 'created_by'
        ]
        widgets = {
            'course_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название курса'
            }),
            'course_description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Краткое описание курса (до 300 символов)'
            }),
            'course_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '0.00',
                'step': '0.01'
            }),
            'course_category': forms.Select(attrs={'class': 'form-control'}),
            'course_type': forms.Select(attrs={'class': 'form-control'}),
            'course_photo_path': forms.FileInput(attrs={'class': 'form-control'}),
            'has_certificate': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'course_max_places': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Максимум мест (необязательно)'
            }),
            'course_hours': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Количество часов'
            }),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'code_link': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'created_by': forms.Select(attrs={'class': 'form-control'}),
        }
        labels = {
            'course_name': 'Название курса',
            'course_description': 'Описание курса',
            'course_price': 'Цена (₽)',
            'course_category': 'Категория',
            'course_type': 'Тип курса',
            'course_photo_path': 'Изображение курса',
            'has_certificate': 'Выдавать сертификат',
            'course_max_places': 'Максимальное количество мест',
            'course_hours': 'Длительность (часов)',
            'is_completed': 'Курс полностью наполнен материалами',
            'code_link': 'Ссылка на видео-встречу',
            'is_active': 'Курс активен',
            'created_by': 'Создатель курса',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course_category'].queryset = CourseCategory.objects.all().order_by('course_category_name')
        self.fields['course_category'].empty_label = "--- Выберите категорию ---"
        
        self.fields['course_type'].queryset = CourseType.objects.all().order_by('course_type_name')
        self.fields['course_type'].empty_label = "--- Выберите тип курса ---"
        
        self.fields['created_by'].queryset = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        self.fields['created_by'].empty_label = "--- Выберите создателя ---"

    def clean_course_name(self):
        name = self.cleaned_data.get('course_name')
        if name:
            name = ' '.join(name.strip().split())
            if len(name) < 3:
                raise ValidationError('Название курса должно содержать минимум 3 символа')
            if not re.match(r'^[а-яА-Яa-zA-Z0-9_\- ,.!?"\'():; ]+$', name):
                raise ValidationError('Недопустимые символы в названии курса')
        return name

    def clean_course_price(self):
        price = self.cleaned_data.get('course_price')
        if price is not None and price < 0:
            raise ValidationError('Цена не может быть отрицательной')
        return price

    def clean_course_max_places(self):
        places = self.cleaned_data.get('course_max_places')
        if places is not None:
            if places < 1:
                raise ValidationError('Количество мест должно быть положительным')
            if places > 1000:
                raise ValidationError('Максимум 1000 мест')
        return places

    def clean_course_hours(self):
        hours = self.cleaned_data.get('course_hours')
        if hours:
            if hours < 1:
                raise ValidationError('Курс должен длиться минимум 1 час')
            if hours > 3000:
                raise ValidationError('Слишком большое количество часов')
        return hours

class UserCourseForm(forms.ModelForm):
    """Форма для записи пользователей на курсы"""
    
    class Meta:
        model = UserCourse
        fields = [
            'user', 'course', 'registration_date', 
            'status_course', 'payment_date', 'completion_date',
            'course_price', 'is_active', 'payment_id'
        ]
        widgets = {
            'user': forms.Select(attrs={'class': 'form-control'}),
            'course': forms.Select(attrs={'class': 'form-control'}),
            'registration_date': DateInput(attrs={'class': 'form-control'}),
            'status_course': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_date': DateTimeInput(attrs={'class': 'form-control'}),
            'completion_date': DateInput(attrs={'class': 'form-control'}),
            'course_price': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'placeholder': 'Цена на момент покупки'
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'payment_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ID платежа в ЮKassa'
            }),
        }
        labels = {
            'user': 'Пользователь (слушатель)',
            'course': 'Курс',
            'registration_date': 'Дата регистрации',
            'status_course': 'Курс завершён',
            'payment_date': 'Дата оплаты',
            'completion_date': 'Дата завершения',
            'course_price': 'Цена покупки',
            'is_active': 'Активен на курсе',
            'payment_id': 'ID платежа',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['user'].queryset = User.objects.filter(is_active=True).order_by('last_name', 'first_name')
        self.fields['user'].empty_label = "--- Выберите пользователя ---"
        
        self.fields['course'].queryset = Course.objects.filter(is_active=True).order_by('course_name')
        self.fields['course'].empty_label = "--- Выберите курс ---"

    def clean(self):
        cleaned_data = super().clean()
        user = cleaned_data.get('user')
        course = cleaned_data.get('course')
        status_course = cleaned_data.get('status_course')
        completion_date = cleaned_data.get('completion_date')
        registration_date = cleaned_data.get('registration_date')
        payment_date = cleaned_data.get('payment_date')
        course_price = cleaned_data.get('course_price')

        if user and course:
            if not self.instance.pk:
                if UserCourse.objects.filter(user=user, course=course).exists():
                    raise ValidationError('Этот пользователь уже записан на данный курс')
            else:
                if UserCourse.objects.filter(user=user, course=course)\
                                     .exclude(pk=self.instance.pk)\
                                     .exists():
                    raise ValidationError('Этот пользователь уже записан на данный курс')

        if completion_date and registration_date and completion_date < registration_date:
            raise ValidationError({'completion_date': 'Дата завершения не может быть раньше даты регистрации'})

        if status_course and not completion_date:
            raise ValidationError({'completion_date': 'При завершении курса должна быть указана дата завершения'})

        if payment_date and payment_date > timezone.now():
            raise ValidationError({'payment_date': 'Дата оплаты не может быть в будущем'})

        if course_price is not None and course_price < 0:
            raise ValidationError({'course_price': 'Цена не может быть отрицательной'})

        return cleaned_data

class CourseTeacherForm(forms.ModelForm):
    """Форма для назначения преподавателей/методистов на курсы"""
    
    class Meta:
        model = CourseTeacher
        fields = ['course', 'teacher', 'start_date', 'is_active']
        widgets = {
            'course': forms.Select(attrs={'class': 'form-control'}),
            'teacher': forms.Select(attrs={'class': 'form-control'}),
            'start_date': DateInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'course': 'Курс',
            'teacher': 'Сотрудник (преподаватель/методист)',
            'start_date': 'Дата начала работы',
            'is_active': 'Активен на курсе',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course'].queryset = Course.objects.filter(is_active=True).order_by('course_name')
        self.fields['course'].empty_label = "--- Выберите курс ---"
        
        self.fields['teacher'].queryset = User.objects.filter(
            is_active=True,
            role__role_name__in=['преподаватель', 'методист']
        ).order_by('last_name', 'first_name')
        self.fields['teacher'].empty_label = "--- Выберите сотрудника ---"

    def clean(self):
        cleaned_data = super().clean()
        course = cleaned_data.get('course')
        teacher = cleaned_data.get('teacher')
        start_date = cleaned_data.get('start_date')

        if course and teacher:
            if not self.instance.pk:
                if CourseTeacher.objects.filter(course=course, teacher=teacher).exists():
                    raise ValidationError('Этот сотрудник уже назначен на данный курс')
            else:
                if CourseTeacher.objects.filter(course=course, teacher=teacher)\
                                       .exclude(pk=self.instance.pk)\
                                       .exists():
                    raise ValidationError('Этот сотрудник уже назначен на данный курс')

        if start_date and start_date < timezone.now().date():
            raise ValidationError({'start_date': 'Дата начала не может быть в прошлом'})

        if teacher and teacher.role:
            role_name = teacher.role.role_name.lower() if teacher.role.role_name else ''
            if role_name not in ['преподаватель', 'методист']:
                raise ValidationError({'teacher': 'Назначить можно только преподавателя или методиста'})

        return cleaned_data

class UserFilterForm(forms.Form):
    """Форма для фильтрации пользователей"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по имени, email или логину...'
        })
    )
    role = forms.ModelChoiceField(
        required=False,
        queryset=Role.objects.all().order_by('role_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Роль',
        empty_label="Все роли"
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', 'Все'), ('true', 'Активные'), ('false', 'Неактивные')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    is_verified = forms.ChoiceField(
        required=False,
        choices=[('', 'Все'), ('true', 'Подтверждённые'), ('false', 'Неподтверждённые')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


class CourseFilterForm(forms.Form):
    """Форма для фильтрации курсов"""
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Поиск по названию...'
        })
    )
    course_category = forms.ModelChoiceField(
        required=False,
        queryset=CourseCategory.objects.all().order_by('course_category_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Категория',
        empty_label="Все категории"
    )
    course_type = forms.ModelChoiceField(
        required=False,
        queryset=CourseType.objects.all().order_by('course_type_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Тип курса',
        empty_label="Все типы"
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', 'Все'), ('true', 'Активные'), ('false', 'Неактивные')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    has_certificate = forms.ChoiceField(
        required=False,
        choices=[('', 'Все'), ('true', 'С сертификатом'), ('false', 'Без сертификата')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class UserCourseFilterForm(forms.Form):
    """Форма для фильтрации записей пользователей на курсы"""
    user = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(is_active=True).order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Пользователь',
        empty_label="Все пользователи"
    )
    course = forms.ModelChoiceField(
        required=False,
        queryset=Course.objects.filter(is_active=True).order_by('course_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Курс',
        empty_label="Все курсы"
    )
    status_course = forms.ChoiceField(
        required=False,
        choices=[('', 'Все'), ('true', 'Завершён'), ('false', 'Не завершён')],
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Статус'
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', 'Все'), ('true', 'Активен'), ('false', 'Неактивен')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )

class CourseTeacherFilterForm(forms.Form):
    """Форма для фильтрации назначений преподавателей"""
    course = forms.ModelChoiceField(
        required=False,
        queryset=Course.objects.filter(is_active=True).order_by('course_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Курс',
        empty_label="Все курсы"
    )
    teacher = forms.ModelChoiceField(
        required=False,
        queryset=User.objects.filter(
            is_active=True,
            role__role_name__in=['преподаватель', 'методист']
        ).order_by('last_name', 'first_name'),
        widget=forms.Select(attrs={'class': 'form-control'}),
        label='Сотрудник',
        empty_label="Все сотрудники"
    )
    is_active = forms.ChoiceField(
        required=False,
        choices=[('', 'Все'), ('true', 'Активен'), ('false', 'Неактивен')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )


