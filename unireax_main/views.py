from django.shortcuts import render
from .models import User, Course

def main_page(request):
    """функция для отображения главной страницы с популярными курсами"""
    students_count = User.objects.filter(role__role_name='слушатель курсов').count()
    courses_count = Course.objects.filter(is_active=True).count()
    
    courses = Course.objects.filter(is_active=True)[:12]
    
    theme = request.COOKIES.get('theme', 'dark')
    
    context = {
        'courses': courses,
        'students_count': students_count,
        'courses_count': courses_count,
        'theme': theme,
        'is_dark': theme == 'dark'
    }
    
    return render(request, 'main_page.html', context)