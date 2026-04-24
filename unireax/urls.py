"""
URL configuration for unireax project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.contrib import admin
from django.shortcuts import render
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve
from unireax_main.views import (
    save_user_theme, 
    protected_certificate, 
    protected_lecture_file, 
    protected_assignment_file, 
    protected_submission_file
)


def custom_400(request, exception=None):
    return render(request, 'errors/general_error.html', {
        'error_code': 400,
        'error_title': 'Неверный запрос',
        'error_message': 'Сервер не может обработать запрос.',
        'error_icon': 'fas fa-exclamation-triangle'
    }, status=400)

def custom_403(request, exception=None):
    return render(request, 'errors/general_error.html', {
        'error_code': 403,
        'error_title': 'Доступ запрещен',
        'error_message': str(exception) if exception else 'У вас недостаточно прав.',
        'error_icon': 'fas fa-lock'
    }, status=403)

def custom_404(request, exception):
    return render(request, 'errors/general_error.html', {
        'error_code': 404,
        'error_title': 'Страница не найдена',
        'error_message': 'Запрашиваемая страница не существует.',
        'error_icon': 'fas fa-search'
    }, status=404)

def custom_500(request):
    return render(request, 'errors/general_error.html', {
        'error_code': 500,
        'error_title': 'Ошибка сервера',
        'error_message': 'Произошла техническая ошибка. Попробуйте позже.',
        'error_icon': 'fas fa-exclamation-circle'
    }, status=500)

def error_page(request):
    """Страница для редиректа из API"""
    code = request.GET.get('code', '500')
    messages = {
        '400': 'Неверный запрос.',
        '401': 'Необходимо авторизоваться.',
        '403': 'Доступ запрещен.',
        '404': 'Страница не найдена.',
        '405': 'Метод запроса не поддерживается.',
        '408': 'Время запроса истекло.',
        '429': 'Слишком много запросов.',
        '500': 'Ошибка на сервере.',
        '502': 'Ошибка шлюза.',
        '503': 'Сервис недоступен.',
        '504': 'Время ожидания истекло.',
    }
    
    titles = {
        '400': 'Неверный запрос',
        '401': 'Не авторизован',
        '403': 'Доступ запрещен',
        '404': 'Страница не найдена',
        '405': 'Метод не разрешен',
        '408': 'Время запроса истекло',
        '429': 'Слишком много запросов',
        '500': 'Ошибка сервера',
        '502': 'Неверный шлюз',
        '503': 'Сервис недоступен',
        '504': 'Шлюз не отвечает',
    }
    
    icons = {
        '400': 'fas fa-exclamation-triangle',
        '401': 'fas fa-sign-in-alt',
        '403': 'fas fa-lock',
        '404': 'fas fa-search',
        '405': 'fas fa-ban',
        '408': 'fas fa-clock',
        '429': 'fas fa-tachometer-alt',
        '500': 'fas fa-exclamation-circle',
        '502': 'fas fa-network-wired',
        '503': 'fas fa-server',
        '504': 'fas fa-hourglass-half',
    }
    
    context = {
        'error_code': code,
        'error_title': titles.get(code, 'Ошибка'),
        'error_message': messages.get(code, 'Произошла ошибка. Попробуйте позже.'),
        'error_icon': icons.get(code, 'fas fa-exclamation-circle'),
    }
    
    return render(request, 'errors/general_error.html', context, status=int(code))

handler400 = custom_400
handler403 = custom_403
handler404 = custom_404
handler500 = custom_500


urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('unireax_main.urls')),
    path('api/', include('api_unireax.urls')),
    path('admin-panel/', include('admin_app.urls')),  
    path('methodist/', include('methodist_app.urls')), 
    path('teacher/', include('teacher_app.urls')),
    path('listener/', include('listener_app.urls')),
    path('error-page/', error_page, name='error_page'),
    path('theme/save/', save_user_theme, name='save_user_theme'),
]

urlpatterns += [
    re_path(r'^media/certificates/(?P<path>.*)$', protected_certificate, name='protected_certificate'),
    re_path(r'^media/lectures/(?P<path>.*)$', protected_lecture_file, name='protected_lecture_file'),
    re_path(r'^media/assignments/(?P<path>.*)$', protected_assignment_file, name='protected_assignment_file'),
    re_path(r'^media/assignment_submissions/(?P<path>.*)$', protected_submission_file, name='protected_submission_file'),
]

# раздача всех остальных медиа-файлов (публичные файлы course_photos)
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
]

# раздача статики через стандартный механизм (только при DEBUG=True)
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)