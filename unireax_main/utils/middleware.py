import threading
import traceback
from django.shortcuts import render, redirect
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin
import logging

logger = logging.getLogger(__name__)

_thread_locals = threading.local()

def get_current_request():
    return getattr(_thread_locals, 'request', None)


class RequestMiddleware(MiddlewareMixin):
    def process_request(self, request):
        _thread_locals.request = request
    
    def process_response(self, request, response):
        if hasattr(_thread_locals, 'request'):
            del _thread_locals.request
        return response


class GlobalErrorHandlerMiddleware(MiddlewareMixin):
    
    def __init__(self, get_response):
        super().__init__(get_response)
    
    def process_request(self, request):
        """
        Проверка доступа ДО вызова view
        """
        skip_urls = [
            '/login/', '/logout/', '/register/', '/error-page/', 
            '/static/', '/media/', '/api/', '/password-reset/'
        ]
        for skip_url in skip_urls:
            if request.path.startswith(skip_url):
                return None
        
        protection_needed = self.check_protection(request.path)
        
        if protection_needed:
            if not request.user.is_authenticated:
                return redirect(f'/login/?next={request.path}')
            
            if not self.check_role_permission(request.user, protection_needed):
                return self.handle_permission_error(
                    request, 
                    self.get_permission_error_message(protection_needed, request.user)
                )
        
        return None
    
    def process_response(self, request, response):
        """
        Обработка ответа после выполнения view
        """
        if request.path.startswith('/api/'):
            return response
        
        if request.path.startswith('/error-page/') or request.path.startswith('/login/'):
            return response
        
        if response.status_code == 405:
            protection_needed = self.check_protection(request.path)
            if protection_needed:
                if not request.user.is_authenticated:
                    return redirect(f'/login/?next={request.path}')
                if not self.check_role_permission(request.user, protection_needed):
                    return self.handle_permission_error(
                        request, 
                        self.get_permission_error_message(protection_needed, request.user)
                    )
        
        if response.status_code >= 400 and response.status_code != 302:
            return self.handle_http_error(request, response)
        
        return response
    
    def process_exception(self, request, exception):
        if isinstance(exception, PermissionDenied):
            return self.handle_permission_error(request, str(exception))
        
        logger.error(f"Error in {request.path}: {exception}\n{traceback.format_exc()}")
        return self.handle_server_error(request)
    
    def check_protection(self, path):
        """
        Проверяет, нужна ли защита для URL и какая именно
        """
        public_urls = [
            '/',          
            '/courses/', 
            '/course/',   
            '/details-course/', 
            '/search/',    
            '/about/',    
            '/teachers/',  
            '/feedback/',  
            '/register/',  
            '/login/',     
            '/logout/',    
        ]
        
        for public_url in public_urls:
            if public_url == '/':
                if path == '/':
                    return None
            else:
                if path.startswith(public_url):
                    return None
        
        if path.startswith('/admin/') or path.startswith('/admin-panel/'):
            return 'admin'
        
        if path.startswith('/methodist/'):
            return 'methodist'
        
        if path.startswith('/teacher/'):
            return 'teacher'
        
        if path.startswith('/listener/'):
            return 'auth'
        
        auth_urls = [
            '/profile/', '/dashboard/', '/my-courses/', '/favorites/',
            '/certificates/', '/payment/'
        ]
        for auth_url in auth_urls:
            if path.startswith(auth_url):
                return 'auth'
        
        return 'auth'
    
    def check_role_permission(self, user, protection_needed):
        """
        Проверяет, имеет ли пользователь права доступа по роли
        """
        user_role = user.role.role_name.lower() if user.role and user.role.role_name else None
        
        if protection_needed == 'admin':
            return user_role == 'администратор' or user.is_staff
        
        elif protection_needed == 'methodist':
            return user_role == 'методист' and user.is_verified
        
        elif protection_needed == 'teacher':
            return user_role == 'преподаватель' and user.is_verified
        
        elif protection_needed == 'auth':
            return user.is_authenticated
        
        return False
    
    def get_permission_error_message(self, protection_needed, user):
        user_role = user.role.role_name if user.role else "неизвестная"
        
        messages = {
            'admin': f'Доступ разрешен только администраторам. Ваша роль: {user_role}',
            'methodist': f'Доступ разрешен только методистам. Ваша роль: {user_role}',
            'teacher': f'Доступ разрешен только преподавателям. Ваша роль: {user_role}',
            'auth': 'Необходимо авторизоваться для доступа к этой странице',
        }
        return messages.get(protection_needed, f'У вас недостаточно прав. Ваша роль: {user_role}')
    
    def handle_http_error(self, request, response):
        status_code = response.status_code
        
        return render(request, 'errors/general_error.html', {
            'error_code': status_code,
            'error_title': self.get_error_title(status_code),
            'error_message': self.get_error_message(status_code),
            'error_icon': self.get_error_icon(status_code)
        }, status=status_code)
    
    def handle_permission_error(self, request, message):
        return render(request, 'errors/general_error.html', {
            'error_code': 403,
            'error_title': 'Доступ запрещен',
            'error_message': message,
            'error_icon': 'fas fa-lock'
        }, status=403)
    
    def handle_server_error(self, request):
        return render(request, 'errors/general_error.html', {
            'error_code': 500,
            'error_title': 'Ошибка сервера',
            'error_message': 'Произошла техническая ошибка. Пожалуйста, попробуйте позже.',
            'error_icon': 'fas fa-exclamation-triangle'
        }, status=500)
    
    def get_error_title(self, code):
        titles = {
            400: 'Неверный запрос',
            401: 'Не авторизован',
            403: 'Доступ запрещен',
            404: 'Страница не найдена',
            405: 'Метод не разрешен',
            500: 'Ошибка сервера',
        }
        return titles.get(code, 'Ошибка')
    
    def get_error_message(self, code):
        messages = {
            400: 'Сервер не может обработать запрос.',
            401: 'Необходимо авторизоваться.',
            403: 'У вас недостаточно прав.',
            404: 'Страница не найдена.',
            405: 'Метод запроса не поддерживается.',
            500: 'Ошибка на сервере. Мы уже работаем над её исправлением.',
        }
        return messages.get(code, 'Произошла ошибка.')
    
    def get_error_icon(self, code):
        icons = {
            400: 'fas fa-exclamation-triangle',
            401: 'fas fa-sign-in-alt',
            403: 'fas fa-lock',
            404: 'fas fa-search',
            405: 'fas fa-ban',
            500: 'fas fa-exclamation-circle',
        }
        return icons.get(code, 'fas fa-exclamation-circle')