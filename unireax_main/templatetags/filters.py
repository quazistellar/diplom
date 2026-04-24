from django import template
from django.db.models import Q
from ..models import CourseCategory, CourseType

register = template.Library()

@register.simple_tag
def get_course_categories():
    """Получить все категории курсов"""
    return CourseCategory.objects.all()

@register.simple_tag
def get_course_types():
    """Получить все типы курсов"""
    return CourseType.objects.all()

@register.simple_tag
def get_active_filters_count(request):
    """Подсчитать количество активных фильтров"""
    count = 0
    if request.GET.get('search'):
        count += 1
    if request.GET.getlist('category'):
        count += len(request.GET.getlist('category'))
    if request.GET.getlist('type'):
        count += len(request.GET.getlist('type'))
    if request.GET.get('has_certificate'):
        count += 1
    if request.GET.get('free_only'):
        count += 1
    if request.GET.get('sort_by'):
        count += 1
    if request.GET.get('price_min'):
        count += 1
    if request.GET.get('price_max'):
        count += 1
    return count

@register.simple_tag
def get_filter_url(request, filter_type, filter_value=None, remove=False):
    """Сгенерировать URL с применением/удалением фильтра"""
    params = request.GET.copy()
    
    if remove:
        if filter_type == 'search':
            params.pop('search', None)
        elif filter_type == 'category':
            categories = params.getlist('category')
            if filter_value in categories:
                categories.remove(filter_value)
                params.setlist('category', categories)
        elif filter_type == 'type':
            types = params.getlist('type')
            if filter_value in types:
                types.remove(filter_value)
                params.setlist('type', types)
        elif filter_type == 'has_certificate':
            params.pop('has_certificate', None)
        elif filter_type == 'free_only':
            params.pop('free_only', None)
        elif filter_type == 'price_min':
            params.pop('price_min', None)
        elif filter_type == 'price_max':
            params.pop('price_max', None)
        elif filter_type == 'sort':
            params.pop('sort_by', None)
        elif filter_type == 'view':
            params.pop('view', None)
    else:
        if filter_type == 'search':
            params['search'] = filter_value
        elif filter_type == 'category':
            params.appendlist('category', filter_value)
        elif filter_type == 'type':
            params.appendlist('type', filter_value)
        elif filter_type == 'has_certificate':
            params['has_certificate'] = 'true'
        elif filter_type == 'free_only':
            params['free_only'] = 'true'
        elif filter_type == 'price_min':
            params['price_min'] = filter_value
        elif filter_type == 'price_max':
            params['price_max'] = filter_value
        elif filter_type == 'sort':
            params['sort_by'] = filter_value
        elif filter_type == 'view':
            params['view'] = filter_value
    
    return f'?{params.urlencode()}' if params else '?'

@register.simple_tag
def clear_all_filters_url(request):
    """Сгенерировать URL для сброса всех фильтров"""
    params = request.GET.copy()

    view = params.get('view')
    params.clear()
    if view:
        params['view'] = view
    
    return f'?{params.urlencode()}' if params else '?'

@register.filter
def is_selected_category(category_id, request):
    """Проверить, выбрана ли категория"""
    return str(category_id) in request.GET.getlist('category')

@register.filter
def is_selected_type(type_id, request):
    """Проверить, выбран ли тип"""
    return str(type_id) in request.GET.getlist('type')

@register.filter
def has_active_filters(request):
    """Проверить, есть ли активные фильтры"""
    return (
        request.GET.get('search') or
        request.GET.getlist('category') or
        request.GET.getlist('type') or
        request.GET.get('has_certificate') or
        request.GET.get('free_only') or
        request.GET.get('price_min') or
        request.GET.get('price_max') or
        request.GET.get('sort_by')
    )