from rest_framework import permissions

class IsListenerPermission(permissions.BasePermission):
    """Разрешает доступ только пользователям с ролью 'слушатель курсов'"""
    def has_permission(self, request, view):

        if not request.user or not request.user.is_authenticated:
            return False
        
        if hasattr(request.user, 'role') and request.user.role:
            role_name = request.user.role.role_name.lower()
            return role_name in ['слушатель курсов', 'слушатель']
        
        return False