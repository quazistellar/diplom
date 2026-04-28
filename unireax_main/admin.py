from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.contrib import messages
from django import forms
from django.utils.translation import gettext_lazy as _
from .models import *
from .utils.assignment_utils import update_assignment_status
from django.contrib.admin.models import LogEntry, ADDITION, CHANGE, DELETION
from django.utils.html import format_html
from django.db.models import Q
import json

class CustomUserCreationForm(UserCreationForm):
    """Форма для создания нового пользователя"""
    
    class Meta(UserCreationForm.Meta):
        model = User
        fields = ('username', 'email', 'first_name', 'last_name', 'patronymic', 'role')
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].required = True
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'vTextField'})


class CustomUserChangeForm(UserChangeForm):
    """Форма для редактирования пользователя"""
    
    class Meta(UserChangeForm.Meta):
        model = User
        fields = '__all__'
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            self.fields['password'].required = False
            self.fields['password'].help_text = (
                "Зашифрованный пароль. Можно сбросить его, нажав на кнопку 'Сбросить пароль' выше."
            )


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    form = CustomUserChangeForm
    add_form = CustomUserCreationForm
    
    list_display = ('id', 'username', 'email', 'get_full_name', 'role', 'is_active', 'is_verified', 'is_staff')
    list_filter = ('is_active', 'is_verified', 'role', 'is_staff', 'is_superuser', 'groups')
    search_fields = ('username', 'email', 'first_name', 'last_name', 'patronymic')
    readonly_fields = ('last_login', 'date_joined')
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'password1', 'password2', 
                      'first_name', 'last_name', 'patronymic', 'role'),
        }),
    )
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        (_('Основная информация'), {
            'fields': ('first_name', 'last_name', 'patronymic', 'email')
        }),
        (_('Профессиональная информация'), {
            'fields': ('role', 'position', 'educational_institution', 'certificate_file'),
            'classes': ('collapse',)
        }),
        (_('Разрешения пользователя'), {
            'fields': ('is_active', 'is_verified', 'is_staff', 'is_superuser', 
                      'groups', 'user_permissions'),
            'classes': ('collapse',)
        }),
        (_('Настройки интерфейса'), {
            'fields': ('is_light_theme',)
        }),
        (_('Даты'), {
            'fields': ('last_login', 'date_joined'),
            'classes': ('collapse',)
        }),
    )
    
    def get_full_name(self, obj):
        return obj.get_full_name() if hasattr(obj, 'get_full_name') else obj.full_name
    get_full_name.short_description = 'ФИО'
    get_full_name.admin_order_field = 'last_name'
    
    def save_model(self, request, obj, form, change):
        """Сохранение модели"""
        try:
            super().save_model(request, obj, form, change)
        except Exception as e:
            messages.error(request, f'Ошибка при сохранении пользователя: {str(e)}')
            raise


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ('id', 'role_name')
    search_fields = ('role_name',)
    ordering = ('role_name',)


@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    list_display = ('id', 'course_category_name')
    search_fields = ('course_category_name',)
    ordering = ('course_category_name',)


@admin.register(CourseType)
class CourseTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'course_type_name', 'course_type_description')
    search_fields = ('course_type_name',)


@admin.register(AssignmentStatus)
class AssignmentStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'assignment_status_name')
    search_fields = ('assignment_status_name',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'course_name', 'course_category', 'course_type', 'course_price', 'is_active', 'created_at')
    list_filter = ('is_active', 'has_certificate', 'is_completed', 'course_category', 'course_type')
    search_fields = ('course_name', 'course_description')
    autocomplete_fields = ['created_by']
    readonly_fields = ('created_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('course_name', 'course_description', 'course_category', 'course_type')
        }),
        ('Характеристики курса', {
            'fields': ('course_price', 'course_hours', 'course_max_places', 'has_certificate')
        }),
        ('Медиа и ссылки', {
            'fields': ('course_photo_path', 'code_link'),
            'classes': ('collapse',)
        }),
        ('Статус', {
            'fields': ('is_active', 'is_completed', 'created_by', 'created_at')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)


@admin.register(CourseTeacher)
class CourseTeacherAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'teacher', 'start_date', 'is_active')
    list_filter = ('is_active', 'start_date')
    search_fields = ('course__course_name', 'teacher__username', 'teacher__last_name')
    autocomplete_fields = ['course', 'teacher']
    date_hierarchy = 'start_date'


@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    list_display = ('id', 'lecture_name', 'course', 'lecture_order', 'is_active', 'created_at')
    list_filter = ('is_active', 'course')
    search_fields = ('lecture_name', 'lecture_content')
    autocomplete_fields = ['course']
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('lecture_name', 'lecture_content', 'course', 'lecture_order')
        }),
        ('Файлы', {
            'fields': ('lecture_document_path',)
        }),
        ('Статус', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(PracticalAssignment)
class PracticalAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'practical_assignment_name', 'lecture', 'grading_type', 'max_score', 'assignment_deadline', 'is_active')
    list_filter = ('is_active', 'grading_type', 'lecture__course')
    search_fields = ('practical_assignment_name', 'practical_assignment_description')
    autocomplete_fields = ['lecture']
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('practical_assignment_name', 'practical_assignment_description', 'lecture')
        }),
        ('Оценивание', {
            'fields': ('grading_type', 'max_score', 'passing_score', 'assignment_criteria')
        }),
        ('Сроки', {
            'fields': ('assignment_deadline', 'is_can_pin_after_deadline')
        }),
        ('Файлы и статус', {
            'fields': ('assignment_document_path', 'is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(UserPracticalAssignment)
class UserPracticalAssignmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'practical_assignment', 'attempt_number', 'submission_status', 'submission_date', 'submitted_at')
    list_filter = ('submission_status', 'submission_date')
    search_fields = ('user__username', 'user__last_name', 'practical_assignment__practical_assignment_name')
    autocomplete_fields = ['user', 'practical_assignment', 'submission_status']
    readonly_fields = ('submitted_at',)
    date_hierarchy = 'submission_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'practical_assignment', 'attempt_number')
        }),
        ('Статус и даты', {
            'fields': ('submission_status', 'submission_date', 'submitted_at')
        }),
        ('Комментарий', {
            'fields': ('comment',)
        }),
    )


@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'registration_date', 'status_course', 'is_active', 'payment_date', 'completion_date')
    list_filter = ('status_course', 'is_active', 'registration_date')
    search_fields = ('user__username', 'user__last_name', 'course__course_name')
    autocomplete_fields = ['user', 'course']
    readonly_fields = ('enrolled_at',)
    date_hierarchy = 'registration_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'course')
        }),
        ('Статус', {
            'fields': ('status_course', 'is_active', 'registration_date', 'enrolled_at')
        }),
        ('Финансы', {
            'fields': ('course_price', 'payment_date'),
            'classes': ('collapse',)
        }),
        ('Завершение', {
            'fields': ('completion_date',),
            'classes': ('collapse',)
        }),
    )


@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_practical_assignment', 'get_user', 'get_assignment', 'score', 'is_passed', 'given_by', 'given_at')
    list_filter = ('is_passed', 'given_at')
    search_fields = ('user_practical_assignment__user__username', 'comment_feedback')
    autocomplete_fields = ['user_practical_assignment', 'given_by']
    readonly_fields = ('given_at',)
    
    fieldsets = (
        ('Сдача задания', {
            'fields': ('user_practical_assignment',)
        }),
        ('Оценка', {
            'fields': ('score', 'is_passed', 'comment_feedback')
        }),
        ('Информация о проверке', {
            'fields': ('given_by', 'given_at')
        }),
    )
    
    def get_user(self, obj):
        return obj.user_practical_assignment.user if obj.user_practical_assignment else None
    get_user.short_description = 'Студент'
    get_user.admin_order_field = 'user_practical_assignment__user__last_name'
    
    def get_assignment(self, obj):
        return obj.user_practical_assignment.practical_assignment if obj.user_practical_assignment else None
    get_assignment.short_description = 'Задание'
    get_assignment.admin_order_field = 'user_practical_assignment__practical_assignment__practical_assignment_name'
    
    def save_model(self, request, obj, form, change):
        try:
            if not obj.given_by:
                obj.given_by = request.user
            
            super().save_model(request, obj, form, change)
            
            if obj.user_practical_assignment:
                try:
                    new_status = update_assignment_status(obj.user_practical_assignment, obj)
                    obj.user_practical_assignment.refresh_from_db()
                    
                    messages.success(
                        request, 
                        f"Статус задания обновлен на '{obj.user_practical_assignment.submission_status.assignment_status_name}'"
                    )
                except Exception as e:
                    messages.warning(request, f"Задание сохранено, но статус не обновлен: {str(e)}")
                    
        except Exception as e:
            messages.error(request, f"Ошибка при сохранении: {str(e)}")
            raise


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('id', 'course', 'user', 'rating', 'publish_date', 'is_approved')
    list_filter = ('is_approved', 'rating', 'publish_date')
    search_fields = ('user__username', 'course__course_name', 'comment_review')
    autocomplete_fields = ['course', 'user']
    date_hierarchy = 'publish_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('course', 'user', 'rating')
        }),
        ('Отзыв', {
            'fields': ('comment_review',)
        }),
        ('Модерация', {
            'fields': ('is_approved', 'publish_date')
        }),
    )


@admin.register(AnswerType)
class AnswerTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'answer_type_name', 'answer_type_description')
    search_fields = ('answer_type_name',)


@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ('id', 'test_name', 'lecture', 'is_final', 'grading_form', 'passing_score', 'max_attempts', 'is_active')
    list_filter = ('is_final', 'grading_form', 'is_active', 'lecture__course')
    search_fields = ('test_name', 'test_description')
    autocomplete_fields = ['lecture']
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('test_name', 'test_description', 'lecture', 'is_final')
        }),
        ('Оценивание', {
            'fields': ('grading_form', 'passing_score', 'max_attempts')
        }),
        ('Статус', {
            'fields': ('is_active', 'created_at', 'updated_at')
        }),
    )


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('id', 'question_text_short', 'test', 'answer_type', 'question_score', 'question_order')
    list_filter = ('answer_type', 'test')
    search_fields = ('question_text',)
    autocomplete_fields = ['test', 'answer_type']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('test', 'answer_type', 'question_order')
        }),
        ('Текст вопроса', {
            'fields': ('question_text',)
        }),
        ('Оценивание', {
            'fields': ('question_score', 'correct_text')
        }),
    )
    
    def question_text_short(self, obj):
        return (obj.question_text[:50] + '...') if len(obj.question_text) > 50 else obj.question_text
    question_text_short.short_description = 'Текст вопроса'


@admin.register(ChoiceOption)
class ChoiceOptionAdmin(admin.ModelAdmin):
    list_display = ('id', 'option_text_short', 'question', 'is_correct')
    list_filter = ('is_correct', 'question__test')
    search_fields = ('option_text',)
    autocomplete_fields = ['question']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('question', 'option_text', 'is_correct')
        }),
    )
    
    def option_text_short(self, obj):
        return (obj.option_text[:50] + '...') if len(obj.option_text) > 50 else obj.option_text
    option_text_short.short_description = 'Текст варианта'


@admin.register(MatchingPair)
class MatchingPairAdmin(admin.ModelAdmin):
    list_display = ('id', 'left_text_short', 'right_text_short', 'question')
    search_fields = ('left_text', 'right_text')
    autocomplete_fields = ['question']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('question', 'left_text', 'right_text')
        }),
    )
    
    def left_text_short(self, obj):
        return (obj.left_text[:30] + '...') if len(obj.left_text) > 30 else obj.left_text
    left_text_short.short_description = 'Левый текст'
    
    def right_text_short(self, obj):
        return (obj.right_text[:30] + '...') if len(obj.right_text) > 30 else obj.right_text
    right_text_short.short_description = 'Правый текст'


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'question', 'attempt_number', 'score', 'answer_date')
    list_filter = ('answer_date',)
    search_fields = ('user__username', 'question__question_text')
    autocomplete_fields = ['user', 'question']
    date_hierarchy = 'answer_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'question', 'attempt_number')
        }),
        ('Ответ', {
            'fields': ('answer_text',)
        }),
        ('Результат', {
            'fields': ('score', 'answer_date')
        }),
    )


@admin.register(UserSelectedChoice)
class UserSelectedChoiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_answer', 'choice_option', 'selected_at')
    autocomplete_fields = ['user_answer', 'choice_option']
    readonly_fields = ('selected_at',)


@admin.register(UserMatchingAnswer)
class UserMatchingAnswerAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_answer', 'matching_pair', 'user_selected_right_text_short', 'selected_at')
    autocomplete_fields = ['user_answer', 'matching_pair']
    readonly_fields = ('selected_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user_answer', 'matching_pair')
        }),
        ('Ответ', {
            'fields': ('user_selected_right_text',)
        }),
        ('Дата', {
            'fields': ('selected_at',)
        }),
    )
    
    def user_selected_right_text_short(self, obj):
        return (obj.user_selected_right_text[:30] + '...') if len(obj.user_selected_right_text) > 30 else obj.user_selected_right_text
    user_selected_right_text_short.short_description = 'Выбранный текст'


@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'test', 'attempt_number', 'final_score', 'is_passed', 'completion_date', 'time_spent')
    list_filter = ('is_passed', 'completion_date')
    search_fields = ('user__username', 'test__test_name')
    autocomplete_fields = ['user', 'test']
    date_hierarchy = 'completion_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'test', 'attempt_number')
        }),
        ('Результаты', {
            'fields': ('final_score', 'is_passed', 'time_spent')
        }),
        ('Дата', {
            'fields': ('completion_date',)
        }),
    )


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('id', 'certificate_number', 'user_course', 'issue_date', 'certificate_file_path')
    search_fields = ('certificate_number', 'user_course__user__username')
    autocomplete_fields = ['user_course']
    readonly_fields = ('certificate_number',)
    date_hierarchy = 'issue_date'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user_course', 'certificate_number', 'issue_date')
        }),
        ('Файл', {
            'fields': ('certificate_file_path',)
        }),
    )

@admin.register(AssignmentSubmissionFile)
class AssignmentSubmissionFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'file_name', 'user_assignment', 'file_size_mb', 'uploaded_at', 'description')
    list_filter = ('uploaded_at',)
    search_fields = ('file_name', 'description')
    autocomplete_fields = ['user_assignment']
    readonly_fields = ('uploaded_at', 'file_size')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user_assignment', 'file_name', 'description')
        }),
        ('Файл', {
            'fields': ('file', 'file_size', 'uploaded_at')
        }),
    )
    
    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024*1024):.2f} МБ"
        return '0 МБ'
    file_size_mb.short_description = 'Размер'

@admin.register(TeacherAssignmentFile)
class TeacherAssignmentFileAdmin(admin.ModelAdmin):
    list_display = ('id', 'original_filename', 'practical_assignment', 'file_type', 'uploaded_by', 'uploaded_at', 'is_active')
    list_filter = ('file_type', 'is_active', 'uploaded_at')
    search_fields = ('original_filename',)
    autocomplete_fields = ['practical_assignment', 'uploaded_by']
    readonly_fields = ('uploaded_at',)
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('practical_assignment', 'original_filename', 'file_type')
        }),
        ('Файл', {
            'fields': ('file_path', 'file_size')
        }),
        ('Автор и статус', {
            'fields': ('uploaded_by', 'uploaded_at', 'is_active')
        }),
    )
    
    def save_model(self, request, obj, form, change):
        if not change:
            obj.uploaded_by = request.user
        super().save_model(request, obj, form, change)
    
    def file_size_mb(self, obj):
        if obj.file_size:
            return f"{obj.file_size / (1024*1024):.2f} МБ"
        return '0 МБ'
    file_size_mb.short_description = 'Размер'


@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'code', 'created_at', 'expires_at', 'is_used', 'is_valid')
    list_filter = ('is_used', 'created_at')
    search_fields = ('user__username', 'user__email', 'code')
    autocomplete_fields = ['user']
    readonly_fields = ('created_at', 'expires_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'code')
        }),
        ('Статус', {
            'fields': ('is_used', 'created_at', 'expires_at')
        }),
    )
    
    def is_valid(self, obj):
        return obj.is_valid() if hasattr(obj, 'is_valid') else False
    is_valid.short_description = 'Действителен'
    is_valid.boolean = True


class LogEntryAdmin(admin.ModelAdmin):
    list_display = ('action_time', 'user', 'content_type_display', 'object_repr', 'action_flag_display', 'change_message_display')
    list_filter = ('action_flag', 'user', 'content_type')
    search_fields = ('object_repr', 'change_message')
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag_display', 'change_message_display')
    date_hierarchy = 'action_time'
    ordering = ('-action_time',)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.exclude(
            Q(content_type__app_label='sessions') |
            Q(content_type__app_label='admin', content_type__model='logentry')
        )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def action_flag_display(self, obj):
        if obj.action_flag == ADDITION:
            return format_html('<span style="color: #27ae60;">Добавлено</span>')
        elif obj.action_flag == CHANGE:
            return format_html('<span style="color: #f39c12;">Изменено</span>')
        elif obj.action_flag == DELETION:
            return format_html('<span style="color: #e74c3c;">Удалено</span>')
        return ""
    action_flag_display.short_description = "Действие"

    def content_type_display(self, obj):
        return f"{obj.content_type.app_label}.{obj.content_type.model}"
    content_type_display.short_description = "Модель"

    def change_message_display(self, obj):
        if obj.change_message:
            return obj.change_message[:200] + ('...' if len(obj.change_message) > 200 else '')
        return "—"
    change_message_display.short_description = "Сообщение"


if not admin.site.is_registered(LogEntry):
    admin.site.register(LogEntry, LogEntryAdmin)


@admin.register(TeacherApplication)
class TeacherApplicationAdmin(admin.ModelAdmin):
    list_display = ('id', 'teacher', 'course', 'get_status_name', 'created_at')
    list_filter = ('status', 'created_at', 'course')
    search_fields = ('teacher__username', 'teacher__last_name', 'teacher__email', 'course__course_name')
    autocomplete_fields = ['teacher', 'course', 'status']
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('teacher', 'course')
        }),
        ('Статус', {
            'fields': ('status', 'comment')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_status_name(self, obj):
        return obj.status.name if obj.status else '-'
    get_status_name.short_description = 'Статус'
    get_status_name.admin_order_field = 'status__name'
    
    def save_model(self, request, obj, form, change):
        old_status_code = None
        if change:
            try:
                old_obj = TeacherApplication.objects.get(pk=obj.pk)
                old_status_code = old_obj.status.code if old_obj.status else None
            except TeacherApplication.DoesNotExist:
                pass
        
        super().save_model(request, obj, form, change)
        
        if change and old_status_code == 'pending' and obj.status and obj.status.code != 'pending':
            if obj.status.code == 'approved':
                obj.approve(request)
            elif obj.status.code == 'rejected':
                obj.reject(obj.comment, request)
    
    actions = ['approve_selected', 'reject_selected']
    
    def approve_selected(self, request, queryset):
        from unireax_main.models import ApplicationStatus
        pending_status = ApplicationStatus.objects.get(code='pending')
        count = queryset.filter(status=pending_status).count()
        for application in queryset.filter(status=pending_status):
            application.approve(request)
        self.message_user(request, f'Одобрено {count} заявок.')
    approve_selected.short_description = 'Одобрить выбранные заявки'
    
    def reject_selected(self, request, queryset):
        from unireax_main.models import ApplicationStatus
        pending_status = ApplicationStatus.objects.get(code='pending')
        count = queryset.filter(status=pending_status).count()
        for application in queryset.filter(status=pending_status):
            application.reject(request=request)
        self.message_user(request, f'Отклонено {count} заявок.')
    reject_selected.short_description = 'Отклонить выбранные заявки'


@admin.register(LoginAttempt)
class LoginAttemptAdmin(admin.ModelAdmin):
    list_display = ('id', 'username', 'ip_address', 'success', 'attempt_time')
    list_filter = ('success', 'attempt_time')
    search_fields = ('username', 'ip_address')
    readonly_fields = ('attempt_time',)
    date_hierarchy = 'attempt_time'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
    
    def has_delete_permission(self, request, obj=None):
        return False
    

@admin.register(FavoriteCourse)
class FavoriteCourseAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'course', 'added_at')
    list_filter = ('added_at',)
    search_fields = ('user__username', 'user__last_name', 'user__email', 'course__course_name')
    autocomplete_fields = ['user', 'course']
    readonly_fields = ('added_at',)
    date_hierarchy = 'added_at'
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('user', 'course')
        }),
        ('Дата', {
            'fields': ('added_at',),
            'classes': ('collapse',)
        }),
    )

@admin.register(ApplicationStatus)
class ApplicationStatusAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name')
    search_fields = ('code', 'name')

@admin.register(PostType)
class PostTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'code', 'name')
    search_fields = ('code', 'name')

@admin.register(CoursePost)
class CoursePostAdmin(admin.ModelAdmin):
    list_display = ('id', 'title', 'course', 'author', 'get_post_type_name', 'is_pinned', 'is_active', 'created_at')
    list_filter = ('post_type', 'is_pinned', 'is_active', 'created_at')
    search_fields = ('title', 'content', 'course__course_name', 'author__username')
    autocomplete_fields = ['course', 'author', 'post_type']
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('title', 'content', 'course', 'author')
        }),
        ('Тип и статус', {
            'fields': ('post_type', 'is_pinned', 'is_active')
        }),
        ('Даты', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_post_type_name(self, obj):
        return obj.post_type.name if obj.post_type else '-'
    get_post_type_name.short_description = 'Тип поста'
    get_post_type_name.admin_order_field = 'post_type__name'
