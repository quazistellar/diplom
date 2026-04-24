from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import User
from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError
from .models import User
import re
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox
from django.contrib.auth.forms import UserCreationForm
from django.core.validators import FileExtensionValidator
from django.contrib.auth import get_user_model
from .models import Role

User = get_user_model()

class UserAdminForm(forms.ModelForm):
    password = forms.CharField(
        label="Пароль",
        widget=forms.PasswordInput(attrs={'autocomplete': 'new-password'}),
        required=False,
        strip=False,
        help_text="Введите пароль или оставьте пустым, чтобы сохранить текущий."
    )

    class Meta:
        model = User
        fields = '__all__'
        widgets = {
            'password': forms.PasswordInput(render_value=True),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['password'].required = False
            self.fields['password'].help_text = "Оставьте пустым для сохранения текущего пароля. Введите новый пароль для изменения."
    
    def clean_password(self):
        password = self.cleaned_data.get("password")
        
        if not password and self.instance and self.instance.pk:
            return None  
        
        if password:
            try:
                validate_password(password, self.instance)
            except ValidationError as e:
                raise forms.ValidationError(" ".join([error.message for error in e.error_list]))
        
        return password
    
    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password")
        
        if password:
            user.set_password(password)
        elif not user.pk:
            raise ValueError("Пароль обязателен для нового пользователя")
        
        if commit:
            user.save()
            self.save_m2m()  
        
        return user

from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.core.exceptions import ValidationError


class ProfilePasswordChangeForm(PasswordChangeForm):
    """Форма для смены пароля в профиле"""
    
    old_password = forms.CharField(
        label='Текущий пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите текущий пароль'
        })
    )
    
    new_password1 = forms.CharField(
        label='Новый пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите новый пароль'
        })
    )
    
    new_password2 = forms.CharField(
        label='Подтверждение пароля',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Подтвердите новый пароль'
        })
    )
    
    def clean_new_password1(self):
        """Проверка пароля на минимальную длину"""
        password = self.cleaned_data.get('new_password1')
        if password and len(password) < 8:
            raise ValidationError('Пароль должен содержать минимум 8 символов')
        return password
    
    def clean(self):
        """Дополнительная проверка совпадения паролей"""
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise ValidationError('Новый пароль и подтверждение не совпадают')
        
        return cleaned_data
    
class ProfilePasswordChangeForm(PasswordChangeForm):
    """Форма для смены пароля"""
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['old_password'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Введите текущий пароль'})
        self.fields['new_password1'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Введите новый пароль'})
        self.fields['new_password2'].widget.attrs.update({'class': 'form-control', 'placeholder': 'Подтвердите новый пароль'})


class ProfileInfoForm(forms.ModelForm):
    """Форма для редактирования личной информации"""
    username = forms.CharField(
        label='Имя пользователя',
        max_length=150,
        required=True,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя пользователя'})
    )
    email = forms.EmailField(
        label='Электронная почта',
        required=True,
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Введите email'})
    )
    first_name = forms.CharField(
        label='Имя',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите имя'})
    )
    last_name = forms.CharField(
        label='Фамилия',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите фамилию'})
    )
    patronymic = forms.CharField(
        label='Отчество',
        required=False,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите отчество'})
    )
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'patronymic']
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = False
        self.fields['last_name'].required = False
        self.fields['patronymic'].required = False
    
    def clean_username(self):
        """Проверка уникальности username"""
        username = self.cleaned_data.get('username')
        if not username:
            raise ValidationError('Имя пользователя обязательно для заполнения')
        
        if not re.match(r'^[\w.@+-]+$', username):
            raise ValidationError('Имя пользователя может содержать только буквы, цифры и символы @/./+/-/_')

        if self.instance and self.instance.pk:
            if User.objects.exclude(pk=self.instance.pk).filter(username=username).exists():
                raise ValidationError('Пользователь с таким именем уже существует')
        else:
            if User.objects.filter(username=username).exists():
                raise ValidationError('Пользователь с таким именем уже существует')
        
        return username
    
    def clean_email(self):
        """Проверка уникальности email"""
        email = self.cleaned_data.get('email')
        if not email:
            raise ValidationError('Email обязателен для заполнения')
    
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationError('Введите корректный email адрес')
        
        if self.instance and self.instance.pk:
            if User.objects.exclude(pk=self.instance.pk).filter(email=email).exists():
                raise ValidationError('Пользователь с таким email уже существует')
        else:
            if User.objects.filter(email=email).exists():
                raise ValidationError('Пользователь с таким email уже существует')
        
        return email
    
    def clean_first_name(self):
        """Проверка имени"""
        first_name = self.cleaned_data.get('first_name')
        if first_name and len(first_name) > 150:
            raise ValidationError('Имя не может быть длиннее 150 символов')
        return first_name
    
    def clean_last_name(self):
        """Проверка фамилии"""
        last_name = self.cleaned_data.get('last_name')
        if last_name and len(last_name) > 150:
            raise ValidationError('Фамилия не может быть длиннее 150 символов')
        return last_name
    
    def clean_patronymic(self):
        """Проверка отчества"""
        patronymic = self.cleaned_data.get('patronymic')
        if patronymic and len(patronymic) > 150:
            raise ValidationError('Отчество не может быть длиннее 150 символов')
        return patronymic
    

class FeedbackForm(forms.Form):
    name = forms.CharField(max_length=100, required=True)
    email = forms.EmailField(required=True)
    subject = forms.CharField(max_length=200, required=False)
    message = forms.CharField(widget=forms.Textarea, required=True)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox)


class ListenerRegistrationForm(UserCreationForm):
    """Форма регистрации слушателя курсов"""
    
    username = forms.CharField(
        max_length=150, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'})
    )
    first_name = forms.CharField(
        max_length=35, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'})
    )
    last_name = forms.CharField(
        max_length=35, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'})
    )
    patronymic = forms.CharField(
        max_length=35, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Отчество (если его нет - оставьте поле пустым)'})
    )
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Почта'})
    )
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'})
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Подтвердите пароль'})
    )
    accept_policies = forms.BooleanField(
        required=True, 
        error_messages={'required': 'Необходимо согласиться с политиками'},
        widget=forms.CheckboxInput(attrs={'id': 'accept_policies'})
    )

    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'patronymic', 'email', 'password1', 'password2', 'accept_policies']

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают')
        return password2



class TeacherMethodistRegistrationForm(UserCreationForm):
    """Форма регистрации преподавателя/методиста"""
    
    username = forms.CharField(
        max_length=150, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя пользователя'})
    )
    first_name = forms.CharField(
        max_length=35, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Имя'})
    )
    last_name = forms.CharField(
        max_length=35, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Фамилия'})
    )
    patronymic = forms.CharField(
        max_length=35, 
        required=False, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Отчество (если его нет - оставьте поле пустым)'})
    )
    email = forms.EmailField(
        required=True, 
        widget=forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Почта'})
    )
    
    role_choice = forms.ChoiceField(
        choices=[
            ('teacher', 'Преподаватель'),
            ('methodist', 'Методист'),
        ],
        required=True,
        widget=forms.RadioSelect(attrs={'class': 'role-radio'}),
        error_messages={'required': 'Пожалуйста, выберите одну из ролей'}
    )
    
    position = forms.CharField(
        max_length=100, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Должность по месту работы'})
    )
    
    educational_institution = forms.CharField(
        max_length=100, 
        required=True, 
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Учебное заведение, в котором вы работаете'})
    )
    
    certificat_from_the_place_of_work_path = forms.FileField(
        required=True,
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        validators=[FileExtensionValidator(allowed_extensions=['jpg', 'jpeg', 'png', 'pdf'])],
        help_text='Форматы: JPG, PNG, PDF. Максимальный размер: 10 МБ'
    )
    
    password1 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Пароль'})
    )
    password2 = forms.CharField(
        required=True,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Подтвердите пароль'})
    )
    
    accept_policies = forms.BooleanField(
        required=True, 
        error_messages={'required': 'Необходимо согласиться с политиками'},
        widget=forms.CheckboxInput(attrs={'id': 'accept_policies'})
    )

    class Meta:
        model = User
        fields = [
            'username', 'first_name', 'last_name', 'patronymic', 'email', 
            'password1', 'password2', 'role_choice', 'position', 
            'educational_institution', 'certificat_from_the_place_of_work_path', 'accept_policies'
        ]

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError('Пользователь с таким именем уже существует')
        return username

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError('Пользователь с таким email уже существует')
        return email

    def clean_password2(self):
        password1 = self.cleaned_data.get('password1')
        password2 = self.cleaned_data.get('password2')
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают')
        return password2

    def clean_certificat_from_the_place_of_work_path(self):
        file = self.cleaned_data.get('certificat_from_the_place_of_work_path')
        if file:
            if file.size > 10 * 1024 * 1024:
                raise forms.ValidationError('Файл слишком большой. Максимальный размер: 10 МБ')
        return file


class PasswordResetRequestForm(forms.Form):
    """Форма для запроса кода восстановления"""
    email = forms.EmailField(
        max_length=254,
        widget=forms.EmailInput(attrs={
            'class': 'auth-input',
            'placeholder': 'example@mail.ru',
            'autofocus': 'autofocus'
        }),
        label='Email'
    )


class PasswordResetVerifyForm(forms.Form):
    """Форма для проверки кода восстановления"""
    code = forms.CharField(
        max_length=6,
        min_length=6,
        widget=forms.TextInput(attrs={
            'class': 'otp-input',
            'maxlength': '1',
            'pattern': '[0-9]',
            'inputmode': 'numeric'
        }),
        label='Код подтверждения'
    )


class PasswordResetConfirmForm(forms.Form):
    """Форма для установки нового пароля"""
    new_password1 = forms.CharField(
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Новый пароль'
        }),
        label='Новый пароль'
    )
    new_password2 = forms.CharField(
        min_length=8,
        max_length=128,
        widget=forms.PasswordInput(attrs={
            'class': 'auth-input',
            'placeholder': 'Повторите пароль'
        }),
        label='Подтверждение пароля'
    )
    
    def clean_new_password1(self):
        password = self.cleaned_data.get('new_password1')
        
        if len(password) < 8:
            raise forms.ValidationError('Пароль должен содержать минимум 8 символов')
        
        if not re.search(r'[A-Z]', password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну заглавную букву (A-Z)')
        
        if not re.search(r'[a-z]', password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну строчную букву (a-z)')
        
        if not re.search(r'\d', password):
            raise forms.ValidationError('Пароль должен содержать хотя бы одну цифру (0-9)')
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:\'",.<>/?\\|`~]', password):
            raise forms.ValidationError('Пароль должен содержать хотя бы один специальный символ (!@#$%^&* и т.д.)')
        
        return password
    
    def clean(self):
        cleaned_data = super().clean()
        password1 = cleaned_data.get('new_password1')
        password2 = cleaned_data.get('new_password2')
        
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError('Пароли не совпадают')
        
        return cleaned_data