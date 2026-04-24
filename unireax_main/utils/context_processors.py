def user_permissions(request):
    """данная функция добавляет в шаблоны информацию о пользователе"""
    return {
        'is_staff': request.user.is_staff if request.user.is_authenticated else False,
        'is_authenticated': request.user.is_authenticated,
    }