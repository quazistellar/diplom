from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.conf import settings
import glob
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import HttpResponseForbidden, Http404, FileResponse
from .utils.additional_function import calculate_course_completion
from .models import Lecture, PracticalAssignment, Test, User, Course, CourseCategory, CourseType, Review, UserCourse
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.core.mail import send_mail 
from django.views.decorators.http import require_POST
import json
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils import timezone
import pytz
from .forms import FeedbackForm 
from django.shortcuts import redirect, get_object_or_404
from .models import Course, Review
from datetime import timedelta
from .models import LoginAttempt  
from .forms import ListenerRegistrationForm, TeacherMethodistRegistrationForm
import random
import string
from .forms import ListenerRegistrationForm, TeacherMethodistRegistrationForm
from .models import Role, User
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache
from django.views.decorators.debug import sensitive_post_parameters
from django.core.exceptions import ValidationError
from .forms import PasswordResetRequestForm, PasswordResetVerifyForm, PasswordResetConfirmForm
from .models import User, PasswordResetCode, Certificate, Lecture, PracticalAssignment, AssignmentSubmissionFile, UserCourse, FavoriteCourse
from .utils.email_utils import send_password_reset_code, send_password_reset_success_email
from django.views.static import serve
import os
import urllib.parse
from rest_framework_simplejwt.tokens import RefreshToken
from unireax_main.models import (
    Course, Lecture, PracticalAssignment, Test, 
    UserCourse, Review, FavoriteCourse, TeacherApplication
)

MAX_ATTEMPTS = 5
BLOCK_MINUTES = 5
ATTEMPT_WINDOW_MINUTES = 5


@login_required
@require_POST
def save_user_theme(request):
    """Сохранение темы пользователя в БД"""
    try:
        data = json.loads(request.body)
        theme = data.get('theme')
        
        if theme == 'light':
            request.user.is_light_theme = True
        elif theme == 'dark':
            request.user.is_light_theme = False
        else:
            return JsonResponse({'status': 'error'}, status=400)
        
        request.user.save(update_fields=['is_light_theme'])
        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error'}, status=400)


def main_page(request):
    """функция для отображения главной страницы с популярными курсами"""
    students_count = User.objects.filter(role__role_name='слушатель курсов').count()
    courses_count = Course.objects.filter(
        is_active=True
    ).exclude(
        course_type__course_type_name='классная комната'
    ).count()

    popular_courses = Course.objects.filter(
        is_active=True
    ).exclude(
        course_type__course_type_name='классная комната'
    ).annotate(
        avg_rating=Avg('review__rating', filter=Q(review__is_approved=True)),
        student_count=Count('usercourse', filter=Q(usercourse__is_active=True))
    ).order_by('-student_count', '-avg_rating')[:6]
    
    theme = request.COOKIES.get('theme', 'dark')
    
    context = {
        'popular_courses': popular_courses,
        'students_count': students_count,
        'courses_count': courses_count,
        'theme': theme,
        'is_dark': theme == 'dark'
    }
    
    return render(request, 'main_page.html', context)


def generate_verification_code():
    """Генерирует 6-значный код из цифр"""
    return ''.join(random.choices(string.digits, k=6))


def send_verification_email(email, code, first_name, last_name):
    """Отправляет письмо с кодом подтверждения"""
    subject = 'Подтверждение регистрации на UNIREAX'
    
    message = f"""
Здравствуйте, {first_name} {last_name}!

Вы зарегистрировались на образовательной платформе UNIREAX.

Ваш код подтверждения: {code}

Введите этот код на странице подтверждения, чтобы завершить регистрацию.

Если вы не регистрировались на нашем сайте, просто проигнорируйте это письмо.

С уважением,
Команда UNIREAX
"""
    
    try:
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[email],
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Ошибка отправки email: {e}")
        return False


def register_listener(request):
    """Представление для регистрации слушателя курсов - шаг 1"""
    
    if request.user.is_authenticated:
        return redirect('profile_page')
    
    if request.method == 'POST':
        form = ListenerRegistrationForm(request.POST)
        
        if form.is_valid():
            request.session['temp_user_data'] = {
                'username': form.cleaned_data['username'],
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'patronymic': form.cleaned_data.get('patronymic', ''),
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password1'],
                'is_listener': True,
            }
            
            code = generate_verification_code()
            request.session['verification_code'] = code
            request.session['verification_email'] = form.cleaned_data['email']
            request.session['verification_expires'] = (timezone.now() + timedelta(minutes=10)).timestamp()
            
            if send_verification_email(
                email=form.cleaned_data['email'],
                code=code,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            ):
                messages.success(request, 'Код подтверждения отправлен на вашу почту!')
                return redirect('verify_registration')
            else:
                messages.error(request, 'Ошибка при отправке письма. Попробуйте позже.')
                return render(request, 'register/registration_listener.html', {'form': form})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = ListenerRegistrationForm()
    
    return render(request, 'register/registration_listener.html', {'form': form})


def register_teacher_methodist(request):
    """Представление для регистрации преподавателя/методиста - шаг 1"""
    
    if request.user.is_authenticated:
        return redirect('profile_page')
    
    if request.method == 'POST':
        form = TeacherMethodistRegistrationForm(request.POST, request.FILES)
        
        if form.is_valid():
            request.session['temp_user_data'] = {
                'username': form.cleaned_data['username'],
                'first_name': form.cleaned_data['first_name'],
                'last_name': form.cleaned_data['last_name'],
                'patronymic': form.cleaned_data.get('patronymic', ''),
                'email': form.cleaned_data['email'],
                'password': form.cleaned_data['password1'],
                'role_choice': form.cleaned_data['role_choice'],
                'position': form.cleaned_data['position'],
                'educational_institution': form.cleaned_data['educational_institution'],
                'is_listener': False,
            }
            
            if 'certificat_from_the_place_of_work_path' in request.FILES:
                certificate = request.FILES['certificat_from_the_place_of_work_path']
                request.session['temp_certificate_name'] = certificate.name
                from django.core.files.storage import default_storage
                temp_path = f'temp_certificates/{certificate.name}'
                default_storage.save(temp_path, certificate)
                request.session['temp_certificate_path'] = temp_path
            
            code = generate_verification_code()
            request.session['verification_code'] = code
            request.session['verification_email'] = form.cleaned_data['email']
            request.session['verification_expires'] = (timezone.now() + timedelta(minutes=10)).timestamp()
            
            if send_verification_email(
                email=form.cleaned_data['email'],
                code=code,
                first_name=form.cleaned_data['first_name'],
                last_name=form.cleaned_data['last_name']
            ):
                messages.success(request, 'Код подтверждения отправлен на вашу почту!')
                return redirect('verify_registration')
            else:
                messages.error(request, 'Ошибка при отправке письма. Попробуйте позже.')
                return render(request, 'register/registration_teacher_methodist.html', {'form': form})
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{error}')
    else:
        form = TeacherMethodistRegistrationForm()
    
    return render(request, 'register/registration_teacher_methodist.html', {'form': form})


def verify_registration(request):
    """Представление для подтверждения email кодом - шаг 2"""
    
    if 'temp_user_data' not in request.session or 'verification_code' not in request.session:
        messages.error(request, 'Сессия истекла. Пожалуйста, начните регистрацию заново.')
        return redirect('register_listener')
    
    expires = request.session.get('verification_expires')
    if expires and timezone.now().timestamp() > expires:
        messages.error(request, 'Срок действия кода истек. Пожалуйста, начните регистрацию заново.')
        request.session.pop('temp_user_data', None)
        request.session.pop('verification_code', None)
        request.session.pop('verification_expires', None)
        return redirect('register_listener')
    
    if request.method == 'POST':
        entered_code = request.POST.get('code', '').strip()
        stored_code = request.session.get('verification_code')
        
        if entered_code == stored_code:
            user_data = request.session['temp_user_data']
            
            user = User.objects.create_user(
                username=user_data['username'],
                email=user_data['email'],
                password=user_data['password'],
                first_name=user_data['first_name'],
                last_name=user_data['last_name'],
                patronymic=user_data.get('patronymic', ''),
            )
            

            if user_data.get('is_listener'):
                
                listener_role, _ = Role.objects.get_or_create(role_name="слушатель курсов")
                user.role = listener_role
                user.is_verified = True 
                user.save()

                request.session.pop('temp_user_data', None)
                request.session.pop('verification_code', None)
                request.session.pop('verification_expires', None)
                
                login(request, user)
                messages.success(request, 'Регистрация прошла успешно! Добро пожаловать в UNIREAX!')
                return redirect('main_page')
            else:
                role_choice = user_data['role_choice']
                if role_choice == 'teacher':
                    teacher_role, _ = Role.objects.get_or_create(role_name="преподаватель")
                    user.role = teacher_role
                else:
                    methodist_role, _ = Role.objects.get_or_create(role_name="методист")
                    user.role = methodist_role
                
                user.position = user_data['position']
                user.educational_institution = user_data['educational_institution']
                user.is_verified = False 
                
                temp_path = request.session.get('temp_certificate_path')
                if temp_path:
                    from django.core.files.storage import default_storage
                    from django.core.files.base import ContentFile
                    import os
                    
                    if default_storage.exists(temp_path):
                        file_content = default_storage.open(temp_path).read()
                        file_name = os.path.basename(temp_path)
                        user.certificate_file.save(file_name, ContentFile(file_content))
                        default_storage.delete(temp_path)
                
                user.save()
                
                request.session.pop('temp_user_data', None)
                request.session.pop('verification_code', None)
                request.session.pop('verification_expires', None)
                request.session.pop('temp_certificate_path', None)
                request.session.pop('temp_certificate_name', None)
                
                login(request, user)
                messages.success(request, 'Регистрация прошла успешно! Ваш аккаунт будет активирован после проверки документов администратором.')
                return redirect('unverified_profile')
        else:
            messages.error(request, 'Неверный код подтверждения. Попробуйте снова.')
    
    email = request.session.get('verification_email', '')
    
    return render(request, 'register/verify_registration.html', {'email': email})


def resend_verification_code(request):
    """Повторная отправка кода подтверждения"""
    
    if 'temp_user_data' not in request.session:
        messages.error(request, 'Сессия истекла. Пожалуйста, начните регистрацию заново.')
        return redirect('register_listener')
    
    user_data = request.session['temp_user_data']
    
    code = generate_verification_code()
    request.session['verification_code'] = code
    request.session['verification_expires'] = (timezone.now() + timedelta(minutes=10)).timestamp()
    
    if send_verification_email(
        email=user_data['email'],
        code=code,
        first_name=user_data['first_name'],
        last_name=user_data['last_name']
    ):
        messages.success(request, 'Новый код подтверждения отправлен на вашу почту!')
    else:
        messages.error(request, 'Ошибка при отправке письма. Попробуйте позже.')
    
    return redirect('verify_registration')

@login_required
def unverified_profile(request):
    """Страница для пользователей, ожидающих подтверждения"""
    if not request.user.is_authenticated:
        return redirect('login_page')
    
    user = request.user
    
    if request.method == 'POST' and 'profile_update' in request.POST:
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        patronymic = request.POST.get('patronymic', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip()
        position = request.POST.get('position', '').strip()
        educational_institution = request.POST.get('educational_institution', '').strip()
        
        has_error = False
        
        if not first_name:
            messages.error(request, 'Имя обязательно для заполнения')
            has_error = True
        if not last_name:
            messages.error(request, 'Фамилия обязательна для заполнения')
            has_error = True
        if not username:
            messages.error(request, 'Имя пользователя обязательно')
            has_error = True
        if not email:
            messages.error(request, 'Email обязателен')
            has_error = True
        
        if username != user.username and User.objects.filter(username=username).exists():
            messages.error(request, 'Пользователь с таким именем уже существует')
            has_error = True
        
        if email != user.email and User.objects.filter(email=email).exists():
            messages.error(request, 'Пользователь с таким email уже существует')
            has_error = True
        
        if user.role and user.role.role_name in ['преподаватель', 'методист']:
            if not position:
                messages.error(request, 'Должность обязательна для заполнения')
                has_error = True
            if not educational_institution:
                messages.error(request, 'Учебное заведение обязательно для заполнения')
                has_error = True
        
        if not has_error:
            user.first_name = first_name
            user.last_name = last_name
            user.patronymic = patronymic
            user.username = username
            user.email = email
            user.position = position
            user.educational_institution = educational_institution
            
            if 'certificate_file' in request.FILES:
                certificate_file = request.FILES['certificate_file']
                if certificate_file.size > 10 * 1024 * 1024:
                    messages.error(request, 'Размер файла не должен превышать 10 МБ')
                else:
                    if user.certificate_file:
                        try:
                            os.remove(user.certificate_file.path)
                        except:
                            pass
                    user.certificate_file = certificate_file
            
            user.is_verified = False
            user.save()
            
            messages.success(request, 'Ваши данные успешно обновлены! Аккаунт отправлен на повторную проверку.')
            return redirect('unverified_profile')
    
    if request.method == 'POST' and 'password_change' in request.POST:
        old_password = request.POST.get('old_password')
        new_password1 = request.POST.get('new_password1')
        new_password2 = request.POST.get('new_password2')
        
        if not user.check_password(old_password):
            messages.error(request, 'Неверный текущий пароль')
        elif new_password1 != new_password2:
            messages.error(request, 'Новые пароли не совпадают')
        elif len(new_password1) < 8:
            messages.error(request, 'Пароль должен содержать минимум 8 символов')
        else:
            user.set_password(new_password1)
            user.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменен!')
            return redirect('unverified_profile')
    
    return render(request, 'unverified_profile.html')

def search_courses(request):
    """
    Динамический поиск курсов через БД с функцией "Возможно вы имели ввиду"
    Возвращает полные данные для отображения карточек курсов
    """
    from django.db.models import Avg, Count, Q
    from django.urls import reverse
    
    query = request.GET.get('q', '').strip()
    
    if len(query) < 3:
        return JsonResponse({'results': [], 'suggestion': None})
    
    padded_query = f"  {query.lower()}  "
    query_trigrams = {padded_query[i:i+3] for i in range(len(padded_query) - 2)}
    
    courses = Course.objects.filter(
        Q(course_name__icontains=query) |
        Q(course_description__icontains=query) |
        Q(course_category__course_category_name__icontains=query) |
        Q(course_type__course_type_name__icontains=query)
    ).filter(
        is_active=True
    ).exclude(
        course_type__course_type_name='классная комната'
    ).select_related('course_category', 'course_type', 'created_by').annotate(
        avg_rating=Avg('review__rating', filter=Q(review__is_approved=True)),
        student_count=Count('usercourse', filter=Q(usercourse__is_active=True))
    ).distinct()[:12]
    
    if not courses.exists():
        all_courses = Course.objects.filter(
            is_active=True
        ).exclude(
            course_type__course_type_name='классная комната'
        ).select_related('course_category', 'course_type')[:50]
        
        suggestions = []
        for course in all_courses:
            padded_name = f"  {course.course_name.lower()}  "
            name_trigrams = {padded_name[i:i+3] for i in range(len(padded_name) - 2)}
            common = query_trigrams & name_trigrams
            all_trigrams = query_trigrams | name_trigrams
            similarity = len(common) / len(all_trigrams) if all_trigrams else 0
            
            if similarity > 0.2:
                suggestions.append((course, similarity))
        
        suggestions.sort(key=lambda x: x[1], reverse=True)
        
        if suggestions:
            suggested_course = suggestions[0][0]
            return JsonResponse({
                'results': [],
                'suggestion': {
                    'title': suggested_course.course_name,
                    'url': reverse('course_detail', args=[suggested_course.id])
                }
            })
        return JsonResponse({'results': [], 'suggestion': None})
    
    results = []
    for course in courses:
        icon = "fas fa-graduation-cap"
        if course.course_category:
            cat_name = course.course_category.course_category_name.lower()
            if any(word in cat_name for word in ['программ', 'код', 'python', 'java']):
                icon = "fas fa-code"
            elif any(word in cat_name for word in ['дизайн', 'design']):
                icon = "fas fa-palette"
            elif any(word in cat_name for word in ['аналит', 'данных', 'data']):
                icon = "fas fa-chart-line"
            elif any(word in cat_name for word in ['маркет', 'реклам']):
                icon = "fas fa-bullhorn"
        
        image_url = None
        if course.course_photo_path:
            image_url = course.course_photo_path.url
        
        results.append({
            'id': course.id,
            'title': course.course_name,
            'description': course.course_description or '',
            'price': int(course.course_price) if course.course_price else None,
            'category': course.course_category.course_category_name if course.course_category else None,
            'type': course.course_type.course_type_name if course.course_type else None,
            'hours': course.course_hours or 0,
            'has_certificate': course.has_certificate,
            'is_completed': course.is_completed,
            'max_places': course.course_max_places,
            'student_count': course.student_count or 0,
            'avg_rating': str(round(course.avg_rating, 1)) if course.avg_rating else '0.0',
            'created_date': course.created_at.strftime('%d.%m.%Y') if course.created_at else '',
            'image_url': image_url,
            'icon': icon,
            'url': reverse('course_detail', args=[course.id])
        })
    
    return JsonResponse({'results': results, 'suggestion': None})

def get_client_ip(request):
    """Получение IP адреса клиента (только для информации)"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def is_username_blocked(username):
    """
    Проверка, заблокирован ли пользователь для входа
    Возвращает tuple: (is_blocked, minutes_left, remaining_attempts)
    """
    if not username:
        return False, 0, MAX_ATTEMPTS
    
    now = timezone.now()
    check_since = now - timedelta(minutes=ATTEMPT_WINDOW_MINUTES)
    
    failed_attempts = LoginAttempt.objects.filter(
        username__iexact=username,
        attempt_time__gte=check_since,
        success=False
    ).order_by('attempt_time')
    
    attempts_count = failed_attempts.count()
    remaining_attempts = max(0, MAX_ATTEMPTS - attempts_count)
    
    if attempts_count >= MAX_ATTEMPTS:
        oldest_attempt = failed_attempts.first()
        if oldest_attempt:
            block_until = oldest_attempt.attempt_time + timedelta(minutes=BLOCK_MINUTES)
            if now < block_until:
                minutes_left = int((block_until - now).total_seconds() / 60) + 1
                return True, minutes_left, 0
    
    return False, 0, remaining_attempts


def record_failed_attempt(username, ip_address):
    """Записывает неудачную попытку входа"""
    return LoginAttempt.objects.create(
        username=username,
        ip_address=ip_address,
        success=False
    )


def clear_attempts(username):
    """Очищает неудачные попытки для пользователя"""
    LoginAttempt.objects.filter(
        username__iexact=username,
        success=False
    ).delete()


def login_page(request):
    """функция авторизации пользователей"""
    if request.user.is_authenticated:
        return redirect('main_page')
    
    ip_address = get_client_ip(request) 

    if request.method == 'GET':
        username_from_session = request.session.get('last_login_username', None)
        if username_from_session:
            is_blocked, minutes_left, _ = is_username_blocked(username_from_session)
            if is_blocked:
                return render(request, 'auth/login.html', {
                    'error': True,
                    'blocked': True,
                    'minutes_left': minutes_left,
                    'error_message': f'Слишком много неудачных попыток входа. Попробуйте через {minutes_left} минут(ы).',
                    'debug': settings.DEBUG
                })
        
        return render(request, 'auth/login.html', {
            'error': False,
            'blocked': False,
            'debug': settings.DEBUG
        })
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        remember_me = request.POST.get('remember') == 'on'
        
        request.session['last_login_username'] = username
        
        is_blocked, minutes_left, remaining_attempts = is_username_blocked(username)
        
        if is_blocked:
            return render(request, 'auth/login.html', {
                'error': True,
                'blocked': True,
                'minutes_left': minutes_left,
                'error_message': f'Слишком много неудачных попыток входа. Доступ заблокирован на {minutes_left} минут(ы).',
                'username': username,
                'debug': settings.DEBUG
            })
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            clear_attempts(username)
            
            LoginAttempt.objects.create(
                user=user,
                username=username,
                ip_address=ip_address,
                success=True
            )
            
            login(request, user)
            
            if not remember_me:
                request.session.set_expiry(0)
            else:
                request.session.set_expiry(1209600)  

            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)
            refresh_token = str(refresh)
            
            response = redirect('main_page')
            
            max_age = 3600 if not remember_me else 1209600
            response.set_cookie(
                'access_token',
                access_token,
                max_age=max_age,
                httponly=True,
                samesite='Lax',
                secure=not settings.DEBUG
            )
            
            response.set_cookie(
                'refresh_token',
                refresh_token,
                max_age=1209600,
                httponly=True,
                samesite='Lax',
                secure=not settings.DEBUG
            )
            
            return response
        else:
            record_failed_attempt(username, ip_address)
            one_hour_ago = timezone.now() - timedelta(hours=1)
            LoginAttempt.objects.filter(attempt_time__lt=one_hour_ago).delete()
            is_blocked, minutes_left, remaining_attempts = is_username_blocked(username)
            
            if is_blocked:
                error_message = f'Слишком много неудачных попыток входа. Доступ заблокирован на {minutes_left} минут(ы).'
            else:
                error_message = 'Неверное имя пользователя или пароль'
            
            return render(request, 'auth/login.html', {
                'error': True,
                'blocked': is_blocked,
                'minutes_left': minutes_left if is_blocked else 0,
                'error_message': error_message,
                'username': username,
                'remaining_attempts': remaining_attempts,
                'max_attempts': MAX_ATTEMPTS,
                'debug': settings.DEBUG
            })

def logout_view(request):
    """Выход из системы"""
    logout(request)

    if 'access_token' in request.session:
        del request.session['access_token']
    if 'refresh_token' in request.session:
        del request.session['refresh_token']
    
    response = redirect('login_page')
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    messages.success(request, 'Вы успешно вышли из системы')
    return response


@login_required
def profile_page(request):
    """
    Страница профиля пользователя 
    """
    user = request.user
    
    if hasattr(user, 'full_name') and user.full_name:
        full_name = user.full_name
    else:
        parts = [user.last_name, user.first_name, getattr(user, 'patronymic', '')]
        full_name = ' '.join(filter(None, parts)).strip() or user.username
    
    role_name = 'cлушатель курсов'
    role_id = None
    if user.role:
        role_name = user.role.role_name
        role_id = user.role.id
    elif user.is_superuser:
        role_name = 'администратор'
    
    date_joined = user.date_joined.strftime('%d.%m.%Y') if user.date_joined else '—'
    
    enrolled_courses = user.usercourse_set.filter(is_active=True).count() if hasattr(user, 'usercourse_set') else 0
    completed_courses = user.usercourse_set.filter(status_course=True).count() if hasattr(user, 'usercourse_set') else 0
    certificates_count = user.certificate_set.count() if hasattr(user, 'certificate_set') else 0
    
    context = {
        'user': user,
        'full_name': full_name,
        'role_name': role_name,
        'role_id': role_id,
        'date_joined': date_joined,
        'is_verified': getattr(user, 'is_verified', False),
        'position': getattr(user, 'position', ''),
        'educational_institution': getattr(user, 'educational_institution', ''),
        'enrolled_courses': enrolled_courses,
        'completed_courses': completed_courses,
        'certificates_count': certificates_count,
        'access_token': request.session.get('access_token'),
    }
    
    return render(request, 'profile.html', context)

def courses_page(request):
    """
    Страница каталога курсов с фильтрацией и сортировкой
    """
    from django.db.models import Case, When, Value, IntegerField, F
    
    courses = Course.objects.filter(
        is_active=True
    ).exclude(
        course_type__course_type_name='классная комната'
    ).annotate(
        avg_rating=Avg('review__rating', filter=Q(review__is_approved=True)),
        review_count=Count('review', filter=Q(review__is_approved=True)),
        student_count=Count('usercourse', filter=Q(usercourse__is_active=True))
    )
    
    user = request.user
    
    if user.is_authenticated and user.role and user.role.role_name.lower() == 'преподаватель':
        courses = courses.filter(
            Q(is_find_teacher=False) | 
            Q(is_find_teacher__isnull=True) | 
            Q(is_find_teacher=True)
        )
    else:
        courses = courses.filter(
            Q(is_find_teacher=False) | Q(is_find_teacher__isnull=True)
        )
    
    search_query = request.GET.get('search', '')
    if search_query:
        courses = courses.filter(
            Q(course_name__icontains=search_query) |
            Q(course_description__icontains=search_query)
        )
    
    selected_categories = request.GET.getlist('category')
    if selected_categories:
        courses = courses.filter(course_category_id__in=selected_categories)
    
    selected_types = request.GET.getlist('type')
    if selected_types:
        courses = courses.filter(course_type_id__in=selected_types)
    
    if request.GET.get('has_certificate'):
        courses = courses.filter(has_certificate=True)
    
    if request.GET.get('free_only'):
        courses = courses.filter(
            Q(course_price__isnull=True) | 
            Q(course_price=0)
        )
    
    price_min = request.GET.get('price_min')
    if price_min:
        courses = courses.filter(course_price__gte=price_min)
    
    price_max = request.GET.get('price_max')
    if price_max:
        courses = courses.filter(
            Q(course_price__lte=price_max) |
            Q(course_price__isnull=True)
        )

    sort_by = request.GET.get('sort_by', 'popular')
    if sort_by == 'popular':
        courses = courses.order_by('-student_count', '-avg_rating')
    
    elif sort_by == 'rating_asc':
        courses = courses.order_by(
            Case(
                When(avg_rating__isnull=True, then=Value(0)),
                default=F('avg_rating'),
                output_field=IntegerField()
            ).asc()
        )
    
    elif sort_by == 'rating_desc':
        courses = courses.order_by(
            Case(
                When(avg_rating__isnull=True, then=Value(0)),
                default=F('avg_rating'),
                output_field=IntegerField()
            ).desc()
        )
    
    elif sort_by == 'price_asc':
        courses = courses.annotate(
            price_order=Case(
                When(Q(course_price__isnull=True) | Q(course_price=0), then=Value(0)),
                default=F('course_price'),
                output_field=IntegerField()
            )
        ).order_by('price_order', 'course_price')
    
    elif sort_by == 'price_desc':
        courses = courses.annotate(
            price_order=Case(
                When(Q(course_price__isnull=True) | Q(course_price=0), then=Value(999999999)),
                default=F('course_price'),
                output_field=IntegerField()
            )
        ).order_by('-price_order', '-course_price')
    
    elif sort_by == 'newest':
        courses = courses.order_by('-created_at')
    
    elif sort_by == 'hours_asc':
        courses = courses.order_by('course_hours')
    
    elif sort_by == 'hours_desc':
        courses = courses.order_by('-course_hours')
    
    paginator = Paginator(courses, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    categories = CourseCategory.objects.all()
    types = CourseType.objects.all()
    
    context = {
        'courses': page_obj,
        'categories': categories,
        'types': types,
        'search_query': search_query,
        'selected_categories': [int(c) for c in selected_categories if c.isdigit()],
        'selected_types': [int(t) for t in selected_types if t.isdigit()],
        'has_certificate': request.GET.get('has_certificate') == 'true',
        'free_only': request.GET.get('free_only') == 'true',
        'price_min': price_min,
        'price_max': price_max,
        'sort_by': sort_by,
        'view_mode': request.GET.get('view', 'grid'),
    }
    
    return render(request, 'catalog.html', context)

def course_detail(request, course_id):
    """
    Страница детального просмотра курса (для всех пользователей)
    """
    course = get_object_or_404(
        Course.objects.filter(is_active=True).annotate(
            avg_rating=Avg('review__rating', filter=Q(review__is_approved=True)),
            review_count=Count('review', filter=Q(review__is_approved=True)),
            student_count=Count('usercourse', filter=Q(usercourse__is_active=True))
        ),
        id=course_id
    )

    lectures = Lecture.objects.filter(
        course=course,
        is_active=True
    ).order_by('lecture_order')
    
    lectures_data = []
    for lecture in lectures:
        lecture_assignments = PracticalAssignment.objects.filter(
            lecture=lecture,
            is_active=True
        ).values('id', 'practical_assignment_name')
        
        lecture_tests = Test.objects.filter(
            lecture=lecture,
            is_active=True
        ).values('id', 'test_name')
        
        lectures_data.append({
            'id': lecture.id,
            'name': lecture.lecture_name,
            'order': lecture.lecture_order,
            'assignments': [
                {'id': a['id'], 'name': a['practical_assignment_name']} 
                for a in lecture_assignments
            ],
            'tests': [
                {'id': t['id'], 'name': t['test_name']} 
                for t in lecture_tests
            ]
        })
    
    reviews = course.review_set.filter(is_approved=True).order_by('-publish_date')[:10]
    
    is_enrolled = False
    was_enrolled = False
    progress = 0
    user_review = None
    is_favorited = False
    is_teacher_applied = False  
    
    if request.user.is_authenticated:
        user_course = UserCourse.objects.filter(user=request.user, course=course).first()
        if user_course:
            is_enrolled = user_course.is_active
            was_enrolled = True
            if is_enrolled:
                progress = calculate_course_completion(request.user.id, course.id)
        
        user_review = Review.objects.filter(user=request.user, course=course).first()
        
        is_favorited = FavoriteCourse.objects.filter(
            user=request.user, 
            course=course
        ).exists()
        
        if request.user.role and request.user.role.role_name.lower() == 'преподаватель':
            teacher_application = TeacherApplication.objects.filter(
                teacher=request.user,
                course=course
            ).first()
            if teacher_application:
                is_teacher_applied = teacher_application.status == 'pending'
    
    context = {
        'course': course,
        'lectures': lectures_data,
        'reviews': reviews,
        'is_enrolled': is_enrolled,
        'was_enrolled': was_enrolled,
        'progress': progress,
        'user_review': user_review,
        'student_count': course.student_count,
        'avg_rating': course.avg_rating or 0,
        'review_count': course.review_count,
        'is_favorited': is_favorited,
        'is_teacher_applied': is_teacher_applied,  # ДОБАВЛЕНО
    }
    
    return render(request, 'course_detail.html', context)


@login_required
def add_review(request, course_id):
    """
    Добавление отзыва к курсу
    """
    if request.method == 'POST':
        course = get_object_or_404(Course, id=course_id, is_active=True)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        
        existing_review = Review.objects.filter(user=request.user, course=course).first()
        if existing_review:
            messages.error(request, 'Вы уже оставляли отзыв на этот курс')
            return redirect('course_detail', course_id=course.id)
        
        review = Review.objects.create(
            user=request.user,
            course=course,
            rating=rating,
            comment_review=comment,
            is_approved=True  
        )
        
        messages.success(request, 'Спасибо за ваш отзыв! Он появится после проверки модератором.')
        return redirect('course_detail', course_id=course.id)
    
    return redirect('course_detail', course_id=course_id)

def about_page(request):
    """
    Страница "О нас" с формой обратной связи
    """
    return render(request, 'about.html')

def teachers_page(request):
    """
    Страница для преподавателей 
    """
    return render(request, 'teachers.html')


def feedback_page(request):
    """
    Отдельная страница обратной связи с расширенной формой и капчей
    """
    if request.method == 'POST':
        form = FeedbackForm(request.POST)
        
        if form.is_valid():
            name = form.cleaned_data['name']
            email = form.cleaned_data['email']
            subject = form.cleaned_data.get('subject', 'Без темы')
            message = form.cleaned_data['message']
            
            try:
                moscow_tz = pytz.timezone('Europe/Moscow')
                current_time = timezone.now().astimezone(moscow_tz)
                formatted_date = current_time.strftime('%d.%m.%Y %H:%M')
                text_message = f"""
                Имя: {name}
                Email: {email}
                Тема: {subject}
                Дата: {formatted_date}

                Сообщение:
                {message}
                """
                html_message = render_to_string('emails/feedback_email.html', {
                    'name': name,
                    'email': email,
                    'subject': subject,
                    'message': message,
                    'date': formatted_date,
                })
                
                email_message = EmailMultiAlternatives(
                    subject=f'Обратная связь: {subject}',
                    body=text_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    to=['unireax@mail.ru'],
                )
                email_message.attach_alternative(html_message, "text/html")
                email_message.send()
                
                messages.success(request, 'Спасибо за обращение! Мы свяжемся с вами в ближайшее время.')
                return redirect('feedback_page')
                
            except Exception as e:
                messages.error(request, f'Ошибка отправки. Попробуйте позже. ({str(e)})')
        else:
            messages.error(request, 'Пожалуйста, проверьте правильность заполнения формы и подтвердите, что вы не робот.')
    else:
        form = FeedbackForm()
    
    return render(request, 'feedback.html', {'form': form})

def password_reset_request(request):
    """
    Шаг 1: Запрос email для восстановления пароля
    """
    if request.user.is_authenticated:
        return redirect('main_page')
    
    form = PasswordResetRequestForm()
    
    if request.method == 'POST':
        form = PasswordResetRequestForm(request.POST)
        
        if form.is_valid():
            email = form.cleaned_data['email']
            
            try:
                user = User.objects.get(email=email)
                reset_code = PasswordResetCode.create_reset_code(user)
                send_password_reset_code(user, reset_code.code, request)
                request.session['reset_email'] = email
                
                messages.success(request, 'Код восстановления отправлен на ваш email!')
                return redirect('password_reset_verif')
                
            except User.DoesNotExist:
                messages.error(request, 'Пользователь с таким email не найден')
    
    context = {
        'form': form,
        'title': 'Восстановление пароля',
        'subtitle': 'Введите email, указанный при регистрации',
    }
    
    return render(request, 'auth/password_reset_request.html', context)


def password_reset_verify(request):
    """
    Шаг 2: Проверка кода восстановления
    """
    if request.user.is_authenticated:
        return redirect('main_page')
    
    email = request.session.get('reset_email')
    
    if not email:
        messages.error(request, 'Сессия истекла. Пожалуйста, начните заново.')
        return redirect('password_reset_req')
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('password_reset_req')
    
    form = PasswordResetVerifyForm()
    
    reset_code = PasswordResetCode.objects.filter(
        user=user,
        is_used=False
    ).order_by('-created_at').first()
    
    time_remaining = reset_code.time_remaining() if reset_code else 0
    can_resend = False
    
    if reset_code and reset_code.is_expired():
        can_resend = True
    elif not reset_code:
        can_resend = True
    
    if request.method == 'POST':
        form = PasswordResetVerifyForm(request.POST)
        
        if form.is_valid():
            code = form.cleaned_data['code']
            
            reset_code, error = PasswordResetCode.validate_code(user, code)
            
            if reset_code:
                reset_code.mark_code_used()
                
                request.session['reset_verified'] = True
                
                messages.success(request, 'Код подтвержден! Придумайте новый пароль.')
                return redirect('password_reset_conf')
            else:
                messages.error(request, error)
    
    context = {
        'form': form,
        'email': email,
        'time_remaining': time_remaining,
        'can_resend': can_resend,
        'title': 'Подтверждение кода',
        'subtitle': f'Введите код из письма, отправленного на {email}',
    }
    
    return render(request, 'auth/password_reset_verify.html', context)


def password_reset_resend_code(request):
    """
    Повторная отправка кода восстановления
    """
    if request.method != 'POST':
        return redirect('password_reset_req')
    
    email = request.session.get('reset_email')
    
    if not email:
        return redirect('password_reset_req')
    
    try:
        user = User.objects.get(email=email)
        
        PasswordResetCode.objects.filter(
            user=user,
            is_used=False
        ).delete()
        
        reset_code = PasswordResetCode.create_reset_code(user)
        
        send_password_reset_code(user, reset_code.code, request)
        
        messages.success(request, 'Новый код отправлен на ваш email!')
        
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('password_reset_req')
    
    return redirect('password_reset_verif')


@sensitive_post_parameters()
@csrf_protect
@never_cache
def password_reset_confirm(request):
    """
    Шаг 3: Установка нового пароля
    """
    if request.user.is_authenticated:
        return redirect('main_page')
    
    if not request.session.get('reset_verified'):
        messages.error(request, 'Доступ запрещен. Пожалуйста, подтвердите код.')
        return redirect('password_reset_req')
    
    email = request.session.get('reset_email')
    
    if not email:
        messages.error(request, 'Сессия истекла')
        return redirect('password_reset_req')
    
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        messages.error(request, 'Пользователь не найден')
        return redirect('password_reset_req')
    
    form = PasswordResetConfirmForm()
    
    if request.method == 'POST':
        form = PasswordResetConfirmForm(request.POST)
        
        if form.is_valid():
            new_password = form.cleaned_data['new_password1']
            
            user.set_password(new_password)
            user.save()
            
            update_session_auth_hash(request, user)
            
            send_password_reset_success_email(user, request)
            
            if 'reset_email' in request.session:
                del request.session['reset_email']
            if 'reset_verified' in request.session:
                del request.session['reset_verified']
            
            messages.success(request, 'Пароль успешно изменен! Теперь вы можете войти.')
            return redirect('login_page')
    
    context = {
        'form': form,
        'title': 'Новый пароль',
        'subtitle': 'Придумайте надежный пароль',
    }
    
    return render(request, 'auth/password_reset_confirm.html', context)


def protected_certificate(request, path):
    """Защищённая выдача файлов из папки certificates:
       - Сертификаты курсов (доступ: владелец, администратор)
       - Документы пользователей (справки/дипломы) (доступ: владелец, администратор)
    """

    decoded_path = urllib.parse.unquote(path)
    filename = os.path.basename(decoded_path)
    
    owner_user = None
    file_field = None
    
    try:
        certificate = Certificate.objects.get(certificate_file_path__endswith=filename)
        owner_user = certificate.user_course.user
        file_field = certificate.certificate_file_path
    except Certificate.DoesNotExist:

        try:
            user = User.objects.get(certificate_file__endswith=filename)
            owner_user = user
            file_field = user.certificate_file
        except User.DoesNotExist:
            raise Http404(f"Файл не найден в базе данных: {filename}")
    
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Необходимо авторизоваться")
    
    if request.user.id != owner_user.id and not request.user.is_admin:
        return HttpResponseForbidden("У вас нет доступа к этому файлу")

    possible_paths = [
        os.path.join(settings.MEDIA_ROOT, decoded_path),
        os.path.join(settings.MEDIA_ROOT, path),
        os.path.join(settings.MEDIA_ROOT, 'certificates', filename),
        os.path.join(settings.MEDIA_ROOT, filename),
    ]
    
    if file_field:
        db_path = str(file_field)
        db_full_path = os.path.join(settings.MEDIA_ROOT, db_path)
        if db_full_path not in possible_paths:
            possible_paths.append(db_full_path)
    
    search_pattern = os.path.join(settings.MEDIA_ROOT, 'certificates', '*', '*', '*', filename)
    matching_files = glob.glob(search_pattern)
    for match in matching_files:
        if match not in possible_paths:
            possible_paths.append(match)
    
    for file_path in possible_paths:
        if os.path.exists(file_path):

            ext = os.path.splitext(filename)[1].lower()
            if ext == '.pdf':
                content_type = 'application/pdf'
            elif ext in ['.jpg', '.jpeg']:
                content_type = 'image/jpeg'
            elif ext == '.png':
                content_type = 'image/png'
            else:
                content_type = 'application/octet-stream'
            
            return FileResponse(open(file_path, 'rb'), content_type=content_type)
    
    raise Http404(f"Файл не найден на диске: {filename}")

def protected_lecture_file(request, path):
    """Защищённая выдача файлов лекций
       Доступ: администраторы, методисты, преподаватели, а также слушатели, записанные на курс
    """
    decoded_path = urllib.parse.unquote(path)
    filename = os.path.basename(decoded_path)
    
    try:
        lecture = Lecture.objects.get(lecture_document_path__endswith=filename)
    except Lecture.DoesNotExist:
        lecture = Lecture.objects.filter(lecture_document_path__icontains=filename).first()
        if not lecture:
            raise Http404(f"Файл лекции не найден в базе данных: {filename}")
    
    course = lecture.course
    
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Необходимо авторизоваться")
    
    has_access = False

    if request.user.is_teacher_or_methodist_or_admin:
        has_access = True
    else:

        has_access = UserCourse.objects.filter(
            user=request.user,
            course=course,
            is_active=True
        ).exists()
    
    if not has_access:
        return HttpResponseForbidden("У вас нет доступа к этому файлу")
    
    possible_paths = [
        os.path.join(settings.MEDIA_ROOT, decoded_path),
        os.path.join(settings.MEDIA_ROOT, path),
        os.path.join(settings.MEDIA_ROOT, 'lectures', filename),
        os.path.join(settings.MEDIA_ROOT, filename),
    ]
    
    if lecture.lecture_document_path:
        db_path = str(lecture.lecture_document_path)
        db_full_path = os.path.join(settings.MEDIA_ROOT, db_path)
        if db_full_path not in possible_paths:
            possible_paths.append(db_full_path)
    
    for file_path in possible_paths:
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'))
    
    raise Http404(f"Файл лекции не найден на диске: {filename}")

def protected_assignment_file(request, path):
    """Защищённая выдача файлов практических заданий (условия заданий)
       Доступ: администраторы, методисты, преподаватели, а также слушатели, записанные на курс
    """
    decoded_path = urllib.parse.unquote(path)
    filename = os.path.basename(decoded_path)

    try:
        assignment = PracticalAssignment.objects.get(assignment_document_path__endswith=filename)
    except PracticalAssignment.DoesNotExist:
        assignment = PracticalAssignment.objects.filter(assignment_document_path__icontains=filename).first()
        if not assignment:
            raise Http404(f"Файл задания не найден в базе данных: {filename}")
    
    course = assignment.lecture.course
    
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Необходимо авторизоваться")
    
    has_access = False
    
    if request.user.is_teacher_or_methodist_or_admin:
        has_access = True
    else:
        has_access = UserCourse.objects.filter(
            user=request.user,
            course=course,
            is_active=True
        ).exists()
    
    if not has_access:
        return HttpResponseForbidden("У вас нет доступа к этому файлу")
    
    possible_paths = [
        os.path.join(settings.MEDIA_ROOT, decoded_path),
        os.path.join(settings.MEDIA_ROOT, path),
        os.path.join(settings.MEDIA_ROOT, 'assignments', filename),
        os.path.join(settings.MEDIA_ROOT, filename),
    ]
    
    if assignment.assignment_document_path:
        db_path = str(assignment.assignment_document_path)
        db_full_path = os.path.join(settings.MEDIA_ROOT, db_path)
        if db_full_path not in possible_paths:
            possible_paths.append(db_full_path)
    
    for file_path in possible_paths:
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'))
    
    raise Http404(f"Файл задания не найден на диске: {filename}")


def protected_submission_file(request, path):
    """Защищённая выдача файлов сдачи заданий студентами
       Доступ: автор работы, администраторы, методисты, преподаватели
    """
    decoded_path = urllib.parse.unquote(path)
    filename = os.path.basename(decoded_path)
    
    try:
        submission_file = AssignmentSubmissionFile.objects.get(file__endswith=filename)
    except AssignmentSubmissionFile.DoesNotExist:
        submission_file = AssignmentSubmissionFile.objects.filter(file__icontains=filename).first()
        if not submission_file:
            raise Http404(f"Файл не найден в базе данных: {filename}")
    
    user_assignment = submission_file.user_assignment
    
    if not request.user.is_authenticated:
        return HttpResponseForbidden("Необходимо авторизоваться")
    
    has_access = False
    
    if request.user.is_teacher_or_methodist_or_admin:
        has_access = True

    elif user_assignment.user == request.user:
        has_access = True
    
    if not has_access:
        return HttpResponseForbidden("У вас нет доступа к этому файлу")
    
    possible_paths = [
        os.path.join(settings.MEDIA_ROOT, decoded_path),
        os.path.join(settings.MEDIA_ROOT, path),
        os.path.join(settings.MEDIA_ROOT, 'assignment_submissions', filename),
        os.path.join(settings.MEDIA_ROOT, filename),
    ]
    
    if submission_file.file:
        db_path = str(submission_file.file)
        db_full_path = os.path.join(settings.MEDIA_ROOT, db_path)
        if db_full_path not in possible_paths:
            possible_paths.append(db_full_path)
    
    for file_path in possible_paths:
        if os.path.exists(file_path):
            return FileResponse(open(file_path, 'rb'))
    
    raise Http404(f"Файл не найден на диске: {filename}")