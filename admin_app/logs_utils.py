from unireax_main.utils.middleware import get_current_request
import json
import logging
import weakref
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone
from django.db.models.signals import post_save, pre_save, pre_delete
from django.dispatch import receiver

logger = logging.getLogger(__name__)
previous_values = weakref.WeakKeyDictionary()

EXCLUDED_MODELS = {
    'sessions': ['session'],
    'admin': ['logentry'],
}

EXCLUDED_FIELDS = {
    'auth.user': ['last_login', 'password'],
    'unireax_main.user': ['last_login', 'password'],
}

def is_admin_request():
    """Проверяет, является ли запрос админским"""
    request = get_current_request()
    return request and request.path.startswith('/admin/')

def should_log_model(sender):
    """Проверяет, нужно ли логировать данную модель"""
    model_name = sender._meta.model_name
    app_label = sender._meta.app_label
    
    if app_label in EXCLUDED_MODELS:
        if model_name in EXCLUDED_MODELS[app_label]:
            return False
    
    if sender == LogEntry:
        return False
    
    return True

def should_log_field(instance, field_name):
    """Проверяет, нужно ли логировать данное поле"""
    model_key = f"{instance._meta.app_label}.{instance._meta.model_name}"
    
    if model_key in EXCLUDED_FIELDS:
        if field_name in EXCLUDED_FIELDS[model_key]:
            return False
    
    return True

def safe_log_action(user, obj, action_flag, change_message=''):
    """Безопасная запись лога"""
    try:
        if user is None or not user.is_authenticated:
            return None
            
        if not should_log_model(type(obj)):
            return None
            
        log_entry = LogEntry.objects.create(
            user=user,
            content_type=ContentType.objects.get_for_model(obj),
            object_id=str(obj.pk),
            object_repr=str(obj)[:200],
            action_flag=action_flag,
            change_message=change_message,
            action_time=timezone.now()
        )
        return log_entry
    except Exception as e:
        logger.debug(f"Ошибка логирования: {e}")
        return None

def create_change_message(instance, updated_fields, created=False):
    """Создает читаемое сообщение об изменениях"""
    if created:
        changes = []
        for field in updated_fields:
            if should_log_field(instance, field):
                value = getattr(instance, field)
                if len(str(value)) > 50:
                    value = str(value)[:50] + '...'
                changes.append(f"{field}: '{value}'")
        return ', '.join(changes)
    else:
        changes = []
        for field in updated_fields:
            if should_log_field(instance, field):
                old_value = previous_values.get(instance, {}).get(field)
                new_value = getattr(instance, field)
                if old_value and len(str(old_value)) > 50:
                    old_value = str(old_value)[:50] + '...'
                if new_value and len(str(new_value)) > 50:
                    new_value = str(new_value)[:50] + '...'
                changes.append(f"{field}: '{old_value}' -> '{new_value}'")
        return ', '.join(changes)

def is_duplicate_log_entry(change_message):
    """Проверяет дубликаты JSON логов Django"""
    try:
        data = json.loads(change_message)
        if isinstance(data, list):
            for item in data:
                if 'added' in item or 'changed' in item or 'deleted' in item:
                    return True
        return False
    except (json.JSONDecodeError, TypeError, IndexError):
        return False

@receiver(pre_save)
def capture_pre_save_state(sender, instance, **kwargs):
    """Захватывает состояние объекта до сохранения"""
    if not should_log_model(sender):
        return
    
    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
            previous_values[instance] = {
                field.name: getattr(old_instance, field.name) 
                for field in instance._meta.fields
                if should_log_field(instance, field.name)
            }
        except sender.DoesNotExist:
            previous_values[instance] = {}

@receiver(post_save)
def log_model_post_save(sender, instance, created, **kwargs):
    """Логирует создание и изменение объектов"""
    if not should_log_model(sender):
        return

    action_flag = ADDITION if created else CHANGE

    if created:
        updated_fields = [
            field.name for field in instance._meta.fields 
            if field.name != 'id' and should_log_field(instance, field.name)
        ]
        if not updated_fields:
            return
        change_message = create_change_message(instance, updated_fields, created=True)
    else:
        old_values = previous_values.get(instance, {})
        updated_fields = [
            field.name for field in instance._meta.fields 
            if field.name in old_values and 
            old_values.get(field.name) != getattr(instance, field.name) and
            should_log_field(instance, field.name)
        ]
        
        if not updated_fields: 
            if instance in previous_values:
                del previous_values[instance]
            return
            
        change_message = create_change_message(instance, updated_fields)

    request = get_current_request()
    user = request.user if request and hasattr(request, 'user') else None
    
    if is_admin_request():
        change_message = f"[Админка] {change_message}"
    
    safe_log_action(
        user=user,
        obj=instance,
        action_flag=action_flag,
        change_message=change_message
    )

    if instance in previous_values:
        del previous_values[instance]

@receiver(pre_delete)
def log_model_pre_delete(sender, instance, **kwargs):
    """Логирует удаление объектов"""
    if not should_log_model(sender):
        return
    
    request = get_current_request()
    user = request.user if request and hasattr(request, 'user') else None
    
    object_repr = str(instance)
    
    if is_admin_request():
        change_message = f'[Админка] Объект удален: {object_repr}'
    else:
        change_message = f'Объект удален: {object_repr}'
    
    safe_log_action(
        user=user,
        obj=instance,
        action_flag=DELETION,
        change_message=change_message
    )