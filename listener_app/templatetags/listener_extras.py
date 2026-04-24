from django.contrib.staticfiles import finders
from django import template

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Получить значение из словаря по ключу"""
    if dictionary is None:
        return None
    return dictionary.get(key)


@register.filter
def sum_attribute(queryset, attribute):
    """Суммирует значения атрибута в queryset"""
    if not queryset:
        return 0
    total = 0
    for item in queryset:
        value = getattr(item, attribute, 0)
        if value:
            total += value
    return total


@register.filter
def multiply(value, arg):
    """Умножает значение на аргумент"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def divide(value, arg):
    """Делит значение на аргумент"""
    try:
        if float(arg) == 0:
            return 0
        return float(value) / float(arg)
    except (ValueError, TypeError):
        return 0


@register.filter
def percentage(value, total):
    """Вычисляет процент"""
    try:
        if float(total) == 0:
            return 0
        return (float(value) / float(total)) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def static_exists(path):
    """
    Проверяет, существует ли статический файл.
    Использование: {% if 'images/write.png'|static_exists %}
    """
    try:
        result = finders.find(path)
        return result is not None
    except Exception:
        return False