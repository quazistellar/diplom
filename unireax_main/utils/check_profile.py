from django.shortcuts import render
from django.contrib import messages


def render_profile(request, user, context=None):
    """
    Универсальная функция для рендеринга профиля
    Выбирает нужный шаблон в зависимости от статуса верификации
    """
    if context is None:
        context = {}
    
    context['user'] = user
    
    if not user.is_verified:
        return render(request, 'unverified_profile.html', context)
    
    role_name = user.role.role_name.lower() if user.role else ''
    
    if role_name == 'администратор':
        return render(request, 'admin_profile.html', context)
    elif role_name == 'методист':
        return render(request, 'methodist_profile.html', context)
    elif role_name == 'преподаватель':
        return render(request, 'teacher_profile.html', context)
    elif role_name == 'слушатель курсов':
        return render(request, 'listener_profile.html', context)
    else:
        return render(request, 'main_page.html', context)