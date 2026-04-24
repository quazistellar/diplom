import json
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from django.contrib.auth import authenticate, logout
from django.db.models import Q, Count, Avg
from django.shortcuts import get_object_or_404
from .models import *
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth import logout
import traceback
from .serializers import *
import logging
from django.utils import timezone
from rest_framework.permissions import BasePermission
from django.http import HttpResponse
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from io import BytesIO
from django.db.models import Case, When, Value, IntegerField, F, DecimalField
from django.db.models.functions import Coalesce
from django.db.models import Q
from rest_framework import viewsets, filters
from django.db.models import Case, When, Value, FloatField, F
from django.db.models import Q
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.conf import settings
from django.utils import timezone
from django.core.cache import cache
from rest_framework.views import APIView
from django.db.models import Count, Q, Sum, Avg
from .models import *
from .serializers import *
import json
from django.utils import timezone
import uuid
from yookassa import Configuration, Payment
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils.crypto import get_random_string
from rest_framework.permissions import AllowAny
from .serializers import (
    PasswordResetRequestSerializer, 
    PasswordResetVerifySerializer,
    PasswordResetConfirmSerializer
)

User = get_user_model()

try:
    from unireax_main.utils.additional_function import calculate_course_completion
except ImportError as e:
    print(f"ошибка импорта: {e}")

logger = logging.getLogger(__name__)

from django.core.cache import cache
from datetime import timedelta
from rest_framework.decorators import api_view, permission_classes

MAX_ATTEMPTS = 5
BLOCK_MINUTES = 5
ATTEMPT_WINDOW_MINUTES = 5

class SendVerificationCodeView(APIView):
    """Отправка кода подтверждения на email"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({'error': 'Email обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Пользователь с таким email уже существует'
            }, status=status.HTTP_400_BAD_REQUEST)

        code = ''.join(random.choices(string.digits, k=6))
        
        cache.set(f'verification_code_{email}', code, timeout=600)

        subject = 'Подтверждение регистрации в UNIREAX'
        message = f"""
Здравствуйте!

Вы начали регистрацию на образовательной платформе UNIREAX.

Ваш код подтверждения: {code}

Если вы не регистрировались в UNIREAX, просто проигнорируйте это письмо.

С уважением,
Команда UNIREAX
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({
                'success': True,
                'message': 'Код отправлен на почту'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Ошибка отправки email: {e}')
            return Response({
                'error': 'Ошибка при отправке письма. Попробуйте позже.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class VerifyCodeView(APIView):
    """Проверка кода подтверждения"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        code = request.data.get('code')
        
        if not email or not code:
            return Response({
                'error': 'Email и код обязательны'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        saved_code = cache.get(f'verification_code_{email}')
        
        if saved_code and saved_code == code:
            cache.delete(f'verification_code_{email}')
            cache.set(f'email_verified_{email}', True, timeout=600)  
            
            return Response({
                'success': True,
                'verified': True,
                'message': 'Email успешно подтвержден'
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                'error': 'Неверный или просроченный код',
                'verified': False
            }, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationCodeView(APIView):
    """Повторная отправка кода подтверждения"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        email = request.data.get('email')
        
        if not email:
            return Response({'error': 'Email обязателен'}, status=status.HTTP_400_BAD_REQUEST)
        
        if User.objects.filter(email=email).exists():
            return Response({
                'error': 'Пользователь с таким email уже существует'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        code = ''.join(random.choices(string.digits, k=6))
        
        cache.set(f'verification_code_{email}', code, timeout=600)

        subject = 'Подтверждение регистрации в UNIREAX (повторная отправка)'
        message = f"""
Здравствуйте!

Вы запросили повторную отправку кода подтверждения для регистрации в UNIREAX.

Ваш новый код подтверждения: {code}

Если вы не регистрировались в UNIREAX, просто проигнорируйте это письмо.

С уважением,
Команда UNIREAX
"""
        
        try:
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[email],
                fail_silently=False,
            )
            return Response({
                'success': True,
                'message': 'Новый код отправлен на почту'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            logger.error(f'Ошибка отправки email: {e}')
            return Response({
                'error': 'Ошибка при отправке письма. Попробуйте позже.'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

def get_attempts_key_by_username(username):
    """Ключ для кэша попыток по username"""
    return f"login_attempts_username:{username.lower()}"

def get_block_key_by_username(username):
    """Ключ для кэша блокировки по username"""
    return f"login_block_username:{username.lower()}"

def check_rate_limit_by_username(username):
    """Проверяет лимиты попыток входа по username"""
    if not username:
        return False, MAX_ATTEMPTS, 0
    
    block_key = get_block_key_by_username(username)
    block_until = cache.get(block_key)
    
    if block_until:
        now = timezone.now()
        if isinstance(block_until, (int, float)):
            from datetime import datetime
            block_until = datetime.fromtimestamp(block_until, tz=timezone.get_current_timezone())
        
        if now < block_until:
            seconds_left = int((block_until - now).total_seconds())
            return True, 0, seconds_left
        else:
            cache.delete(block_key)
    
    attempts_key = get_attempts_key_by_username(username)
    attempts = cache.get(attempts_key, [])
    
    window_start = timezone.now() - timedelta(minutes=ATTEMPT_WINDOW_MINUTES)
    recent_attempts = [a for a in attempts if a > window_start]
    
    if len(recent_attempts) != len(attempts):
        cache.set(attempts_key, recent_attempts, timeout=ATTEMPT_WINDOW_MINUTES * 60 + 60)
    
    remaining_attempts = max(0, MAX_ATTEMPTS - len(recent_attempts))
    return False, remaining_attempts, 0


def update_assignment_status(user_assignment, feedback):
    """
    Обновляет статус задания на основе обратной связи
    Возвращает новый статус
    """
    try:
        assignment = user_assignment.practical_assignment
        score = feedback.score
        is_passed = feedback.is_passed        
        pending_status = AssignmentStatus.objects.get(assignment_status_name='на проверке')
        overdue_status = AssignmentStatus.objects.get(assignment_status_name='просрочено')
        rejected_status = AssignmentStatus.objects.get(assignment_status_name='отклонено')
        revision_status = AssignmentStatus.objects.get(assignment_status_name='на доработке')
        completed_status = AssignmentStatus.objects.get(assignment_status_name='завершено')
        
        print(f"ID статуса 'завершено': {completed_status.id}")
        print(f"ID статуса 'на проверке': {pending_status.id}")
        
        if assignment.grading_type == 'points':
            max_score = assignment.max_score
            
            if assignment.passing_score is not None:
                passing_score = assignment.passing_score
                print(f"Проходной балл (баллы): {passing_score}")
                
                if score is not None and score >= passing_score:
                    new_status = completed_status
                else:
                    new_status = revision_status
            else:
                passing_percentage = max_score * 0.5
                
                if score is not None and score >= passing_percentage:
                    new_status = completed_status
                else:
                    new_status = revision_status
        
        elif assignment.grading_type == 'pass_fail':
            print(f"Зачетная система, is_passed: {is_passed}")
            
            if is_passed:
                new_status = completed_status
            else:
                if score is not None and assignment.max_score:
                    percentage = (score / assignment.max_score) * 100
                    print(f"Процент: {percentage}%")
                    if percentage >= 50:
                        new_status = completed_status
                    else:
                        new_status = revision_status
                else:
                    new_status = revision_status
        
        else:
            new_status = revision_status
        
        
        current_status_name = user_assignment.submission_status.assignment_status_name        
        if current_status_name == 'на доработке' and new_status == revision_status:
            attempts_count = UserPracticalAssignment.objects.filter(
                user=user_assignment.user,
                practical_assignment=assignment
            ).count()
            
            if attempts_count >= 200:
                new_status = rejected_status
        
        user_assignment.submission_status = new_status
        user_assignment.save()
        user_assignment.refresh_from_db()
        return new_status
        
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        raise


class CustomPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if request.method in ['GET', 'HEAD', 'OPTIONS']:
            return True
        return super().has_permission(request, view)

class AdminOnlyPermission(IsAdminUser):
    pass

class TeacherMethodistPermission(IsAuthenticated):
    def has_permission(self, request, view):
        if not super().has_permission(request, view):
            return False
        return request.user.is_teacher_or_methodist or request.user.is_superuser


class IsListenerPermission(BasePermission):
    """Проверяет, что пользователь - слушатель курсов"""
    def has_permission(self, request, view):
        return (
            request.user and 
            request.user.is_authenticated and
            request.user.role and 
            request.user.role.role_name == 'слушатель курсов'
        )

class PaginationPage(PageNumberPagination):
    page_size_query_param = 'page_size'
    page_query_param = 'page'
    page_size = 20
    max_page_size = 100


# 1. роли пользователей
class RoleViewSet(viewsets.ModelViewSet):
    queryset = Role.objects.all()
    serializer_class = RoleSerializer
    permission_classes = [AdminOnlyPermission]
    pagination_class = PaginationPage


# 2. пользователи
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [AdminOnlyPermission]
    pagination_class = PaginationPage
    
    def get_permissions(self):
        if self.action in ['me', 'update_profile', 'change_password']:
            return [IsAuthenticated()]
        elif self.action in ['create', 'register']:
            return [AllowAny()]
        return super().get_permissions()
    
    @action(detail=False, methods=['get'])
    def me(self, request):
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put'])
    def update_profile(self, request):
        user = request.user
        serializer = self.get_serializer(user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        if not user.check_password(serializer.validated_data['old_password']):
            return Response(
                {"old_password": ["Неверный пароль"]},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        return Response({"detail": "Пароль успешно изменен"})


# 3. категории курсов
class CourseCategoryViewSet(viewsets.ModelViewSet):
    queryset = CourseCategory.objects.all()
    serializer_class = CourseCategorySerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage


# 4. типы курсов
class CourseTypeViewSet(viewsets.ModelViewSet):
    queryset = CourseType.objects.all()
    serializer_class = CourseTypeSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage


# 5. статусы заданий
class AssignmentStatusViewSet(viewsets.ModelViewSet):
    queryset = AssignmentStatus.objects.all()
    serializer_class = AssignmentStatusSerializer
    permission_classes = [AdminOnlyPermission]
    pagination_class = PaginationPage

# 6. курсы
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.filter(
        is_active=True
    ).exclude(
        course_type__course_type_name='классная комната'
    ).annotate(
        student_count=Count('usercourse', filter=Q(usercourse__is_active=True))
    ).order_by('id')
    serializer_class = CourseSerializer
    permission_classes = [CustomPermission]
    pagination_class = PaginationPage
    filter_backends = [filters.SearchFilter]
    search_fields = ['course_name', 'course_description']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        queryset = queryset.exclude(course_type__course_type_name='классная комната')
        category_param = self.request.query_params.get('course_category')
        if category_param:
            category_ids = []
            for cat in category_param.split(','):
                cat = cat.strip()
                if cat.isdigit():
                    category_ids.append(int(cat))
            
            if category_ids:
                queryset = queryset.filter(course_category_id__in=category_ids)

        type_param = self.request.query_params.get('course_type')
        if type_param:
            type_ids = []
            for t in type_param.split(','):
                t = t.strip()
                if t.isdigit():
                    type_ids.append(int(t))
            
            if type_ids:
                queryset = queryset.filter(course_type_id__in=type_ids)
        
        has_certificate = self.request.query_params.get('has_certificate')
        if has_certificate is not None:
            queryset = queryset.filter(has_certificate=has_certificate.lower() == 'true')
        
        free_only = self.request.query_params.get('free_only')
        if free_only is not None and free_only.lower() == 'true':
            from decimal import Decimal
            queryset = queryset.filter(
                Q(course_price__isnull=True) | 
                Q(course_price=0) |
                Q(course_price=Decimal('0')) |
                Q(course_price=Decimal('0.00'))
            )
        
        sort_by = self.request.query_params.get('sort_by')
        sort_order = self.request.query_params.get('sort_order', 'asc').lower()
        
        if sort_by == 'student_count':
            queryset = queryset.order_by('-student_count')
        elif sort_by == 'rating':
            queryset = queryset.annotate(
                avg_rating=Avg('review__rating', filter=Q(review__is_approved=True))
            )
            if sort_order == 'desc':
                queryset = queryset.order_by('-avg_rating')
            else:
                queryset = queryset.order_by('avg_rating')
        elif sort_by == 'course_price':
            queryset = queryset.annotate(
                sort_price=Case(
                    When(course_price__isnull=True, then=Value(0.0)),
                    default='course_price',
                    output_field=FloatField()
                )
            )
            if sort_order == 'desc':
                queryset = queryset.order_by('-sort_price')
            else:
                queryset = queryset.order_by('sort_price')
        elif sort_by == 'course_hours':
            if sort_order == 'desc':
                queryset = queryset.order_by('-course_hours')
            else:
                queryset = queryset.order_by('course_hours')
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def completion(self, request, pk=None):
        """Получить процент завершения курса для текущего пользователя"""
        try:
            course = self.get_object()
            user = request.user

            progress = calculate_course_completion(user.id, course.id)
            
            return Response({
                'course_id': course.id,
                'course_name': course.course_name,
                'completion': float(progress), 
                'user_id': user.id
            })
        except Exception as e:
            logger.error(f"Ошибка расчета завершения курса: {e}")
            return Response({
                'completion': 0.0,
                'error': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)
    
# 7. преподаватели курсов
class CourseTeacherViewSet(viewsets.ModelViewSet):
    queryset = CourseTeacher.objects.all()
    serializer_class = CourseTeacherSerializer
    permission_classes = [TeacherMethodistPermission]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        course = self.request.query_params.get('course')
        if course:
            queryset = queryset.filter(course_id=course)
        
        teacher = self.request.query_params.get('teacher')
        if teacher:
            queryset = queryset.filter(teacher_id=teacher)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset

# 8. лекции
class LectureViewSet(viewsets.ModelViewSet):
    queryset = Lecture.objects.all()
    serializer_class = LectureSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [TeacherMethodistPermission()]

# 9. практические задания
class PracticalAssignmentViewSet(viewsets.ModelViewSet):
    queryset = PracticalAssignment.objects.all()
    serializer_class = PracticalAssignmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [TeacherMethodistPermission()]


# 10. сдачи практических заданий
class UserPracticalAssignmentViewSet(viewsets.ModelViewSet):
    queryset = UserPracticalAssignment.objects.all()
    serializer_class = UserPracticalAssignmentSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        user = self.request.user
    
        if user.is_superuser or user.is_admin:
            queryset = super().get_queryset()
        elif user.is_teacher_or_methodist:
            teacher_courses = CourseTeacher.objects.filter(
                teacher=user, is_active=True
            ).values_list('course_id', flat=True)
            
            course_assignments = PracticalAssignment.objects.filter(
                lecture__course_id__in=teacher_courses
            ).values_list('id', flat=True)
            
            queryset = UserPracticalAssignment.objects.filter(
                practical_assignment_id__in=course_assignments
            )
        else:
            queryset = UserPracticalAssignment.objects.filter(user=user)
        
        assignment = self.request.query_params.get('assignment')
        if assignment:
            queryset = queryset.filter(practical_assignment_id=assignment)
        
        status_filter = self.request.query_params.get('status')
        if status_filter:
            queryset = queryset.filter(submission_status_id=status_filter)
        
        user_filter = self.request.query_params.get('user')
        if user_filter and (user.is_superuser or user.is_admin):
            queryset = queryset.filter(user_id=user_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# 11. пользователи на курсах
class UserCourseViewSet(viewsets.ModelViewSet):
    queryset = UserCourse.objects.all()
    serializer_class = UserCourseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser or user.is_admin:
            queryset = super().get_queryset()
        elif user.is_teacher_or_methodist:
            teacher_courses = CourseTeacher.objects.filter(
                teacher=user, is_active=True
            ).values_list('course_id', flat=True)
            
            queryset = UserCourse.objects.filter(course_id__in=teacher_courses)
        else:
            queryset = UserCourse.objects.filter(user=user)
        
        course = self.request.query_params.get('course')
        if course:
            queryset = queryset.filter(course_id=course)
        
        user_filter = self.request.query_params.get('user')
        if user_filter and (user.is_superuser or user.is_admin):
            queryset = queryset.filter(user_id=user_filter)
        
        is_active = self.request.query_params.get('is_active')
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def enroll(self, request):
        """Запись на курс"""
        course_id = request.data.get('course_id')
        if not course_id:
            return Response(
                {"detail": "Не указан ID курса"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        course = get_object_or_404(Course, id=course_id, is_active=True)
        
        if UserCourse.objects.filter(user=request.user, course=course).exists():
            return Response(
                {"detail": "Вы уже записаны на этот курс"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if course.course_max_places:
            enrolled_count = UserCourse.objects.filter(course=course, is_active=True).count()
            if enrolled_count >= course.course_max_places:
                return Response(
                    {"detail": "На курсе нет свободных мест"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        user_course = UserCourse.objects.create(
            user=request.user,
            course=course,
            course_price=course.course_price
        )
        
        serializer = self.get_serializer(user_course)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Покинуть курс (установить is_active=False)"""
        try:
            user_course = self.get_queryset().get(pk=pk, user=request.user)
        except UserCourse.DoesNotExist:
            return Response(
                {"detail": "Запись на курс не найдена"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if not user_course.is_active:
            return Response(
                {"detail": "Вы уже покинули этот курс"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user_course.is_active = False
        user_course.save()
        
        return Response({
            "detail": "Вы успешно покинули курс",
            "course_id": user_course.course_id,
            "is_active": user_course.is_active
        })


# 12. обратная связь
class FeedbackViewSet(viewsets.ModelViewSet):
    """
    ViewSet для работы с обратной связью по практическим заданиям.
    При создании/обновлении обратной связи автоматически обновляет статус задания.
    """
    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    permission_classes = [TeacherMethodistPermission]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        """
        Получение queryset с фильтрацией по параметрам запроса.
        """
        queryset = super().get_queryset()
        assignment = self.request.query_params.get('assignment')
        if assignment:
            queryset = queryset.filter(user_practical_assignment_id=assignment)
        user = self.request.query_params.get('user')
        if user:
            queryset = queryset.filter(user_practical_assignment__user_id=user)
        course = self.request.query_params.get('course')
        if course:
            queryset = queryset.filter(
                user_practical_assignment__practical_assignment__lecture__course_id=course
            )

        is_graded = self.request.query_params.get('is_graded')
        if is_graded is not None:
            if is_graded.lower() == 'true':
                queryset = queryset.filter(given_by__isnull=False)
            else:
                queryset = queryset.filter(given_by__isnull=True)
        
        return queryset.select_related(
            'user_practical_assignment',
            'user_practical_assignment__practical_assignment',
            'user_practical_assignment__user',
            'given_by'
        ).order_by('-given_at')
    
    def _check_course_completion(self, user_assignment):
        """
        Проверяет, завершен ли курс после обновления обратной связи.
        """
        try:
            from unireax_main.utils.course_progress import check_course_completion
            from unireax_main.models import UserCourse
            
            course_id = user_assignment.practical_assignment.lecture.course_id
            user_id = user_assignment.user_id
            
            completion_data = check_course_completion(user_id, course_id)
 
            
            if completion_data['completed']:                
                user_course = UserCourse.objects.filter(
                    user_id=user_id,
                    course_id=course_id,
                    is_active=True
                ).first()
                
                if user_course:
                    print(f"  Найдена запись UserCourse: id={user_course.id}, status_course={user_course.status_course}")
                    
                    if not user_course.status_course:
                        user_course.status_course = True
                        user_course.completion_date = timezone.now()
                        user_course.save()
                        logger.info(f"Курс {course_id} завершен пользователем {user_id} после оценки работы")
                
        except Exception as e:
            import traceback
            traceback.print_exc()
    
    def perform_create(self, serializer):
        """
        Создание обратной связи с автоматическим обновлением статуса задания.
        """
        try:
            user_practical_assignment = serializer.validated_data.get('user_practical_assignment')
            
            existing_feedback = Feedback.objects.filter(
                user_practical_assignment=user_practical_assignment
            ).first()
            
            if existing_feedback:

                existing_feedback.score = serializer.validated_data.get('score', existing_feedback.score)
                existing_feedback.is_passed = serializer.validated_data.get('is_passed', existing_feedback.is_passed)
                existing_feedback.comment_feedback = serializer.validated_data.get('comment_feedback', existing_feedback.comment_feedback)
                existing_feedback.given_by = self.request.user
                existing_feedback.save()
                feedback = existing_feedback
            else:
                feedback = serializer.save(given_by=self.request.user)
            
            user_assignment = feedback.user_practical_assignment            
            from unireax_main.utils.assignment_utils import update_assignment_status            
            new_status = update_assignment_status(user_assignment, feedback)            
            user_assignment.refresh_from_db()            
            self._check_course_completion(user_assignment)
            
            logger.info(
                f"Статус задания #{user_assignment.id} обновлен на "
                f"'{new_status.assignment_status_name}'"
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Ошибка при создании обратной связи: {e}")
            logger.exception(e)
            raise
        
        print("="*60 + "\n")
    
    def perform_update(self, serializer):
        """
        Обновление обратной связи с автоматическим обновлением статуса задания.
        """
        
        try:
            feedback = serializer.save()
            user_assignment = feedback.user_practical_assignment
            assignment = user_assignment.practical_assignment
            from unireax_main.utils.assignment_utils import update_assignment_status            
            new_status = update_assignment_status(user_assignment, feedback)            
            user_assignment.refresh_from_db()            
            self._check_course_completion(user_assignment)
            
            logger.info(
                f"Статус задания #{user_assignment.id} обновлен при изменении "
                f"обратной связи на '{new_status.assignment_status_name}'"
            )
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            logger.error(f"Ошибка при обновлении обратной связи: {e}")
            logger.exception(e)
            raise
    
    def perform_destroy(self, instance):
        """
        Удаление обратной связи.
        При удалении обратной связи статус задания возвращается к 'на проверке'.
        """
        
        try:
            user_assignment = instance.user_practical_assignment
            pending_status = AssignmentStatus.objects.get(assignment_status_name='на проверке')            
            user_assignment.submission_status = pending_status
            user_assignment.save()            
            self._check_course_completion(user_assignment)
            
            logger.info(
                f"Статус задания #{user_assignment.id} возвращен к "
                f"'{pending_status.assignment_status_name}'"
            )
            
        except Exception as e:
            logger.error(f"Ошибка при возврате статуса задания: {e}")
            logger.exception(e)
        
        instance.delete()
    
    @action(detail=False, methods=['get'])
    def my_feedbacks(self, request):
        """
        Получить обратную связь, которую оставил текущий преподаватель/методист.
        """
        queryset = self.get_queryset().filter(given_by=request.user)
        
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def pending(self, request):
        """
        Получить задания, ожидающие проверки (без обратной связи).
        """
        pending_status = AssignmentStatus.objects.get(assignment_status_name='на проверке')        
        if request.user.is_teacher_or_methodist:
            teacher_courses = CourseTeacher.objects.filter(
                teacher=request.user, 
                is_active=True
            ).values_list('course_id', flat=True)
            
            pending_assignments = UserPracticalAssignment.objects.filter(
                submission_status=pending_status,
                practical_assignment__lecture__course_id__in=teacher_courses
            ).select_related(
                'user',
                'practical_assignment',
                'practical_assignment__lecture',
                'practical_assignment__lecture__course'
            ).order_by('submission_date')
        
        else:
            pending_assignments = UserPracticalAssignment.objects.filter(
                submission_status=pending_status
            ).select_related(
                'user',
                'practical_assignment',
                'practical_assignment__lecture',
                'practical_assignment__lecture__course'
            ).order_by('submission_date')
        
        from .serializers import UserPracticalAssignmentSerializer
        serializer = UserPracticalAssignmentSerializer(pending_assignments, many=True)
        
        return Response({
            'count': pending_assignments.count(),
            'results': serializer.data
        })
    
    @action(detail=True, methods=['post'])
    def resend_notification(self, request, pk=None):
        """
        Отправить уведомление студенту о проверке работы.
        """
        feedback = self.get_object()
        user_assignment = feedback.user_practical_assignment
        student = user_assignment.user
        
        try:
            """
            send_mail(
                subject=f'Проверена работа: {user_assignment.practical_assignment.practical_assignment_name}',
                message=f'Здравствуйте, {student.first_name}!\n\n'
                        f'Ваша работа "{user_assignment.practical_assignment.practical_assignment_name}" '
                        f'была проверена преподавателем.\n\n'
                        f'Результат: {feedback.score if feedback.score else "зачтено" if feedback.is_passed else "не зачтено"}\n'
                        f'Комментарий: {feedback.comment_feedback or "без комментария"}\n\n'
                        f'С уважением,\nКоманда UNIREAX',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[student.email],
                fail_silently=True,
            )
            """
            
            logger.info(f"Уведомление отправлено слушателю {student.email} о проверке работы #{user_assignment.id}")
            
            return Response({
                'success': True,
                'detail': 'Уведомление отправлено',
                'student_email': student.email
            })
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
            return Response(
                {'detail': f'Ошибка отправки уведомления: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """
        Получить статистику по проверкам для преподавателя/методиста.
        """
        if not request.user.is_teacher_or_methodist and not request.user.is_superuser:
            return Response(
                {'detail': 'Доступ запрещен'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.user.is_teacher_or_methodist:
            teacher_courses = CourseTeacher.objects.filter(
                teacher=request.user,
                is_active=True
            ).values_list('course_id', flat=True)
            
            course_filter = {'practical_assignment__lecture__course_id__in': teacher_courses}
        else:
            course_filter = {}        
        total_feedbacks = Feedback.objects.filter(
            given_by=request.user,
            **course_filter
        ).count()
        
        feedbacks_today = Feedback.objects.filter(
            given_by=request.user,
            given_at__date=timezone.now().date(),
            **course_filter
        ).count()
        
        feedbacks_this_week = Feedback.objects.filter(
            given_by=request.user,
            given_at__week=timezone.now().isocalendar()[1],
            **course_filter
        ).count()
        
        avg_score = Feedback.objects.filter(
            given_by=request.user,
            score__isnull=False,
            **course_filter
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        pending_status = AssignmentStatus.objects.get(assignment_status_name='на проверке')
        pending_count = UserPracticalAssignment.objects.filter(
            submission_status=pending_status,
            **course_filter
        ).count()
        
        return Response({
            'total_feedbacks': total_feedbacks,
            'feedbacks_today': feedbacks_today,
            'feedbacks_this_week': feedbacks_this_week,
            'average_score': round(avg_score, 1),
            'pending_assignments': pending_count,
            'teacher_name': request.user.get_full_name() or request.user.username,
        })
    
    @action(detail=True, methods=['get'])
    def history(self, request, pk=None):
        """
        Получить историю изменений обратной связи (если есть логирование).
        """
        feedback = self.get_object()
        
        return Response({
            'feedback_id': feedback.id,
            'created_at': feedback.given_at,
            'created_by': {
                'id': feedback.given_by.id if feedback.given_by else None,
                'name': feedback.given_by.get_full_name() if feedback.given_by else None,
            },
            'last_updated': feedback.user_practical_assignment.updated_at 
                           if hasattr(feedback.user_practical_assignment, 'updated_at') 
                           else feedback.given_at,
            'history': []
        })
    

class CheckOverdueAssignmentsView(APIView):
    """Проверка и обновление статусов просроченных заданий"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request):
        try:
            overdue_count = 0
            
            assignments_with_deadline = PracticalAssignment.objects.filter(
                assignment_deadline__isnull=False,
                is_active=True
            )
            
            for assignment in assignments_with_deadline:
                if assignment.is_overdue:
                    user_assignments = UserPracticalAssignment.objects.filter(
                        practical_assignment=assignment,
                        submission_status__assignment_status_name='на проверке'
                    )
                    
                    overdue_status = AssignmentStatus.objects.get(assignment_status_name='просрочено')                    
                    for user_assignment in user_assignments:
                        user_assignment.submission_status = overdue_status
                        user_assignment.save()
                        overdue_count += 1
            
            return Response({
                'detail': f'Обновлено {overdue_count} просроченных заданий'
            })
            
        except Exception as e:
            logger.error(f"Ошибка проверки просроченных заданий: {e}")
            return Response(
                {'detail': f'Ошибка: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# 13. отзывы
class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.all()
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        course = self.request.query_params.get('course')
        if course:
            queryset = queryset.filter(course_id=course)
        
        user = self.request.query_params.get('user')
        if user:
            queryset = queryset.filter(user_id=user)
        
        is_approved = self.request.query_params.get('is_approved')
        if is_approved is not None:
            queryset = queryset.filter(is_approved=is_approved.lower() == 'true')
        
        return queryset
    
    def perform_create(self, serializer):
        course_id = serializer.validated_data['course'].id
        if Review.objects.filter(user=self.request.user, course_id=course_id).exists():
            raise serializers.ValidationError({"detail": "Вы уже оставляли отзыв на этот курс"})
        
        serializer.save(user=self.request.user)


# 14. типы ответов
class AnswerTypeViewSet(viewsets.ModelViewSet):
    queryset = AnswerType.objects.all()
    serializer_class = AnswerTypeSerializer
    permission_classes = [IsAuthenticated] 
    pagination_class = PaginationPage
    
    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [AdminOnlyPermission()]


# 15. тесты
class TestViewSet(viewsets.ModelViewSet):
    queryset = Test.objects.all()
    serializer_class = TestSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_permissions(self):
        if self.request.method in ['GET', 'HEAD', 'OPTIONS']:
            return [IsAuthenticated()]
        return [TeacherMethodistPermission()]

# 16. вопросы
class QuestionViewSet(viewsets.ModelViewSet):
    queryset = Question.objects.all()
    serializer_class = QuestionSerializer
    permission_classes = [TeacherMethodistPermission]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        test = self.request.query_params.get('test')
        if test:
            queryset = queryset.filter(test_id=test)
        
        return queryset.order_by('question_order')


# 17. варианты ответов
class ChoiceOptionViewSet(viewsets.ModelViewSet):
    queryset = ChoiceOption.objects.all()
    serializer_class = ChoiceOptionSerializer
    permission_classes = [TeacherMethodistPermission]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        question = self.request.query_params.get('question')
        if question:
            queryset = queryset.filter(question_id=question)
        
        return queryset


# 18. пары соответствия
class MatchingPairViewSet(viewsets.ModelViewSet):
    queryset = MatchingPair.objects.all()
    serializer_class = MatchingPairSerializer
    permission_classes = [TeacherMethodistPermission]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        queryset = super().get_queryset()
        
        question = self.request.query_params.get('question')
        if question:
            queryset = queryset.filter(question_id=question)
        
        return queryset


# 19. ответы пользователей
class UserAnswerViewSet(viewsets.ModelViewSet):
    queryset = UserAnswer.objects.all()
    serializer_class = UserAnswerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser or user.is_admin:
            queryset = super().get_queryset()
        else:
            queryset = UserAnswer.objects.filter(user=user)
        
        test = self.request.query_params.get('test')
        if test:
            queryset = queryset.filter(question__test_id=test)
        
        question = self.request.query_params.get('question')
        if question:
            queryset = queryset.filter(question_id=question)
        
        attempt = self.request.query_params.get('attempt')
        if attempt:
            queryset = queryset.filter(attempt_number=attempt)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# 20. выбранные варианты
class UserSelectedChoiceViewSet(viewsets.ModelViewSet):
    queryset = UserSelectedChoice.objects.all()
    serializer_class = UserSelectedChoiceSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage


# 21. ответы на сопоставления
class UserMatchingAnswerViewSet(viewsets.ModelViewSet):
    queryset = UserMatchingAnswer.objects.all()
    serializer_class = UserMatchingAnswerSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage


# 22. результаты тестов
class TestResultViewSet(viewsets.ModelViewSet):
    queryset = TestResult.objects.all()
    serializer_class = TestResultSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser or user.is_admin:
            queryset = super().get_queryset()
        else:
            queryset = TestResult.objects.filter(user=user)
        test = self.request.query_params.get('test')
        if test:
            queryset = queryset.filter(test_id=test)
        user_filter = self.request.query_params.get('user')
        if user_filter and (user.is_superuser or user.is_admin):
            queryset = queryset.filter(user_id=user_filter)
        
        return queryset
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

# 23. сертификаты
class CertificateViewSet(viewsets.ModelViewSet):
    queryset = Certificate.objects.all()
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        user = self.request.user
        
        if user.is_superuser or user.is_admin:
            queryset = super().get_queryset()
        else:
            queryset = Certificate.objects.filter(user_course__user=user)
        
        return queryset

    @action(detail=True, methods=['post'], url_path='regenerate')
    def regenerate_certificate(self, request, pk=None):
        """Перегенерация сертификата с актуальными баллами"""
        certificate = self.get_object()
        user_course = certificate.user_course

        if user_course.user != request.user:
            return Response(
                {'detail': 'У вас нет доступа к этому сертификату'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        try:
            if certificate.certificate_file_path:
                old_path = os.path.join(settings.MEDIA_ROOT, certificate.certificate_file_path)
                if os.path.exists(old_path):
                    os.remove(old_path)
            
            from unireax_main.utils.certificate_generator import generate_certificate_pdf, calculate_total_course_score
            pdf_path = generate_certificate_pdf(certificate)
            certificate.certificate_file_path = pdf_path
            certificate.save()
            
            score_data = calculate_total_course_score(request.user.id, user_course.course.id)
            
            serializer = self.get_serializer(certificate)
            return Response({
                'detail': 'Сертификат успешно обновлён',
                'certificate': serializer.data,
                'score_data': score_data
            })
            
        except Exception as e:
            return Response(
                {'detail': f'Ошибка при обновлении сертификата: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

# 24. файлы сдачи заданий
class AssignmentSubmissionFileViewSet(viewsets.ModelViewSet):
    queryset = AssignmentSubmissionFile.objects.all()
    serializer_class = AssignmentSubmissionFileSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage

# 25. файлы преподавателей
class TeacherAssignmentFileViewSet(viewsets.ModelViewSet):
    queryset = TeacherAssignmentFile.objects.all()
    serializer_class = TeacherAssignmentFileSerializer
    permission_classes = [TeacherMethodistPermission]
    pagination_class = PaginationPage

# 26. коды восстановления
class PasswordResetCodeViewSet(viewsets.ModelViewSet):
    queryset = PasswordResetCode.objects.all()
    serializer_class = PasswordResetCodeSerializer
    permission_classes = [AdminOnlyPermission]
    pagination_class = PaginationPage


class ListenerCourseViewSet(viewsets.ReadOnlyModelViewSet):
    """viewset для работы слушателей с курсами"""
    queryset = Course.objects.filter(
        is_active=True
    ).exclude(
        course_type__course_type_name='классная комната'
    )
    serializer_class = CourseSerializer
    permission_classes = [IsAuthenticated]  
    
    def get_queryset(self):
        queryset = super().get_queryset().annotate(
            calculated_rating=Avg(
                'review__rating',
                filter=Q(review__is_approved=True)
            ),
            review_count=Count(
                'review',
                filter=Q(review__is_approved=True)
            ),
            enrolled_count=Count('usercourse', filter=Q(usercourse__is_active=True))
        )
        
        queryset = queryset.exclude(course_type__course_type_name='классная комната')
        
        search = self.request.query_params.get('search')
        if search:
            queryset = queryset.filter(
                Q(course_name__icontains=search) |
                Q(course_description__icontains=search) |
                Q(course_category__course_category_name__icontains=search)
            )
        
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(course_category_id=category)
        
        course_type = self.request.query_params.get('type')
        if course_type:
            queryset = queryset.filter(course_type_id=course_type)
        
        price_min = self.request.query_params.get('price_min')
        if price_min:
            queryset = queryset.filter(course_price__gte=price_min)
        price_max = self.request.query_params.get('price_max')
        if price_max:
            queryset = queryset.filter(course_price__lte=price_max)

        sort_by = self.request.query_params.get('sort_by', '-enrolled_count')
        if sort_by in ['calculated_rating', '-calculated_rating', 'course_price', 
                      '-course_price', 'course_name', '-course_name', 'enrolled_count', '-enrolled_count']:
            queryset = queryset.order_by(sort_by)
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def enrolled(self, request):
        """Курсы, на которые записан текущий пользователь"""
        user = request.user
        enrolled_course_ids = UserCourse.objects.filter(
            user=user, 
            is_active=True
        ).values_list('course_id', flat=True)
        
        courses = Course.objects.filter(
            id__in=enrolled_course_ids,
            is_active=True
        ).exclude(
            course_type__course_type_name='классная комната'
        )
        
        courses_with_progress = []
        for course in courses:
            try:
                progress = calculate_course_completion(user.id, course.id)
            except:
                progress = 0.0
            course_data = CourseSerializer(course, context={'request': request}).data
            course_data['progress'] = progress
            courses_with_progress.append(course_data)
        
        return Response(courses_with_progress)
    
    @action(detail=True, methods=['post'], permission_classes=[IsAuthenticated])
    def enroll(self, request, pk=None):
        """Записаться на курс"""
        try:
            course = self.get_object()
            user = request.user
            
            if course.course_type and course.course_type.course_type_name == 'классная комната':
                return Response(
                    {"detail": "Запись на этот тип курса недоступна"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                    
            if UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
                return Response(
                    {"detail": "Вы уже записаны на этот курс"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if course.course_max_places:
                enrolled_count = UserCourse.objects.filter(course=course, is_active=True).count()
                if enrolled_count >= course.course_max_places:
                    return Response(
                        {"detail": "На курсе нет свободных мест"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            user_course = UserCourse.objects.create(
                user=user,
                course=course,
                registration_date=timezone.now().date(),
                course_price=course.course_price,
                is_active=True,
                status_course=False
            )
                        
            serializer = UserCourseSerializer(user_course)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Course.DoesNotExist:
            return Response(
                {"detail": "Курс не найден"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {"detail": f"Ошибка при записи: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """Покинуть курс"""
        try:
            course = self.get_object()
            user = request.user
            
            user_course = UserCourse.objects.get(
                user=user,
                course=course,
                is_active=True
            )
            user_course.is_active = False
            user_course.save()
            
            return Response({"detail": "Вы успешно покинули курс"})
            
        except UserCourse.DoesNotExist:
            return Response(
                {"detail": "Вы не записаны на этот курс"},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['get'])
    def materials(self, request, pk=None):
        """Получить материалы курса"""
        course = self.get_object()
        user = request.user
        
        if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
            return Response(
                {"detail": "Вы не записаны на этот курс"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        lectures = Lecture.objects.filter(
            course=course,
            is_active=True
        ).order_by('lecture_order')
        
        assignments = PracticalAssignment.objects.filter(
            lecture__course=course,
            is_active=True
        ).select_related('lecture')
        
        tests = Test.objects.filter(
            lecture__course=course,
            is_active=True
        ).select_related('lecture')
        
        return Response({
            'lectures': LectureSerializer(lectures, many=True).data,
            'assignments': PracticalAssignmentSerializer(assignments, many=True).data,
            'tests': TestSerializer(tests, many=True).data,
        })

    @action(detail=True, methods=['get'], url_path='score')
    def course_score(self, request, pk=None):
        """Получить информацию о баллах за курс"""
        course = self.get_object()
        user = request.user
        
        if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
            return Response(
                {'detail': 'Вы не записаны на этот курс'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        from unireax_main.utils.certificate_generator import calculate_total_course_score
        score_data = calculate_total_course_score(user.id, course.id)
        
        return Response(score_data)

class ListenerTestAPIView(APIView):
    """API для работы с тестами"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, test_id):
        """Получить тест для прохождения"""
        user = request.user
        
        user_course = get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        test = get_object_or_404(
            Test,
            id=test_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        previous_attempts = TestResult.objects.filter(
            user=user,
            test=test
        ).count()
        
        if test.max_attempts and previous_attempts >= test.max_attempts:
            return Response(
                {'detail': 'Превышено максимальное количество попыток'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        questions = Question.objects.filter(
            test=test
        ).select_related('answer_type').prefetch_related(
            'choiceoption_set',
            'matchingpair_set'
        ).order_by('question_order')
        
        questions_data = []
        for question in questions:
            choices = question.choiceoption_set.all()
            matching_pairs = question.matchingpair_set.all()
            
            right_options = []
            if matching_pairs.exists():
                right_texts = list(set([pair.right_text for pair in matching_pairs if pair.right_text]))
                right_options = sorted(right_texts)
            
            question_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_score': question.question_score,
                'question_order': question.question_order,
                'answer_type': question.answer_type.answer_type_name if question.answer_type else 'текст',
                'answer_type_id': question.answer_type.id if question.answer_type else None,
                'correct_text': question.correct_text,
                'choiceoption_set': [
                    {
                        'id': choice.id,
                        'option_text': choice.option_text,
                        'is_correct': choice.is_correct,
                    }
                    for choice in choices
                ],
                'matchingpair_set': [
                    {
                        'id': pair.id,
                        'left_text': pair.left_text,
                        'right_text': pair.right_text,
                    }
                    for pair in matching_pairs
                ],
                'right_options': right_options,
            }
            
            questions_data.append(question_data)
        
        return Response({
            'test': {
                'id': test.id,
                'test_name': test.test_name,
                'test_description': test.test_description,
                'is_final': test.is_final,
                'max_attempts': test.max_attempts,
                'grading_form': test.grading_form,
                'passing_score': test.passing_score,
            },
            'questions': questions_data,
            'current_attempt': previous_attempts + 1,
            'max_attempts': test.max_attempts
        })
    
    def post(self, request, course_id, test_id):
        """Отправить ответы на тест"""
        user = request.user
        
        user_course = get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        test = get_object_or_404(
            Test,
            id=test_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        previous_attempts = TestResult.objects.filter(
            user=user,
            test=test
        ).count()
        
        attempt_number = previous_attempts + 1
        
        if test.max_attempts and previous_attempts >= test.max_attempts:
            return Response(
                {'detail': 'Превышено максимальное количество попыток'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        answers_data = request.data.get('answers', [])
        time_spent = request.data.get('time_spent', 0)
        
        if not answers_data:
            return Response(
                {'detail': 'Не переданы ответы на вопросы'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        total_score = 0
        max_score = 0
        
        for answer_data in answers_data:
            question_id = answer_data.get('question_id')
            answer_type = answer_data.get('answer_type')
            
            try:
                question = Question.objects.get(id=question_id, test=test)
            except Question.DoesNotExist:
                continue
            
            max_score += question.question_score if question.question_score else 1
            
            if answer_type == 'text':
                answer_text = answer_data.get('answer_text', '')
                
                if question.correct_text and answer_text.strip().lower() == question.correct_text.strip().lower():
                    score = question.question_score if question.question_score else 1
                    total_score += score
                
            elif answer_type == 'choice':
                selected_ids = answer_data.get('selected_choice_ids', [])
                
                correct_choices = question.choiceoption_set.filter(is_correct=True)
                selected_choices = question.choiceoption_set.filter(id__in=selected_ids, is_correct=True)
                
                if correct_choices.count() > 0:
                    answer_type_name = question.answer_type.answer_type_name if question.answer_type else 'текст'
                    
                    if answer_type_name.lower() in ['один ответ', 'выбор одного', 'single choice']:
                        if len(selected_ids) == 1 and selected_choices.count() == 1:
                            score = question.question_score if question.question_score else 1
                            total_score += score
                    else:
                        if correct_choices.count() == selected_choices.count() == len(selected_ids):
                            score = question.question_score if question.question_score else 1
                            total_score += score
            
            elif answer_type == 'matching':
                matching_data = answer_data.get('matching_data', [])
                
                correct_pairs = question.matchingpair_set.all()
                user_pairs = {(match.get('pair_id'), match.get('selected_right_text', '').strip()) 
                             for match in matching_data}
                
                correct_count = 0
                for pair in correct_pairs:
                    user_pair = (pair.id, pair.right_text.strip())
                    if user_pair in user_pairs:
                        correct_count += 1
                
                if correct_pairs.count() > 0:
                    correct_ratio = correct_count / correct_pairs.count()
                    score = (question.question_score if question.question_score else 1) * correct_ratio
                    total_score += score
        
        final_score = None
        is_passed = None
        passed_for_response = False  
        
        if test.grading_form == 'points':
            final_score = total_score
            is_passed = None  
            
            if test.passing_score:
                passed_for_response = total_score >= test.passing_score
            else:
                passed_for_response = total_score >= (max_score * 0.5) if max_score > 0 else False
                
        elif test.grading_form == 'pass_fail':
            final_score = None
            if max_score > 0:
                percentage = (total_score / max_score) * 100
                is_passed = percentage >= 50
                passed_for_response = is_passed
            else:
                is_passed = False
                passed_for_response = False
        
        try:
            test_result = TestResult.objects.create(
                user=user,
                test=test,
                time_spent=time_spent,
                attempt_number=attempt_number,
                final_score=final_score,
                is_passed=is_passed, 
            )
        except Exception as e:
            return Response(
                {'detail': f'Ошибка при сохранении результата: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        for answer_data in answers_data:
            question_id = answer_data.get('question_id')
            answer_type = answer_data.get('answer_type')
            
            try:
                question = Question.objects.get(id=question_id, test=test)
            except Question.DoesNotExist:
                continue
            
            user_answer = UserAnswer.objects.create(
                user=user,
                question=question,
                attempt_number=attempt_number,
                answer_date=timezone.now(),
            )
            
            if answer_type == 'text':
                answer_text = answer_data.get('answer_text', '')
                user_answer.answer_text = answer_text
                
                if question.correct_text:
                    if answer_text.strip().lower() == question.correct_text.strip().lower():
                        user_answer.score = question.question_score if question.question_score else 1
                    else:
                        user_answer.score = 0
                
                user_answer.save()
                
            elif answer_type == 'choice':
                selected_ids = answer_data.get('selected_choice_ids', [])
                
                for choice_id in selected_ids:
                    try:
                        choice = ChoiceOption.objects.get(id=choice_id, question=question)
                        UserSelectedChoice.objects.create(
                            user_answer=user_answer,
                            choice_option=choice
                        )
                    except ChoiceOption.DoesNotExist:
                        continue
                
                correct_choices = question.choiceoption_set.filter(is_correct=True)
                selected_choices = question.choiceoption_set.filter(id__in=selected_ids, is_correct=True)
                
                if correct_choices.count() > 0:
                    answer_type_name = question.answer_type.answer_type_name if question.answer_type else 'текст'
                    
                    if answer_type_name.lower() in ['один ответ', 'выбор одного', 'single choice']:
                        if len(selected_ids) == 1 and selected_choices.count() == 1:
                            user_answer.score = question.question_score if question.question_score else 1
                        else:
                            user_answer.score = 0
                    else:
                        if correct_choices.count() == selected_choices.count() == len(selected_ids):
                            user_answer.score = question.question_score if question.question_score else 1
                        else:
                            user_answer.score = 0
                
                user_answer.save()
            
            elif answer_type == 'matching':
                matching_data = answer_data.get('matching_data', [])
                
                for match in matching_data:
                    pair_id = match.get('pair_id')
                    selected_right = match.get('selected_right_text', '')
                    
                    try:
                        pair = MatchingPair.objects.get(id=pair_id, question=question)
                        UserMatchingAnswer.objects.create(
                            user_answer=user_answer,
                            matching_pair=pair,
                            user_selected_right_text=selected_right
                        )
                    except MatchingPair.DoesNotExist:
                        continue
                
                correct_pairs = question.matchingpair_set.all()
                user_pairs = {(match.get('pair_id'), match.get('selected_right_text', '').strip()) 
                             for match in matching_data}
                
                correct_count = 0
                for pair in correct_pairs:
                    user_pair = (pair.id, pair.right_text.strip())
                    if user_pair in user_pairs:
                        correct_count += 1
                
                if correct_pairs.count() > 0:
                    correct_ratio = correct_count / correct_pairs.count()
                    user_answer.score = int((question.question_score if question.question_score else 1) * correct_ratio)
                else:
                    user_answer.score = 0
                
                user_answer.save()
        
        from unireax_main.utils.course_progress import check_course_completion        
        completion_data = check_course_completion(user.id, course_id)        
        if completion_data['completed'] and not user_course.status_course:
            user_course.status_course = True
            user_course.completion_date = timezone.now()
            user_course.save()
            
            logger.info(f"Курс '{user_course.course.course_name}' завершен пользователем {user.username}")
        
        certificate_issued = False
        certificate_data = None
        
        # здесь проверяются условия для выдачи сертификата:
        # 1. курс завершен пользователем
        # 2. курс предусматривает сертификат
        # 3. курс полностью готов (завершено наполнение материалами)
        # 4. сертификат еще не выдан
        
        if (user_course.status_course and 
            user_course.course.has_certificate and 
            user_course.course.is_completed and
            not Certificate.objects.filter(user_course=user_course).exists()):
            
            try:
                from unireax_main.utils.certificate_generator import generate_certificate_pdf                
                certificate = Certificate.objects.create(
                    user_course=user_course,
                    issue_date=timezone.now().date()
                )
                
                pdf_path = generate_certificate_pdf(certificate)
                certificate.certificate_file_path = pdf_path
                certificate.save()
                
                certificate_issued = True
                certificate_data = {
                    'id': certificate.id,
                    'certificate_number': certificate.certificate_number,
                    'issue_date': certificate.issue_date,
                    'certificate_file_path': certificate.certificate_file_path,
                }
                
                logger.info(f"Сертификат {certificate.certificate_number} выдан пользователю {user.username} за курс '{user_course.course.course_name}'")
                
            except Exception as e:
                logger.error(f"Ошибка создания сертификата: {e}")
        
        response_data = {
            'test_result_id': test_result.id,
            'total_score': total_score,
            'max_score': max_score,
            'time_spent': time_spent,
            'attempt_number': attempt_number,
            'max_attempts': test.max_attempts,
            'grading_form': test.grading_form,
            'is_passed': passed_for_response,  
            'course_completed': user_course.status_course,
            'course_progress': completion_data['progress'],
            'course_progress_details': completion_data['details'],
            'certificate_issued': certificate_issued,
            'certificate': certificate_data,
        }
        
        return Response(response_data)


# для практических заданий слушателя
class ListenerAssignmentViewSet(viewsets.ModelViewSet):
    """Работа с практическими заданиями для слушателей"""
    serializer_class = UserPracticalAssignmentSerializer
    permission_classes = [IsAuthenticated, IsListenerPermission]
    
    def get_queryset(self):
        user = self.request.user
        
        user_courses = UserCourse.objects.filter(
            user=user,
            is_active=True
        ).values_list('course_id', flat=True)
        
        return UserPracticalAssignment.objects.filter(
            user=user,
            practical_assignment__lecture__course_id__in=user_courses
        ).select_related('practical_assignment', 'submission_status')
    
    def create(self, request, *args, **kwargs):
        """Отправить практическую работу"""
        user = request.user
        assignment_id = request.data.get('practical_assignment')
        comment = request.data.get('comment', '')
        files = request.FILES.getlist('files')
        
        try:
            assignment = PracticalAssignment.objects.get(id=assignment_id)
            
            if not self._has_access_to_assignment(user, assignment):
                return Response(
                    {"detail": "У вас нет доступа к этому заданию"},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            if assignment.assignment_deadline and timezone.now() > assignment.assignment_deadline:
                if not assignment.is_can_pin_after_deadline:
                    return Response(
                        {"detail": "Срок сдачи задания истек"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            previous_submissions = UserPracticalAssignment.objects.filter(
                user=user,
                practical_assignment=assignment
            )

            attempt_number = previous_submissions.count() + 1 
            default_status = AssignmentStatus.objects.get(assignment_status_name='на проверке')
            
            user_assignment = UserPracticalAssignment.objects.create(
                user=user,
                practical_assignment=assignment,
                submission_date=timezone.now(),
                submission_status=default_status,
                attempt_number=attempt_number,
                comment=comment
            )
            
            for file in files:
                AssignmentSubmissionFile.objects.create(
                    user_assignment=user_assignment,
                    file=file,
                    file_name=file.name,
                    file_size=file.size
                )
            
            serializer = self.get_serializer(user_assignment)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except PracticalAssignment.DoesNotExist:
            return Response(
                {"detail": "Задание не найдено"},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def feedback(self, request, pk=None):
        """Получить обратную связь по заданию"""
        user_assignment = self.get_object()
        
        if user_assignment.user != request.user:
            return Response(
                {"detail": "У вас нет доступа к этому заданию"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        feedback = Feedback.objects.filter(user_practical_assignment=user_assignment).first()
        
        if not feedback:
            return Response({"detail": "Обратная связь еще не предоставлена"})
        
        serializer = FeedbackSerializer(feedback)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def my_assignments(self, request):
        """Мои практические задания с фильтрацией"""
        user = request.user
        
        queryset = self.get_queryset()
        
        status_filter = request.query_params.get('status')
        course_filter = request.query_params.get('course')
        
        if status_filter:
            queryset = queryset.filter(submission_status_id=status_filter)
        
        if course_filter:
            queryset = queryset.filter(
                practical_assignment__lecture__course_id=course_filter
            )
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    def _has_access_to_assignment(self, user, assignment):
        """Проверяет, имеет ли пользователь доступ к заданию"""
        user_courses = UserCourse.objects.filter(
            user=user,
            is_active=True
        ).values_list('course_id', flat=True)
        
        return assignment.lecture.course_id in user_courses

# для отзывов слушателя
class ListenerReviewViewSet(viewsets.ModelViewSet):
    """Работа с отзывами для слушателей"""
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticated, IsListenerPermission]
    
    def get_queryset(self):
        user = self.request.user
        return Review.objects.filter(user=user)
    
    def create(self, request, *args, **kwargs):
        """Оставить отзыв на курс"""
        course_id = request.data.get('course')
        rating = request.data.get('rating')
        comment_review = request.data.get('comment_review', '')
        
        user = request.user
        
        try:
            course = Course.objects.get(id=course_id)
            user_course = UserCourse.objects.filter(
                user=user,
                course=course,
                status_course=True  
            ).exists()
            
            if not user_course:
                return Response(
                    {"detail": "Вы можете оставить отзыв только на завершенный курс"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if Review.objects.filter(user=user, course=course).exists():
                return Response(
                    {"detail": "Вы уже оставляли отзыв на этот курс"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            review = Review.objects.create(
                course=course,
                user=user,
                rating=rating,
                comment_review=comment_review,
                publish_date=timezone.now(),
                is_approved=False  
            )
            
            serializer = self.get_serializer(review)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Course.DoesNotExist:
            return Response(
                {"detail": "Курс не найден"},
                status=status.HTTP_404_NOT_FOUND
            )

# для сертификатов слушателя
class ListenerCertificateViewSet(viewsets.ReadOnlyModelViewSet):
    """Сертификаты слушателя"""
    serializer_class = CertificateSerializer
    permission_classes = [IsAuthenticated, IsListenerPermission]
    
    def get_queryset(self):
        user = self.request.user
        return Certificate.objects.filter(user_course__user=user)

# для статистики слушателя
class ListenerStatisticsView(APIView):
    """Статистика слушателя"""
    permission_classes = [IsAuthenticated, IsListenerPermission]
    
    def get(self, request):
        user = request.user
        
        enrolled_courses = UserCourse.objects.filter(user=user, is_active=True)
        completed_courses = enrolled_courses.filter(status_course=True)
        active_courses = enrolled_courses.filter(status_course=False)
        
        certificates = Certificate.objects.filter(user_course__user=user).count()

        course_progress = []
        for user_course in enrolled_courses:
            progress = calculate_course_completion(user.id, user_course.course.id)
            course_progress.append({
                'course_id': user_course.course.id,
                'course_name': user_course.course.course_name,
                'progress': progress
            })
        
        assignments = UserPracticalAssignment.objects.filter(user=user)
        completed_assignments = assignments.filter(submission_status__assignment_status_name='завершено')
        pending_assignments = assignments.filter(submission_status__assignment_status_name='на проверке')
        
        test_results = TestResult.objects.filter(user=user)
        passed_tests = test_results.filter(is_passed=True)
        avg_test_score = test_results.filter(final_score__isnull=False).aggregate(avg=Avg('final_score'))['avg'] or 0
        
        return Response({
            'general': {
                'enrolled_courses': enrolled_courses.count(),
                'completed_courses': completed_courses.count(),
                'active_courses': active_courses.count(),
                'certificates': certificates
            },
            'progress': course_progress,
            'assignments': {
                'total': assignments.count(),
                'completed': completed_assignments.count(),
                'pending': pending_assignments.count()
            },
            'tests': {
                'total': test_results.count(),
                'passed': passed_tests.count(),
                'average_score': avg_test_score
            }
        })
      
# для смены пароля слушателя
class ListenerChangePasswordView(APIView):
    """Смена пароля для слушателя"""
    permission_classes = [IsAuthenticated, IsListenerPermission]
    
    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user

            if not user.check_password(serializer.validated_data['old_password']):
                return Response(
                    {"detail": "Неверный старый пароль"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            return Response({"detail": "Пароль успешно изменен"})
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# профиль слушателя
class ListenerProfileView(APIView):
    """Профиль слушателя"""
    permission_classes = [IsAuthenticated, IsListenerPermission]
    
    def get(self, request):
        """Получить профиль"""
        serializer = UserSerializer(request.user)
        return Response(serializer.data)
    
    def put(self, request):
        """Обновить профиль"""
        user = request.user
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            allowed_fields = ['first_name', 'last_name', 'patronymic', 'email', 'is_light_theme']
            for field in request.data:
                if field not in allowed_fields:
                    return Response(
                        {"detail": f"Поле {field} нельзя изменять"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ListenerStatisticsPDFView(APIView):
    """PDF отчет статистики слушателя"""
    permission_classes = [IsAuthenticated, IsListenerPermission]
    
    def get(self, request):
        """Сгенерировать PDF отчет о статистике"""
        user = request.user
        
        buffer = BytesIO()
        pdf = canvas.Canvas(buffer, pagesize=A4)
        
        pdf.setTitle(f"Отчет слушателя - {user.full_name}")
        pdf.setFont("Helvetica-Bold", 16)
        pdf.drawString(100, 800, f"Отчет о прогрессе: {user.full_name}")

        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, 770, f"Дата генерации: {timezone.now().strftime('%d.%m.%Y %H:%M')}")
        
        enrolled_courses = UserCourse.objects.filter(user=user, is_active=True).count()
        completed_courses = UserCourse.objects.filter(user=user, status_course=True).count()
        certificates = Certificate.objects.filter(user_course__user=user).count()
        
        y_position = 740
        pdf.drawString(100, y_position, f"Записан на курсов: {enrolled_courses}")
        y_position -= 20
        pdf.drawString(100, y_position, f"Завершено курсов: {completed_courses}")
        y_position -= 20
        pdf.drawString(100, y_position, f"Получено сертификатов: {certificates}")

        assignments = UserPracticalAssignment.objects.filter(user=user)
        completed_assignments = assignments.filter(submission_status__assignment_status_name='завершено').count()
        pending_assignments = assignments.filter(submission_status__assignment_status_name='на проверке').count()
        
        y_position -= 40
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(100, y_position, "Статистика по заданиям:")
        y_position -= 20
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, y_position, f"Всего заданий: {assignments.count()}")
        y_position -= 20
        pdf.drawString(100, y_position, f"Зачтено: {completed_assignments}")
        y_position -= 20
        pdf.drawString(100, y_position, f"Ожидают проверки: {pending_assignments}")
        
        test_results = TestResult.objects.filter(user=user)
        passed_tests = test_results.filter(is_passed=True).count()
        avg_test_score = test_results.filter(final_score__isnull=False).aggregate(avg=Avg('final_score'))['avg'] or 0
        
        y_position -= 40
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(100, y_position, "Статистика по тестам:")
        y_position -= 20
        pdf.setFont("Helvetica", 12)
        pdf.drawString(100, y_position, f"Всего тестов: {test_results.count()}")
        y_position -= 20
        pdf.drawString(100, y_position, f"Пройдено успешно: {passed_tests}")
        y_position -= 20
        pdf.drawString(100, y_position, f"Средний балл: {avg_test_score:.2f}")
        
        y_position -= 40
        pdf.setFont("Helvetica-Bold", 14)
        pdf.drawString(100, y_position, "Активные курсы:")
        y_position -= 20
        pdf.setFont("Helvetica", 12)
        
        active_user_courses = UserCourse.objects.filter(user=user, is_active=True, status_course=False)
        for user_course in active_user_courses[:5]:  
            progress = calculate_course_completion(user.id, user_course.course.id)
            course_text = f"- {user_course.course.course_name[:40]}: {progress}%"
            if len(course_text) > 60:
                course_text = course_text[:57] + "..."
            pdf.drawString(120, y_position, course_text)
            y_position -= 20
            if y_position < 50: 
                break
        
        pdf.save()
        
        buffer.seek(0)
        
        response = HttpResponse(buffer, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="student_report_{user.id}_{timezone.now().strftime("%Y%m%d")}.pdf"'
        return response

# регистрация и авторизация
class RegisterView(generics.CreateAPIView):
    serializer_class = RegisterSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        email = request.data.get('email')
        is_verified = cache.get(f'email_verified_{email}', False)
        
        if not is_verified:
            return Response({
                'error': 'Email не подтвержден',
                'need_verification': True,
                'message': 'Сначала подтвердите email кодом из письма'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        try:
            listener_role = Role.objects.get(role_name='слушатель курсов')
            user.role = listener_role
        except Role.DoesNotExist:
            listener_role = Role.objects.create(role_name='слушатель курсов')
            user.role = listener_role
        except Exception as e:
            logger.error(f'ошибка при установке роли: {e}')
        
        user.is_verified = True        
        user.save()
        
        cache.delete(f'email_verified_{email}')
        cache.delete(f'verification_code_{email}')
        
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserSerializer(user, context=self.get_serializer_context()).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }, status=status.HTTP_201_CREATED)


def get_client_ip(request):
    """
    Получение реального IP адреса клиента.
    Работает корректно с HTTP, HTTPS, прокси, CloudFlare и на локалке.
    """
    ip_address = None
    
    ip_headers = [
        'HTTP_CF_CONNECTING_IP',      
        'HTTP_X_FORWARDED_FOR',     
        'HTTP_X_REAL_IP',           
        'HTTP_CLIENT_IP',         
        'REMOTE_ADDR',               
    ]
    
    for header in ip_headers:
        value = request.META.get(header)
        if value:
            if header == 'HTTP_X_FORWARDED_FOR':
                ip_address = value.split(',')[0].strip()
            else:
                ip_address = value.strip()
            
            if ip_address:
                logger.debug(f"IP from {header}: {ip_address}")
                break

    if settings.DEBUG and ip_address in ['127.0.0.1', 'localhost', '::1']:
        ip_address = '127.0.0.1'
        logger.debug(f"Development mode, using IP: {ip_address}")
    
    if ip_address:
        try:
            import ipaddress 
            ipaddress.ip_address(ip_address)
        except ValueError:
            logger.warning(f"Invalid IP address detected: {ip_address}")
            ip_address = '0.0.0.0'
    else:
        ip_address = '0.0.0.0'
    
    logger.info(f"Final client IP: {ip_address}")
    return ip_address


def get_attempts_key(ip_address):
    """Ключ для кэша попыток"""
    return f"login_attempts:{ip_address}"


def get_block_key(ip_address):
    """Ключ для кэша блокировки"""
    return f"login_block:{ip_address}"


def check_rate_limit(ip_address):
    """
    Проверяет лимиты попыток входа по IP
    Возвращает: (is_blocked, remaining_attempts, seconds_left)
    """
    if not ip_address or ip_address == '0.0.0.0':
        return False, MAX_ATTEMPTS, 0
    
    block_key = get_block_key(ip_address)
    block_until = cache.get(block_key)
    
    if block_until:
        now = timezone.now()

        if isinstance(block_until, (int, float)):
            from datetime import datetime
            block_until = datetime.fromtimestamp(block_until, tz=timezone.get_current_timezone())
        
        if now < block_until:
            seconds_left = int((block_until - now).total_seconds())
            return True, 0, seconds_left
        else:
            cache.delete(block_key)
    
    attempts_key = get_attempts_key(ip_address)
    attempts = cache.get(attempts_key, [])
    window_start = timezone.now() - timedelta(minutes=ATTEMPT_WINDOW_MINUTES)
    recent_attempts = [a for a in attempts if a > window_start]
    if len(recent_attempts) != len(attempts):
        cache.set(attempts_key, recent_attempts, timeout=ATTEMPT_WINDOW_MINUTES * 60 + 60)
    
    remaining_attempts = max(0, MAX_ATTEMPTS - len(recent_attempts))
    logger.debug(f"IP {ip_address} - attempts: {len(recent_attempts)}, remaining: {remaining_attempts}")
    
    return False, remaining_attempts, 0


def record_failed_attempt(ip_address):
    """
    Записывает неудачную попытку по IP
    Возвращает: (was_blocked, remaining_attempts, seconds_left)
    """
    if not ip_address or ip_address == '0.0.0.0':
        return False, MAX_ATTEMPTS, 0
    
    attempts_key = get_attempts_key(ip_address)
    attempts = cache.get(attempts_key, [])
    window_start = timezone.now() - timedelta(minutes=ATTEMPT_WINDOW_MINUTES)
    attempts = [a for a in attempts if a > window_start]
    attempts.append(timezone.now())
    if len(attempts) >= MAX_ATTEMPTS:
        block_key = get_block_key(ip_address)
        block_until = timezone.now() + timedelta(minutes=BLOCK_MINUTES)
        cache.set(block_key, block_until, timeout=BLOCK_MINUTES * 60)
        cache.delete(attempts_key)
        
        logger.warning(f"IP {ip_address} BLOCKED for {BLOCK_MINUTES} minutes")
        return True, 0, BLOCK_MINUTES * 60
    else:
        cache.set(attempts_key, attempts, timeout=ATTEMPT_WINDOW_MINUTES * 60 + 60)
        remaining = MAX_ATTEMPTS - len(attempts)
        return False, remaining, 0


def clear_attempts(ip_address):
    """Очищает попытки и блокировку после успешного входа"""
    if ip_address and ip_address != '0.0.0.0':
        attempts_key = get_attempts_key(ip_address)
        block_key = get_block_key(ip_address)
        cache.delete(attempts_key)
        cache.delete(block_key)


class LoginView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            logger.warning(f"Validation error: {serializer.errors}")
            return Response(
                {
                    'error': True,
                    'message': 'Неверный формат данных',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        remember_me = serializer.validated_data.get('remember_me', False)
        
        ip_address = get_client_ip(request)
        is_blocked, remaining_attempts, seconds_left = check_rate_limit(ip_address)
        
        if is_blocked:
            minutes_left = (seconds_left + 59) // 60
            logger.warning(f"Access blocked for IP {ip_address}")
            return Response(
                {
                    'error': True,
                    'blocked': True,
                    'message': f'Слишком много неудачных попыток. Попробуйте через {minutes_left} минут.',
                    'minutes_left': minutes_left,
                    'seconds_left': seconds_left,
                    'remaining_attempts': 0,
                    'max_attempts': MAX_ATTEMPTS
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )
        
        user = authenticate(request, username=username, password=password)
        if user:
            if not user.is_active:
                logger.warning(f"User {username} is inactive")
                return Response(
                    {
                        'error': True,
                        'message': 'Ваш аккаунт деактивирован. Обратитесь к администратору.'
                    },
                    status=status.HTTP_403_FORBIDDEN
                )

            clear_attempts(ip_address)
            refresh = RefreshToken.for_user(user)
            if remember_me:
                refresh.set_exp(lifetime=timedelta(days=30))
                access_lifetime = timedelta(days=1)
            else:
                refresh.set_exp(lifetime=timedelta(hours=12))
                access_lifetime = timedelta(hours=1)
            
            refresh.access_token.set_exp(lifetime=access_lifetime)
            
            logger.info(f"Successful login for user {username}")
            
            from .serializers import UserSerializer
            user_data = UserSerializer(user).data
            
            response_data = {
                'user': user_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh),
                'expires_in': int(access_lifetime.total_seconds())
            }
            
            if user.role:
                response_data['role'] = user.role.role_name
            
            return Response(response_data)
        
        else:
            was_blocked, remaining, seconds_left = record_failed_attempt(ip_address)   
            is_blocked, remaining_attempts, seconds_left = check_rate_limit(ip_address)
            
            if is_blocked:
                minutes_left = (seconds_left + 59) // 60
                return Response(
                    {
                        'error': True,
                        'blocked': True,
                        'message': f'Слишком много неудачных попыток. Доступ заблокирован на {BLOCK_MINUTES} минут.',
                        'minutes_left': minutes_left,
                        'seconds_left': seconds_left,
                        'remaining_attempts': 0,
                        'max_attempts': MAX_ATTEMPTS
                    },
                    status=status.HTTP_429_TOO_MANY_REQUESTS
                )
            else:
                remaining_attempts = MAX_ATTEMPTS - (MAX_ATTEMPTS - remaining) if remaining > 0 else MAX_ATTEMPTS - 1
                
                return Response(
                    {
                        'error': True,
                        'blocked': False,
                        'message': 'Неверное имя пользователя или пароль',
                        'remaining_attempts': remaining_attempts,
                        'max_attempts': MAX_ATTEMPTS
                    },
                    status=status.HTTP_401_UNAUTHORIZED
                )

class LogoutView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if refresh_token:
                RefreshToken(refresh_token)
                return Response(
                    {"detail": "Успешный выход из системы"},
                    status=status.HTTP_200_OK
                )
            return Response(
                {"detail": "Refresh token обязателен"},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {"detail": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class StatisticsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Базовая статистика для всех пользователей"""
        total_users = User.objects.count()
        total_courses = Course.objects.filter(is_active=True).count()
        total_enrollments = UserCourse.objects.filter(is_active=True).count()
        total_certificates = Certificate.objects.count()
        active_users = UserCourse.objects.filter(
            is_active=True
        ).values('user').distinct().count()
        
        avg_rating = Review.objects.filter(
            is_approved=True
        ).aggregate(Avg('rating'))['rating__avg'] or 0
        
        return Response({
            "total_users": total_users,
            "total_courses": total_courses,
            "average_rating": round(avg_rating, 1),
            "active_users": active_users,
            "total_enrollments": total_enrollments,
            "total_certificates": total_certificates,
        })


class PaymentViewSet(viewsets.ViewSet):
    """viewset для работы с платежами через ЮКассу"""
    permission_classes = [IsAuthenticated]
    
    @action(detail=False, methods=['post'], url_path='create/(?P<course_id>[^/.]+)')
    def create_payment(self, request, course_id=None):
        """Создание платежа в ЮКассе"""
        try:
            logger.info(f"создание платежа для курса {course_id}")
            
            from django.conf import settings
            import uuid
            from yookassa import Configuration, Payment
            
            shop_id = str(settings.YOOKASSA_SHOP_ID).strip()
            secret_key = str(settings.YOOKASSA_SECRET_KEY).strip()
            Configuration.account_id = shop_id
            Configuration.secret_key = secret_key
            
            course = Course.objects.get(id=course_id, is_active=True)
            user = request.user
            
            if UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
                return Response(
                    {'detail': 'Вы уже записаны на этот курс'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not course.course_price or course.course_price == 0:
                return Response(
                    {'detail': 'Этот курс бесплатный. Используйте обычную запись.'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            idempotence_key = str(uuid.uuid4())            
            deep_link_scheme = 'unireax://'
            return_url = f"{deep_link_scheme}payment/success?payment_id={{payment_id}}&course_id={course.id}"
            logger.info(f"return-URL для мобильного приложения: {return_url}")
            payment = Payment.create({
                "amount": {
                    "value": f"{course.course_price:.2f}",
                    "currency": "RUB"
                },
                "confirmation": {
                    "type": "redirect",
                    "return_url": return_url
                },
                "capture": True,
                "description": f"Оплата курса: {course.course_name}",
                "metadata": {
                    "course_id": str(course.id),
                    "user_id": str(user.id),
                    "course_name": course.course_name
                }
            }, idempotence_key)
            
            from django.core.cache import cache
            cache_key = f"yookassa_payment_{user.id}_{course.id}"
            cache_data = {
                'payment_id': payment.id,
                'course_id': course.id,
                'user_id': user.id,
                'amount': str(course.course_price),
                'created_at': timezone.now().isoformat(),
            }
            cache.set(cache_key, cache_data, timeout=3600)
            
            return Response({
                'success': True,
                'payment_id': payment.id,
                'confirmation_url': payment.confirmation.confirmation_url,
                'amount': str(course.course_price),
                'course_name': course.course_name,
                'course_id': course.id,
                'return_url_scheme': deep_link_scheme,
            })
            
        except Course.DoesNotExist:
            return Response(
                {'detail': 'Курс не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            logger.error(f"Ошибка создания платежа: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return Response(
                {'detail': f'Ошибка создания платежа: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['get'], url_path='status')
    def payment_status(self, request, pk=None):
        """Проверка статуса платежа"""
        try:
            from yookassa import Payment            
            payment_id = pk
            logger.info(f"Проверка статуса платежа: {payment_id}")
            
            payment = Payment.find_one(payment_id)
            
            return Response({
                'success': True,
                'status': payment.status,
                'paid': payment.paid,
            })
            
        except Exception as e:
            logger.error(f"Ошибка проверки платежа: {e}")
            return Response(
                {'detail': f'Ошибка проверки платежа: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'], url_path='confirm')
    def confirm_payment(self, request, pk=None):
        """Подтверждение успешного платежа и запись на курс"""
        try:
            from yookassa import Payment
            
            payment_id = pk
            logger.info(f"Подтверждение платежа: {payment_id}")
            
            payment = Payment.find_one(payment_id)
            
            if payment.status != 'succeeded':
                return Response({
                    'success': False,
                    'detail': 'Платеж не завершен успешно',
                    'status': payment.status
                }, status=status.HTTP_400_BAD_REQUEST)
            
            course_id = payment.metadata.get('course_id')
            user_id = payment.metadata.get('user_id')
            
            if str(request.user.id) != user_id:
                return Response({
                    'success': False,
                    'detail': 'Неавторизованный доступ к платежу'
                }, status=status.HTTP_403_FORBIDDEN)
            
            course = Course.objects.get(id=course_id)
            user = request.user            
            existing_enrollment = UserCourse.objects.filter(
                user=user, 
                course=course,
                is_active=True
            ).first()
            
            if existing_enrollment:
                return Response({
                    'success': True,
                    'message': 'Вы уже записаны на этот курс',
                    'course_id': course.id,
                })
            
            user_course = UserCourse.objects.create(
                user=user,
                course=course,
                course_price=course.course_price,
                payment_date=timezone.now(),
                payment_id=payment_id, 
                is_active=True,
                status_course=False,
                registration_date=timezone.now().date()
            )
            
            logger.info(f"Пользователь {user.username} записан на курс {course.course_name} после оплаты")
            logger.info(f"Payment ID сохранен: {payment_id}")
            
            return Response({
                'success': True,
                'message': 'Курс успешно оплачен и активирован',
                'course_id': course.id,
                'user_course_id': user_course.id,
                'payment_id': payment_id,  
            })
            
        except Course.DoesNotExist:
            return Response({
                'success': False,
                'detail': 'Курс не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            logger.error(f"Ошибка подтверждения платежа: {e}")
            return Response({
                'success': False,
                'detail': f'Ошибка подтверждения платежа: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    @action(detail=True, methods=['get'], url_path='receipt')
    def get_receipt(self, request, pk=None):
        """Получение данных для чека"""
        try:
            from yookassa import Payment
            
            payment_id = pk
            payment = Payment.find_one(payment_id)
            
            if payment.status != 'succeeded':
                return Response({
                    'success': False,
                    'detail': 'Чек доступен только для успешных платежей'
                }, status=status.HTTP_400_BAD_REQUEST)
            
            course_id = payment.metadata.get('course_id')
            user_id = payment.metadata.get('user_id')
            
            if str(request.user.id) != user_id:
                return Response({
                    'success': False,
                    'detail': 'Неавторизованный доступ к чеку'
                }, status=status.HTTP_403_FORBIDDEN)
            
            course = Course.objects.get(id=course_id)
            user = request.user
            
            user_course = UserCourse.objects.filter(
                user=user,
                course=course,
                payment_date__isnull=False
            ).first()
            
            if not user_course:
                return Response({
                    'success': False,
                    'detail': 'Запись о курсе не найдена'
                }, status=status.HTTP_404_NOT_FOUND)
            
            receipt_data = {
                'success': True,
                'payment_id': payment_id,
                'payment_date': user_course.payment_date.strftime('%d.%m.%Y %H:%M'),
                'course_name': course.course_name,
                'course_category': course.course_category.course_category_name if course.course_category else 'Не указана',
                'course_type': course.course_type.course_type_name if course.course_type else 'Не указан',
                'course_hours': course.course_hours,
                'user_name': f"{user.last_name} {user.first_name}",
                'user_email': user.email,
                'amount': payment.amount.value,
                'currency': payment.amount.currency,
                'status': 'Оплачено',
            }
            return Response(receipt_data)
        except Exception as e:
            logger.error(f"Ошибка получения чека: {e}")
            return Response({
                'success': False,
                'detail': f'Ошибка получения чека: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
class UserProfileView(APIView):
    """профиль пользователя с историей оплат"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        paid_courses = UserCourse.objects.filter(
            user=user,
            payment_date__isnull=False, 
            is_active=True
        ).select_related('course').order_by('-payment_date')
        
        payment_history = []
        for user_course in paid_courses:
            payment_history.append({
                'id': user_course.id,
                'course_id': user_course.course.id,
                'course_name': user_course.course.course_name,
                'amount': str(user_course.course_price) if user_course.course_price else '0',
                'payment_date': user_course.payment_date,
                'payment_id': user_course.payment_id,  
                'status': 'Оплачено',
                'is_active': user_course.is_active,
                'status_course': 'Завершен' if user_course.status_course else 'В процессе',
            })
        
        total_spent = sum([float(p['amount']) for p in payment_history])
        total_paid_courses = len(payment_history)
        total_enrolled = UserCourse.objects.filter(user=user, is_active=True).count()
        
        user_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'patronymic': user.patronymic,
            'full_name': user.full_name,
            'role': user.role.role_name if user.role else 'Слушатель курсов',
            'date_joined': user.date_joined,
            'is_verified': user.is_verified,
        }
        
        return Response({
            'user': user_data,
            'statistics': {
                'total_enrolled': total_enrolled,
                'total_paid_courses': total_paid_courses,
                'total_spent': f"{total_spent:.2f}",
            },
            'payment_history': payment_history, 
        })
    
class CanEnrollPermission(BasePermission):
    """
    Разрешение для записи на курсы.
    Разрешает запись если пользователь авторизован.
    """
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated
    

class ListenerProgressViewSet(viewsets.ViewSet):
    """API для прогресса слушателя курсов"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Получить все курсы пользователя с прогрессом"""
        user = request.user
        
        user_courses = UserCourse.objects.filter(
            user=user,
            is_active=True
        ).select_related('course', 'course__course_category', 'course__course_type')
        
        courses_with_progress = []
        for user_course in user_courses:
            course = user_course.course
            progress = calculate_course_completion(user.id, course.id)
            
            course_data = {
                'id': course.id,
                'name': course.course_name,
                'description': course.course_description,
                'image_url': course.course_photo_path.url if course.course_photo_path else None,
                'category': course.course_category.course_category_name if course.course_category else None,
                'type': course.course_type.course_type_name if course.course_type else None,
                'hours': course.course_hours,
                'has_certificate': course.has_certificate,
                'progress': progress,
                'enrollment_date': user_course.registration_date,
                'is_completed': user_course.status_course,
                'completion_date': user_course.completion_date
            }
            
            courses_with_progress.append(course_data)
        
        return Response(courses_with_progress)
    
    @action(detail=True, methods=['get'])
    def course_materials(self, request, course_id=None):
        """Получить материалы конкретного курса"""
        if not course_id:
            return Response({"detail": "Не указан ID курса"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        user_course = get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        course = user_course.course
        
        lectures = Lecture.objects.filter(
            course=course,
            is_active=True
        ).order_by('lecture_order')
        
        assignments = PracticalAssignment.objects.filter(
            lecture__course=course,
            is_active=True
        ).select_related('lecture').order_by('lecture__lecture_order')
        
        tests = Test.objects.filter(
            lecture__course=course,
            is_active=True
        ).select_related('lecture').order_by('lecture__lecture_order')
        
        user_assignments = UserPracticalAssignment.objects.filter(
            user=user,
            practical_assignment__lecture__course=course
        ).select_related('practical_assignment', 'submission_status')
        
        user_test_results = TestResult.objects.filter(
            user=user,
            test__lecture__course=course
        ).select_related('test')
        
        materials_by_lecture = []
        for lecture in lectures:
            lecture_assignments = [a for a in assignments if a.lecture_id == lecture.id]
            lecture_tests = [t for t in tests if t.lecture_id == lecture.id]
            
            assignments_with_status = []
            for assignment in lecture_assignments:
                user_assignment = next(
                    (ua for ua in user_assignments if ua.practical_assignment_id == assignment.id),
                    None
                )
                
                assignment_data = PracticalAssignmentSerializer(assignment).data
                if user_assignment:
                    assignment_data['user_status'] = {
                        'submission_status': user_assignment.submission_status.assignment_status_name,
                        'submission_date': user_assignment.submission_date,
                        'attempt_number': user_assignment.attempt_number,
                        'has_feedback': Feedback.objects.filter(user_practical_assignment=user_assignment).exists()
                    }
                else:
                    assignment_data['user_status'] = None
                
                assignment_data['is_overdue'] = (
                    assignment.assignment_deadline and 
                    assignment.assignment_deadline < timezone.now()
                )
                
                assignments_with_status.append(assignment_data)

            tests_with_results = []
            for test in lecture_tests:
                user_result = next(
                    (ur for ur in user_test_results if ur.test_id == test.id),
                    None
                )
                
                test_data = TestSerializer(test).data
                if user_result:
                    test_data['user_result'] = {
                        'final_score': user_result.final_score,
                        'is_passed': user_result.is_passed,
                        'completion_date': user_result.completion_date,
                        'attempt_number': user_result.attempt_number
                    }
                else:
                    test_data['user_result'] = None
                
                tests_with_results.append(test_data)
            
            materials_by_lecture.append({
                'lecture': LectureSerializer(lecture).data,
                'assignments': assignments_with_status,
                'tests': tests_with_results
            })
        
        return Response({
            'course': CourseSerializer(course).data,
            'materials_by_lecture': materials_by_lecture,
            'total_progress': calculate_course_completion(user.id, course.id)
        })
    
    @action(detail=True, methods=['get'])
    def lecture_detail(self, request, course_id=None, lecture_id=None):
        """Получить детали лекции"""
        if not course_id or not lecture_id:
            return Response({"detail": "Не указаны course_id или lecture_id"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        lecture = get_object_or_404(
            Lecture,
            id=lecture_id,
            course_id=course_id,
            is_active=True
        )
        
        return Response(LectureSerializer(lecture).data)
    
    @action(detail=True, methods=['get'])
    def assignment_detail(self, request, course_id=None, assignment_id=None):
        """Получить детали практического задания"""
        if not course_id or not assignment_id:
            return Response({"detail": "Не указаны course_id или assignment_id"}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        assignment = get_object_or_404(
            PracticalAssignment,
            id=assignment_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        user_assignments = UserPracticalAssignment.objects.filter(
            user=user,
            practical_assignment=assignment
        ).order_by('-attempt_number')
        
        feedback_list = []
        for ua in user_assignments:
            feedback = Feedback.objects.filter(user_practical_assignment=ua).first()
            if feedback:
                feedback_list.append({
                    'attempt_number': ua.attempt_number,
                    'feedback': FeedbackSerializer(feedback).data,
                    'submission_date': ua.submission_date
                })
        
        assignment_data = PracticalAssignmentSerializer(assignment).data
        
        teacher_files = TeacherAssignmentFile.objects.filter(
            practical_assignment=assignment,
            is_active=True
        )
        
        return Response({
            'assignment': assignment_data,
            'submission_history': UserPracticalAssignmentSerializer(user_assignments, many=True).data,
            'feedback': feedback_list,
            'teacher_files': TeacherAssignmentFileSerializer(teacher_files, many=True).data,
            'can_submit': assignment.is_active and (
                not assignment.assignment_deadline or
                assignment.assignment_deadline > timezone.now() or
                assignment.is_can_pin_after_deadline
            )
        })
    
    @action(detail=True, methods=['post'])
    def submit_assignment(self, request, course_id=None, assignment_id=None):
        """Отправить практическое задание"""
        if not course_id or not assignment_id:
            return Response({"detail": "Не указаны course_id или assignment_id"}, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        assignment = get_object_or_404(
            PracticalAssignment,
            id=assignment_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        if assignment.assignment_deadline and timezone.now() > assignment.assignment_deadline:
            if not assignment.is_can_pin_after_deadline:
                return Response(
                    {'detail': 'Срок сдачи задания истек'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        previous_submissions = UserPracticalAssignment.objects.filter(
            user=user,
            practical_assignment=assignment
        )
        attempt_number = previous_submissions.count() + 1
        
        pending_status = get_object_or_404(AssignmentStatus, assignment_status_name='на проверке')
        
        submission_data = {
            'user': user.id,
            'practical_assignment': assignment.id,
            'submission_date': timezone.now(),
            'submission_status': pending_status.id,
            'attempt_number': attempt_number,
            'comment': request.data.get('comment', '')
        }
        
        serializer = UserPracticalAssignmentSerializer(data=submission_data)
        if serializer.is_valid():
            user_assignment = serializer.save()
            files = request.FILES.getlist('files')
            
            for file in files:
                if file.size > 100 * 1024 * 1024:  
                    return Response(
                        {"detail": f"Файл {file.name} слишком большой. Максимальный размер: 100 МБ"},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                AssignmentSubmissionFile.objects.create(
                    user_assignment=user_assignment,
                    file=file,
                    file_name=file.name,
                    file_size=file.size
                )
            
            return Response({
                'detail': 'Задание успешно отправлено',
                'submission': UserPracticalAssignmentSerializer(user_assignment).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'], url_path='assignment/(?P<assignment_id>[^/.]+)/attempts')
    def assignment_attempts(self, request, course_id=None, assignment_id=None):
        """Получить все попытки сдачи задания с обратной связью"""
        if not course_id or not assignment_id:
            return Response({"detail": "Не указаны course_id или assignment_id"}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        assignment = get_object_or_404(
            PracticalAssignment,
            id=assignment_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        attempts = UserPracticalAssignment.objects.filter(
            user=user,
            practical_assignment=assignment
        ).select_related('submission_status').prefetch_related(
            'assignmentsubmissionfile_set'
        ).order_by('-attempt_number')
        
        attempts_data = []
        for attempt in attempts:
            attempt_files = attempt.assignmentsubmissionfile_set.all()
            
            feedback = Feedback.objects.filter(
                user_practical_assignment=attempt
            ).select_related('given_by').first()
            
            status_name = attempt.submission_status.assignment_status_name
            can_edit = status_name in ['на проверке', 'на доработке']
            
            is_overdue = (
                assignment.assignment_deadline and 
                attempt.submission_date and 
                attempt.submission_date > assignment.assignment_deadline
            ) if assignment.assignment_deadline else False
            
            feedback_data = None
            if feedback:
                feedback_data = {
                    'id': feedback.id,
                    'score': feedback.score,
                    'is_passed': feedback.is_passed,
                    'feedback_text': feedback.comment_feedback,
                    'grade': feedback.score if feedback.score is not None else 'Зачтено' if feedback.is_passed else 'Не зачтено',
                    'given_by': {
                        'id': feedback.given_by.id if feedback.given_by else None,
                        'name': feedback.given_by.get_full_name() if feedback.given_by else None,
                    },
                    'given_at': feedback.given_at,
                }
            
            attempts_data.append({
                'id': attempt.id,
                'attempt_number': attempt.attempt_number,
                'submission_date': attempt.submission_date,
                'comment': attempt.comment,
                'status': {
                    'id': attempt.submission_status.id,
                    'name': status_name,
                    'description': self._get_status_description(attempt.submission_status),
                    'can_edit': can_edit,
                    'color': self._get_status_color(attempt.submission_status),
                },
                'is_overdue': is_overdue,
                'files': [
                    {
                        'id': file.id,
                        'file_name': file.file_name,
                        'file_size': file.file_size,
                        'file_url': file.file.url if file.file else None,
                        'uploaded_at': file.uploaded_at,
                        'description': file.description,
                    }
                    for file in attempt_files
                ],
                'feedback': feedback_data,
                'grading_type': assignment.grading_type,
                'max_score': assignment.max_score if assignment.grading_type == 'points' else None,
            })
        

        can_submit_new = assignment.is_active and (
            not assignment.assignment_deadline or
            timezone.now() <= assignment.assignment_deadline or
            assignment.is_can_pin_after_deadline
        )
        
        current_attempts_count = attempts.count()
        
        return Response({
            'assignment': {
                'id': assignment.id,
                'name': assignment.practical_assignment_name,
                'description': assignment.practical_assignment_description,
                'grading_type': assignment.grading_type,
                'max_score': assignment.max_score if assignment.grading_type == 'points' else None,
                'deadline': assignment.assignment_deadline,
                'is_can_pin_after_deadline': assignment.is_can_pin_after_deadline,
                'is_active': assignment.is_active,
            },
            'attempts': attempts_data,
            'can_submit_new': can_submit_new,
            'current_attempts_count': current_attempts_count,
        })
        
    def _get_status_description(self, status):
        """Получить описание статуса"""
        status_name = status.assignment_status_name
        status_descriptions = {
            'на проверке': 'Работа ожидает проверки преподавателем',
            'просрочено': 'Срок сдачи задания истек',
            'отклонено': 'Работа отклонена преподавателем',
            'на доработке': 'Требуются исправления по замечаниям преподавателя',
            'завершено': 'Работа проверена и оценена',
        }
        return status_descriptions.get(status_name, 'Статус не определён')

    def _get_status_color(self, status):
        """Получить цвет статуса для фронтенда"""
        status_name = status.assignment_status_name
        status_colors = {
            'на проверке': 'orange',
            'просрочено': 'red',
            'отклонено': 'darkred',
            'на доработке': 'blue',
            'завершено': 'green',
        }
        return status_colors.get(status_name, 'grey')
        
    @action(detail=True, methods=['put'], url_path='assignment/(?P<assignment_id>[^/.]+)/attempt/(?P<attempt_id>[^/.]+)')
    def update_attempt(self, request, course_id=None, assignment_id=None, attempt_id=None):
        """Редактировать попытку сдачи задания"""
        if not course_id or not assignment_id or not attempt_id:
            return Response({"detail": "Не указаны все необходимые параметры"}, 
                        status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        
        get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        assignment = get_object_or_404(
            PracticalAssignment,
            id=assignment_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        attempt = get_object_or_404(
            UserPracticalAssignment,
            id=attempt_id,
            user=user,
            practical_assignment=assignment
        )
        
        status_name = attempt.submission_status.assignment_status_name
        can_edit = status_name in ['на проверке', 'на доработке']
        
        if not can_edit:
            return Response(
                {"detail": f"Эту попытку нельзя редактировать (статус: {status_name})"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if assignment.assignment_deadline and timezone.now() > assignment.assignment_deadline:
            if not assignment.is_can_pin_after_deadline:
                return Response(
                    {"detail": "Срок сдачи задания истек. Редактирование невозможно"},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        new_comment = request.data.get('comment')
        if new_comment is not None:
            attempt.comment = new_comment
        
        files_to_remove = request.data.get('files_to_remove', '')
        if files_to_remove:
            try:
                file_ids = [int(fid.strip()) for fid in files_to_remove.split(',') if fid.strip().isdigit()]
                AssignmentSubmissionFile.objects.filter(
                    user_assignment=attempt,
                    id__in=file_ids
                ).delete()
            except ValueError:
                pass
        
        files_to_add = request.FILES.getlist('files')
        for file in files_to_add:
            if file.size > 100 * 1024 * 1024:
                return Response(
                    {"detail": f"Файл {file.name} слишком большой. Максимальный размер: 100 МБ"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            AssignmentSubmissionFile.objects.create(
                user_assignment=attempt,
                file=file,
                file_name=file.name,
                file_size=file.size
            )
        
        attempt.submission_date = timezone.now()
        attempt.save()
        
        attempt.refresh_from_db()
        attempt_files = attempt.assignmentsubmissionfile_set.all()
        feedback = Feedback.objects.filter(user_practical_assignment=attempt).first()
        
        feedback_data = None
        if feedback:
            feedback_data = {
                'id': feedback.id,
                'score': feedback.score,
                'is_passed': feedback.is_passed,
                'feedback_text': feedback.comment_feedback,
                'grade': feedback.score if feedback.score is not None else 'Зачтено' if feedback.is_passed else 'Не зачтено',
                'given_by': {
                    'id': feedback.given_by.id if feedback.given_by else None,
                    'name': feedback.given_by.get_full_name() if feedback.given_by else None,
                },
                'given_at': feedback.given_at,
            }
        
        is_overdue = (
            assignment.assignment_deadline and 
            attempt.submission_date and 
            attempt.submission_date > assignment.assignment_deadline
        ) if assignment.assignment_deadline else False
        
        return Response({
            'detail': 'Попытка успешно обновлена',
            'attempt': {
                'id': attempt.id,
                'attempt_number': attempt.attempt_number,
                'submission_date': attempt.submission_date,
                'comment': attempt.comment,
                'status': {
                    'id': attempt.submission_status.id,
                    'name': status_name,
                    'description': self._get_status_description(attempt.submission_status),
                    'can_edit': can_edit,
                    'color': self._get_status_color(attempt.submission_status),
                },
                'is_overdue': is_overdue,
                'files': [
                    {
                        'id': file.id,
                        'file_name': file.file_name,
                        'file_size': file.file_size,
                        'file_url': file.file.url if file.file else None,
                        'uploaded_at': file.uploaded_at,
                        'description': file.description,
                    }
                    for file in attempt_files
                ],
                'feedback': feedback_data,
                'grading_type': assignment.grading_type,
                'max_score': assignment.max_score if assignment.grading_type == 'points' else None,
            }
        })
            

class ListenerTestAPIView_v2(APIView):
    """API для работы с тестами"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, test_id):
        """Получить тест для прохождения"""
        user = request.user
        
        get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        test = get_object_or_404(
            Test,
            id=test_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        previous_attempts = TestResult.objects.filter(
            user=user,
            test=test
        ).count()
        
        if test.max_attempts and previous_attempts >= test.max_attempts:
            return Response(
                {'detail': 'Превышено максимальное количество попыток'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        questions = Question.objects.filter(
            test=test
        ).select_related('answer_type').prefetch_related(
            'choiceoption_set',
            'matchingpair_set'
        ).order_by('question_order')
        
        questions_data = []
        for question in questions:
            choices = question.choiceoption_set.all()
            matching_pairs = question.matchingpair_set.all()
            
            right_options = []
            if matching_pairs.exists():
                right_texts = list(set([pair.right_text for pair in matching_pairs if pair.right_text]))
                right_options = sorted(right_texts) 
            
            question_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_score': question.question_score,
                'question_order': question.question_order,
                'answer_type': question.answer_type.answer_type_name if question.answer_type else 'текст',
                'answer_type_id': question.answer_type.id if question.answer_type else None,
                'correct_text': question.correct_text,
                'choiceoption_set': [
                    {
                        'id': choice.id,
                        'option_text': choice.option_text,
                        'is_correct': choice.is_correct,
                    }
                    for choice in choices
                ],
                'matchingpair_set': [
                    {
                        'id': pair.id,
                        'left_text': pair.left_text,
                        'right_text': pair.right_text,
                    }
                    for pair in matching_pairs
                ],
                'right_options': right_options,  
            }
            
            questions_data.append(question_data)
        
        return Response({
            'test': {
                'id': test.id,
                'test_name': test.test_name,
                'test_description': test.test_description,
                'is_final': test.is_final,
                'max_attempts': test.max_attempts,
                'grading_form': test.grading_form,
                'passing_score': test.passing_score,
            },
            'questions': questions_data,
            'current_attempt': previous_attempts + 1,
            'max_attempts': test.max_attempts
        })
    
    def post(self, request, course_id, test_id):
        """Отправить ответы на тест"""
        user = request.user
        
        user_course = get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        test = get_object_or_404(
            Test,
            id=test_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        previous_attempts = TestResult.objects.filter(
            user=user,
            test=test
        ).count()
        
        attempt_number = previous_attempts + 1
        
        existing_result = TestResult.objects.filter(
            user=user,
            test=test,
            attempt_number=attempt_number
        ).first()
        
        if existing_result:
            return Response(
                {'detail': f'Попытка {attempt_number} уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if test.max_attempts and previous_attempts >= test.max_attempts:
            return Response(
                {'detail': 'Превышено максимальное количество попыток'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        answers_data = request.data.get('answers', [])
        time_spent = request.data.get('time_spent', 0)
        
        if not answers_data:
            return Response(
                {'detail': 'Не переданы ответы на вопросы'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        total_score = 0
        max_score = 0
        
        for answer_data in answers_data:
            question_id = answer_data.get('question_id')
            answer_type = answer_data.get('answer_type')
            
            try:
                question = Question.objects.get(id=question_id, test=test)
            except Question.DoesNotExist:
                continue
            
            max_score += question.question_score if question.question_score else 1
            
            if answer_type == 'text':
                answer_text = answer_data.get('answer_text', '')
                
                if question.correct_text and answer_text.strip().lower() == question.correct_text.strip().lower():
                    score = question.question_score if question.question_score else 1
                    total_score += score
                
            elif answer_type == 'choice':
                selected_ids = answer_data.get('selected_choice_ids', [])
                
                correct_choices = question.choiceoption_set.filter(is_correct=True)
                selected_choices = question.choiceoption_set.filter(id__in=selected_ids, is_correct=True)
                
                if correct_choices.count() > 0:

                    answer_type_name = question.answer_type.answer_type_name if question.answer_type else 'текст'
                    
                    if answer_type_name.lower() in ['один ответ', 'выбор одного', 'single choice']:
                        if len(selected_ids) == 1 and selected_choices.count() == 1:
                            score = question.question_score if question.question_score else 1
                            total_score += score
                    else:
                        if correct_choices.count() == selected_choices.count() == len(selected_ids):
                            score = question.question_score if question.question_score else 1
                            total_score += score
            
            elif answer_type == 'matching':
                matching_data = answer_data.get('matching_data', [])
                
                correct_pairs = question.matchingpair_set.all()
                user_pairs = {(match.get('pair_id'), match.get('selected_right_text', '').strip()) 
                             for match in matching_data}
                
                correct_count = 0
                for pair in correct_pairs:
                    user_pair = (pair.id, pair.right_text.strip())
                    if user_pair in user_pairs:
                        correct_count += 1
                
                if correct_pairs.count() > 0:
                    correct_ratio = correct_count / correct_pairs.count()
                    score = (question.question_score if question.question_score else 1) * correct_ratio
                    total_score += score
        
        final_score = None
        is_passed = None
        
        if test.grading_form == 'points':
            final_score = total_score
            
        elif test.grading_form == 'pass_fail':
            if test.passing_score:
                if test.passing_score > 1:  
                    percentage = (total_score / max_score * 100) if max_score > 0 else 0
                    is_passed = percentage >= test.passing_score
                else:  
                    is_passed = (total_score / max_score) >= test.passing_score if max_score > 0 else False
            else:
                is_passed = (total_score / max_score * 100) >= 50 if max_score > 0 else False
        
        try:
            test_result = TestResult.objects.create(
                user=user,
                test=test,
                time_spent=time_spent,
                attempt_number=attempt_number,
                final_score=final_score,
                is_passed=is_passed,
            )
            
        except ValidationError as e:
            error_details = {}
            for field, errors in e.message_dict.items():
                error_details[field] = errors
            
            return Response(
                {
                    'detail': 'Ошибка при сохранении результата теста',
                    'errors': error_details
                },
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            return Response(
                {'detail': f'Ошибка при сохранении результата: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        for answer_data in answers_data:
            question_id = answer_data.get('question_id')
            answer_type = answer_data.get('answer_type')
            
            try:
                question = Question.objects.get(id=question_id, test=test)
            except Question.DoesNotExist:
                continue
            
            user_answer = UserAnswer.objects.create(
                user=user,
                question=question,
                attempt_number=attempt_number,
                answer_date=timezone.now(),
            )
            
            if answer_type == 'text':
                answer_text = answer_data.get('answer_text', '')
                user_answer.answer_text = answer_text
                
                if question.correct_text:
                    if answer_text.strip().lower() == question.correct_text.strip().lower():
                        user_answer.score = question.question_score if question.question_score else 1
                    else:
                        user_answer.score = 0
                
                user_answer.save()
                
            elif answer_type == 'choice':
                selected_ids = answer_data.get('selected_choice_ids', [])
                
                for choice_id in selected_ids:
                    try:
                        choice = ChoiceOption.objects.get(id=choice_id, question=question)
                        UserSelectedChoice.objects.create(
                            user_answer=user_answer,
                            choice_option=choice
                        )
                    except ChoiceOption.DoesNotExist:
                        continue
                
                correct_choices = question.choiceoption_set.filter(is_correct=True)
                selected_choices = question.choiceoption_set.filter(id__in=selected_ids, is_correct=True)
                
                if correct_choices.count() > 0:
                    answer_type_name = question.answer_type.answer_type_name if question.answer_type else 'текст'
                    
                    if answer_type_name.lower() in ['один ответ', 'выбор одного', 'single choice']:
                        if len(selected_ids) == 1 and selected_choices.count() == 1:
                            user_answer.score = question.question_score if question.question_score else 1
                        else:
                            user_answer.score = 0
                    else:
                        if correct_choices.count() == selected_choices.count() == len(selected_ids):
                            user_answer.score = question.question_score if question.question_score else 1
                        else:
                            user_answer.score = 0
                
                user_answer.save()
            
            elif answer_type == 'matching':
                matching_data = answer_data.get('matching_data', [])
                
                for match in matching_data:
                    pair_id = match.get('pair_id')
                    selected_right = match.get('selected_right_text', '')
                    
                    try:
                        pair = MatchingPair.objects.get(id=pair_id, question=question)
                        UserMatchingAnswer.objects.create(
                            user_answer=user_answer,
                            matching_pair=pair,
                            user_selected_right_text=selected_right
                        )
                    except MatchingPair.DoesNotExist:
                        continue
                
                correct_pairs = question.matchingpair_set.all()
                user_pairs = {(match.get('pair_id'), match.get('selected_right_text', '').strip()) 
                             for match in matching_data}
                
                correct_count = 0
                for pair in correct_pairs:
                    user_pair = (pair.id, pair.right_text.strip())
                    if user_pair in user_pairs:
                        correct_count += 1
                
                if correct_pairs.count() > 0:
                    correct_ratio = correct_count / correct_pairs.count()
                    user_answer.score = int((question.question_score if question.question_score else 1) * correct_ratio)
                else:
                    user_answer.score = 0
                
                user_answer.save()
        
        if test.is_final:
            if test.grading_form == 'pass_fail':
                passed = test_result.is_passed
            else:
                if test.passing_score:
                    passed = total_score >= test.passing_score
                else:
                    passed = total_score >= max_score
                
            if passed:
                user_course.status_course = True
                user_course.completion_date = timezone.now()
                user_course.save()
                
                try:
                    certificate = Certificate.objects.create(
                        user_course=user_course,
                        certificate_number=f'CERT-{user_course.id}-{int(timezone.now().timestamp())}',
                        issue_date=timezone.now().date()
                    )
                except Exception as e:
                    print(f"Ошибка создания сертификата: {e}")
        
        response_data = {
            'test_result_id': test_result.id,
            'total_score': total_score,
            'max_score': max_score,
            'time_spent': time_spent,
            'attempt_number': attempt_number,
            'max_attempts': test.max_attempts,
            'grading_form': test.grading_form,
        }
        
        if test.grading_form == 'points':
            response_data['final_score'] = final_score
            response_data['percentage'] = (total_score / max_score * 100) if max_score > 0 else 0
            if test.passing_score:
                response_data['is_passed'] = total_score >= test.passing_score
            else:
                response_data['is_passed'] = total_score >= max_score
        elif test.grading_form == 'pass_fail':
            response_data['is_passed'] = test_result.is_passed
            response_data['percentage'] = (total_score / max_score * 100) if max_score > 0 else 0
        
        response_data['passed_final_test'] = test.is_final and (
            test_result.is_passed if test.grading_form == 'pass_fail' else 
            (total_score >= test.passing_score if test.passing_score else total_score >= max_score)
        )
        
        return Response(response_data)


class TestResultDetailView(APIView):
    """API для получения деталей результата теста с отметками правильности"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, test_result_id):
        """Получить детали результата теста с отметками правильности ответов"""
        user = request.user
        
        test_result = get_object_or_404(
            TestResult,
            id=test_result_id,
            user=user
        )
        
        user_answers = UserAnswer.objects.filter(
            user=user,
            attempt_number=test_result.attempt_number,
            question__test=test_result.test
        ).select_related('question__answer_type')
        
        questions_data = []
        
        for user_answer in user_answers:
            question = user_answer.question
            
            question_data = {
                'id': question.id,
                'question_text': question.question_text,
                'question_score': question.question_score,
                'answer_type': question.answer_type.answer_type_name if question.answer_type else 'текст',
                'user_answer': {},
                'is_correct': user_answer.score == question.question_score if question.question_score else user_answer.score > 0,
                'user_score': user_answer.score,
                'max_score': question.question_score if question.question_score else 1
            }
            
            if question_data['answer_type'].lower() in ['текст', 'text']:
                question_data['user_answer'] = {
                    'type': 'text',
                    'answer_text': user_answer.answer_text or '',
                    'correct_answer': question.correct_text if user_answer.score == question.question_score else None,
                    'is_correct': user_answer.score == question.question_score
                }
            
            elif question_data['answer_type'].lower() in ['один ответ', 'несколько ответов', 'single choice', 'multiple choice']:
                selected_choices = UserSelectedChoice.objects.filter(
                    user_answer=user_answer
                ).select_related('choice_option')
                
                selected_ids = [sc.choice_option.id for sc in selected_choices]
                
                all_choices = ChoiceOption.objects.filter(question=question)
                
                choices_data = []
                for choice in all_choices:
                    is_selected = choice.id in selected_ids
                    choices_data.append({
                        'id': choice.id,
                        'option_text': choice.option_text,
                        'is_correct': choice.is_correct,
                        'is_selected': is_selected,
                        'is_user_correct': is_selected == choice.is_correct
                    })
                
                question_data['user_answer'] = {
                    'type': 'choice',
                    'choices': choices_data,
                    'selected_ids': selected_ids
                }
            
            elif question_data['answer_type'].lower() in ['сопоставление', 'matching']:
                user_matchings = UserMatchingAnswer.objects.filter(
                    user_answer=user_answer
                ).select_related('matching_pair')

                all_pairs = MatchingPair.objects.filter(question=question)
                
                pairs_data = []
                for pair in all_pairs:
                    user_matching = next((um for um in user_matchings if um.matching_pair_id == pair.id), None)
                    
                    user_selected = user_matching.user_selected_right_text if user_matching else ''
                    is_correct = (user_selected.strip() == pair.right_text.strip()) if user_matching else False
                    
                    pairs_data.append({
                        'id': pair.id,
                        'left_text': pair.left_text,
                        'correct_right_text': pair.right_text if is_correct else None,
                        'user_selected_right_text': user_selected,
                        'is_correct': is_correct
                    })
                
                question_data['user_answer'] = {
                    'type': 'matching',
                    'pairs': pairs_data
                }
            
            questions_data.append(question_data)

        from django.utils import timezone        
        completion_date = test_result.completion_date
        if completion_date:
            local_date = timezone.localtime(completion_date)
            formatted_date = local_date.strftime('%Y-%m-%d %H:%M:%S')
            iso_date = local_date.isoformat()
        else:
            formatted_date = None
            iso_date = None
        
        return Response({
            'test_result': {
                'id': test_result.id,
                'test_id': test_result.test.id,
                'test_name': test_result.test.test_name,
                'attempt_number': test_result.attempt_number,
                'total_score': test_result.final_score if test_result.final_score else 0,
                'max_score': sum(q['max_score'] for q in questions_data) if questions_data else 0,
                'is_passed': test_result.is_passed,
                'completion_date': formatted_date, 
                'completion_date_iso': iso_date,   
                'time_spent': test_result.time_spent,
            },
            'questions': questions_data
        })

class UserTestAttemptsView(APIView):
    """API для получения всех попыток пользователя по тесту"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id, test_id):
        """Получить все попытки пользователя по тесту"""
        user = request.user
        
        get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        test = get_object_or_404(
            Test,
            id=test_id,
            lecture__course_id=course_id,
            is_active=True
        )
        
        attempts = TestResult.objects.filter(
            user=user,
            test=test
        ).order_by('-attempt_number')
        
        attempts_data = []
        for attempt in attempts:
            user_answers = UserAnswer.objects.filter(
                user=user,
                attempt_number=attempt.attempt_number,
                question__test=test
            )
            
            total_questions = user_answers.count()
            correct_answers = user_answers.filter(score__gt=0).count()
            
            percentage = 0
            if total_questions > 0:
                percentage = (correct_answers / total_questions) * 100
            
            attempts_data.append({
                'id': attempt.id,
                'attempt_number': attempt.attempt_number,
                'total_score': attempt.final_score if attempt.final_score else 0,
                'is_passed': attempt.is_passed,
                'completion_date': attempt.completion_date,
                'time_spent': attempt.time_spent,
                'correct_answers': correct_answers,
                'total_questions': total_questions,
                'percentage': round(percentage, 1)
            })
        
        return Response({
            'test': {
                'id': test.id,
                'name': test.test_name,
                'max_attempts': test.max_attempts
            },
            'attempts': attempts_data
        })


class ListenerResultsView(APIView):
    """API для результатов и сертификатов"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        """Получить результаты и сертификаты"""
        user = request.user
        
        user_courses = UserCourse.objects.filter(
            user=user,
            is_active=True
        ).select_related('course')
        
        total_courses = user_courses.count()
        completed_courses = user_courses.filter(status_course=True).count()
        completion_rate = (completed_courses / total_courses * 100) if total_courses > 0 else 0
        
        from unireax_main.utils.course_progress import check_course_completion        
        assignments_total = 0
        assignments_completed = 0
        tests_total = 0
        tests_passed = 0
        
        for user_course in user_courses:
            progress_data = check_course_completion(user.id, user_course.course.id)
            assignments_total += progress_data['details']['assignments']['total']
            assignments_completed += progress_data['details']['assignments']['completed']
            tests_total += progress_data['details']['tests']['total']
            tests_passed += progress_data['details']['tests']['passed']
        
        certificates = Certificate.objects.filter(
            user_course__user=user
        ).select_related('user_course__course').order_by('-issue_date')
        
        certificates_count = certificates.count()
        
        response_data = {
            'statistics': {
                'total_courses': total_courses,
                'completed_courses': completed_courses,
                'completion_rate': round(completion_rate, 1),
                'certificates_count': certificates_count,
                'assignments': {
                    'total': assignments_total,
                    'completed': assignments_completed,
                    'percentage': (assignments_completed / assignments_total * 100) if assignments_total > 0 else 0
                },
                'tests': {
                    'total': tests_total,
                    'passed': tests_passed,
                    'percentage': (tests_passed / tests_total * 100) if tests_total > 0 else 0
                }
            },
            'certificates': [
                {
                    'certificate': {
                        'id': cert.id,
                        'certificate_number': cert.certificate_number,
                        'issue_date': cert.issue_date,
                        'certificate_file_path': cert.certificate_file_path,
                    },
                    'course': {
                        'id': cert.user_course.course.id,
                        'course_name': cert.user_course.course.course_name,
                        'course_hours': cert.user_course.course.course_hours,
                        'has_certificate': cert.user_course.course.has_certificate,
                        'category_details': {
                            'course_category_name': cert.user_course.course.course_category.course_category_name 
                            if cert.user_course.course.course_category else None
                        }
                    },
                    'issue_date': cert.issue_date
                }
                for cert in certificates
            ]
        }
        
        return Response(response_data)

class PasswordResetRequestView(APIView):
    """Запрос на восстановление пароля"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            
            try:
                user = User.objects.get(email=email)
                
                code = PasswordResetCode.generate_code()
                
                PasswordResetCode.objects.filter(
                    user=user,
                    is_used=False
                ).delete()
                
                reset_code = PasswordResetCode.objects.create(
                    user=user,
                    code=code
                )
                
                self._send_reset_email(user, code)
                
                return Response({
                    "detail": "Код восстановления отправлен на email",
                    "email": email
                }, status=status.HTTP_200_OK)
                
            except User.DoesNotExist:
                return Response({
                    "detail": "Если email зарегистрирован, код будет отправлен"
                }, status=status.HTTP_200_OK)
            except Exception:
                return Response({
                    "detail": "Ошибка при обработке запроса"
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_reset_email(self, user, code):
        """Отправка email с кодом восстановления"""
        subject = 'Код восстановления пароля - UNIREAX'
        
        plain_message = f"""Восстановление пароля - UNIREAX

Здравствуйте, {user.first_name or user.username}!

Вы запросили восстановление пароля для аккаунта {user.email}.

Ваш код восстановления: {code}

Введите этот 6-значный код в приложении для сброса пароля.

Код действителен в течение 15 минут.

Если вы не запрашивали восстановление пароля, проигнорируйте это письмо.

С уважением,
Команда UNIREAX
"""
        
        html_message = render_to_string('emails/password_reset.html', {
            'user': user,
            'code': code,
            'protocol': 'http',
            'domain': 'localhost:8000',
        })
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

class PasswordResetVerifyView(APIView):
    """Верификация кода восстановления"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetVerifySerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            reset_code = serializer.validated_data['reset_code']
            
            return Response({
                "detail": "Код подтвержден",
                "email": user.email,
                "code": reset_code.code,
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    """Подтверждение сброса пароля"""
    permission_classes = [AllowAny]
    
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            reset_code = serializer.validated_data['reset_code']
            new_password = serializer.validated_data['new_password']
            
            user.set_password(new_password)
            user.save()
            
            reset_code.mark_code_used()
            
            PasswordResetCode.objects.filter(
                user=user,
                is_used=False
            ).exclude(id=reset_code.id).delete()
            
            self._send_success_email(user)
            
            return Response({
                "detail": "Пароль успешно изменен"
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _send_success_email(self, user):
        """Отправка email об успешной смене пароля"""
        subject = 'Пароль успешно изменен - UNIREAX'
        
        plain_message = f"""Пароль успешно изменен - UNIREAX

Здравствуйте, {user.first_name or user.username}!

Пароль для вашего аккаунта {user.email} был успешно изменен.

Важная информация:
• Все активные сессии на других устройствах были завершены
• Для входа в аккаунт используйте новый пароль
• Рекомендуем не использовать этот пароль на других сайтах

Если вы не меняли пароль, немедленно свяжитесь с поддержкой по адресу unireax@mail.ru

С уважением,
Команда UNIREAX
"""
        
        html_message = render_to_string('emails/password_reset_success.html', {
            'user': user,
            'protocol': 'http',
            'domain': 'localhost:8000',
        })
        
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_message,
            fail_silently=False,
        )

class CertificateEligibilityView(APIView):
    """API для проверки возможности получения сертификата"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, course_id):
        user = request.user
        
        try:
            user_course = UserCourse.objects.get(
                user=user,
                course_id=course_id,
                is_active=True
            )
        except UserCourse.DoesNotExist:
            return Response({
                'eligible': False,
                'error': 'Вы не записаны на этот курс'
            })
        
        from unireax_main.utils.course_progress import check_course_completion
        completion_data = check_course_completion(user.id, course_id)        
        existing_certificate = Certificate.objects.filter(user_course=user_course).first()
        has_certificate = existing_certificate is not None
        
        eligible = (
            completion_data['completed'] and
            user_course.course.has_certificate and
            user_course.course.is_completed and
            not has_certificate
        )
        
        error_message = None
        if not eligible:
            if not completion_data['completed']:
                error_message = f'Для получения сертификата необходимо выполнить все задания и тесты курса (текущий прогресс: {completion_data["progress"]}%)'
            elif not user_course.course.has_certificate:
                error_message = 'Для этого курса не предусмотрены сертификаты'
            elif not user_course.course.is_completed:
                error_message = 'Сертификат будет доступен после окончательного завершения курса и прекращения добавления новых материалов'
            elif has_certificate:
                error_message = 'Сертификат уже получен'
            else:
                error_message = 'Неизвестная ошибка'
        
        return Response({
            'eligible': eligible,
            'progress': completion_data['progress'],
            'progress_details': completion_data['details'],
            'has_certificate': has_certificate,
            'certificate_id': existing_certificate.id if existing_certificate else None,
            'certificate_number': existing_certificate.certificate_number if existing_certificate else None,
            'issue_date': existing_certificate.issue_date if existing_certificate else None,
            'course_has_certificate': user_course.course.has_certificate,
            'course_completed': user_course.status_course,
            'course_is_completed': user_course.course.is_completed,
            'error': error_message
        })


class CertificateIssueView(APIView):
    """API для принудительной выдачи сертификата"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, course_id):
        user = request.user
        
        user_course = get_object_or_404(
            UserCourse,
            user=user,
            course_id=course_id,
            is_active=True
        )
        
        from unireax_main.utils.course_progress import check_course_completion
        completion_data = check_course_completion(user.id, course_id)
        
        if not completion_data['completed']:
            return Response({
                'detail': f'Для получения сертификата необходимо выполнить все задания и тесты курса (текущий прогресс: {completion_data["progress"]}%)',
                'progress': completion_data['progress'],
                'progress_details': completion_data['details']
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user_course.course.has_certificate:
            return Response({
                'detail': 'Курс не предусматривает выдачу сертификатов'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        if not user_course.course.is_completed:
            return Response({
                'detail': 'Сертификат будет доступен после окончательного завершения курса и прекращения добавления новых материалов'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        existing = Certificate.objects.filter(user_course=user_course).first()
        if existing:
            return Response({
                'detail': 'Сертификат уже выдан',
                'certificate_id': existing.id,
                'certificate_number': existing.certificate_number,
                'issue_date': existing.issue_date
            })
        
        try:
            certificate = Certificate.objects.create(
                user_course=user_course,
                issue_date=timezone.now().date()
            )
            
            from unireax_main.utils.certificate_generator import generate_certificate_pdf
            pdf_path = generate_certificate_pdf(certificate)
            certificate.certificate_file_path = pdf_path
            certificate.save()
            
            if not user_course.status_course:
                user_course.status_course = True
                user_course.completion_date = timezone.now()
                user_course.save()     

            serializer = CertificateSerializer(certificate)
            return Response({
                'detail': 'Сертификат успешно выдан',
                'certificate': serializer.data,
                'pdf_url': request.build_absolute_uri(settings.MEDIA_URL + pdf_path)
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            logger.error(f"Ошибка выдачи сертификата: {e}")
            return Response({
                'detail': f'Ошибка при выдаче сертификата: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class CertificateDownloadView(APIView):
    """Скачивание сертификата"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request, certificate_id):
        certificate = get_object_or_404(
            Certificate,
            id=certificate_id,
            user_course__user=request.user
        )
        
        if not certificate.certificate_file_path:
            from unireax_main.utils.certificate_generator import generate_certificate_pdf
            pdf_path = generate_certificate_pdf(certificate)
            certificate.certificate_file_path = pdf_path
            certificate.save()
        
        file_path = os.path.join(settings.MEDIA_ROOT, certificate.certificate_file_path)
        
        if not os.path.exists(file_path):
            return Response({
                'detail': 'Файл сертификата не найден'
            }, status=status.HTTP_404_NOT_FOUND)
        
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_number}.pdf"'
            return response


class CertificateListView(APIView):
    """Список сертификатов пользователя"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        certificates = Certificate.objects.filter(
            user_course__user=request.user
        ).select_related('user_course__course').order_by('-issue_date')
        serializer = CertificateSerializer(certificates, many=True)
        return Response({
            'count': certificates.count(),
            'certificates': serializer.data
        })
    
class CourseMaterialsView(APIView):
    """Публичный просмотр материалов курса (без проверки записи)"""
    permission_classes = [AllowAny]
    
    def get(self, request, course_id):
        try:
            try:
                course = Course.objects.get(id=course_id, is_active=True)
            except Course.DoesNotExist:
                return Response(
                    {'detail': 'Курс не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            lectures = Lecture.objects.filter(
                course=course,
                is_active=True
            ).order_by('lecture_order').values('id', 'lecture_name', 'lecture_order')
            
            assignments = PracticalAssignment.objects.filter(
                lecture__course=course,
                is_active=True
            ).select_related('lecture').values(
                'id', 
                'practical_assignment_name',
                'practical_assignment_description',
                'lecture_id'
            )
            
            tests = Test.objects.filter(
                lecture__course=course,
                is_active=True
            ).select_related('lecture').values(
                'id',
                'test_name',
                'test_description',
                'lecture_id'
            )
            
            materials_by_lecture = []
            for lecture in lectures:
                lecture_assignments = [
                    {
                        'id': a['id'],
                        'name': a['practical_assignment_name'],
                        'description': a['practical_assignment_description'],
                    }
                    for a in assignments if a['lecture_id'] == lecture['id']
                ]
                
                lecture_tests = [
                    {
                        'id': t['id'],
                        'name': t['test_name'],
                        'description': t['test_description'],
                    }
                    for t in tests if t['lecture_id'] == lecture['id']
                ]
                
                materials_by_lecture.append({
                    'lecture': {
                        'id': lecture['id'],
                        'name': lecture['lecture_name'],
                        'order': lecture['lecture_order'],
                    },
                    'assignments': lecture_assignments,
                    'tests': lecture_tests
                })
            
            return Response({
                'course': {
                    'id': course.id,
                    'name': course.course_name,
                    'description': course.course_description,
                    'has_certificate': course.has_certificate,
                    'hours': course.course_hours,
                    'price': str(course.course_price) if course.course_price else '0',
                },
                'materials_by_lecture': materials_by_lecture,
                'total_lectures': len(lectures),
                'total_assignments': len(assignments),
                'total_tests': len(tests),
            })
            
        except Exception as e:
            print(traceback.format_exc())
            return Response(
                {'detail': f'Внутренняя ошибка сервера: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
@permission_classes([AllowAny])
def api_check_login_status(request):
    """
    Проверка статуса блокировки для username
    """
    username = request.query_params.get('username')
    if not username:
        return Response({
            'blocked': False,
            'remaining_attempts': MAX_ATTEMPTS,
            'minutes_left': 0,
            'seconds_left': 0,
            'max_attempts': MAX_ATTEMPTS
        }, status=status.HTTP_200_OK)
    
    is_blocked, remaining_attempts, seconds_left = check_rate_limit_by_username(username)
    
    return Response({
        'blocked': is_blocked,
        'remaining_attempts': remaining_attempts,
        'minutes_left': (seconds_left + 59) // 60 if is_blocked else 0,
        'seconds_left': seconds_left if is_blocked else 0,
        'max_attempts': MAX_ATTEMPTS
    }, status=status.HTTP_200_OK)

# 27. избранные курсы
class FavoriteCourseViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с избранными курсами"""
    serializer_class = FavoriteCourseSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        return FavoriteCourse.objects.filter(user=self.request.user).select_related('course')
    
    @action(detail=False, methods=['get'], url_path='list')
    def favorite_list(self, request):
        """Получить список избранных курсов с дополнительной информацией"""
        favorites = self.get_queryset().order_by('-added_at')
        
        result = []
        for fav in favorites:
            item = {
                'id': fav.course.id,
                'course_name': fav.course.course_name,
                'course_description': fav.course.course_description,
                'course_price': str(fav.course.course_price) if fav.course.course_price else '0',
                'course_photo_path': fav.course.course_photo_path.url if fav.course.course_photo_path else None,
                'course_hours': fav.course.course_hours,
                'has_certificate': fav.course.has_certificate,
                'avg_rating': self._get_course_rating(fav.course),
                'student_count': self._get_student_count(fav.course),
                'category_name': fav.course.course_category.course_category_name if fav.course.course_category else None,
                'added_at': fav.added_at,
                'is_free': fav.course.course_price is None or fav.course.course_price == 0,
            }
            result.append(item)
        
        return Response({
            'count': len(result),
            'results': result
        })
    
    @action(detail=False, methods=['post'], url_path='toggle')
    def toggle_favorite(self, request):
        """Переключить статус избранного для курса"""
        course_id = request.data.get('course_id')
        if not course_id:
            return Response(
                {'detail': 'Не указан ID курса'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            course = Course.objects.get(id=course_id, is_active=True)
        except Course.DoesNotExist:
            return Response(
                {'detail': 'Курс не найден'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        favorite = FavoriteCourse.objects.filter(
            user=request.user,
            course=course
        ).first()
        
        if favorite:
            favorite.delete()
            is_favorited = False
            message = f'Курс "{course.course_name}" удалён из избранного'
        else:
            FavoriteCourse.objects.create(user=request.user, course=course)
            is_favorited = True
            message = f'Курс "{course.course_name}" добавлен в избранное'
        
        return Response({
            'success': True,
            'is_favorited': is_favorited,
            'message': message,
            'course_id': course_id
        })
    
    @action(detail=False, methods=['get'], url_path='check')
    def check_favorite(self, request):
        """Проверить, добавлен ли курс в избранное"""
        course_id = request.query_params.get('course_id')
        if not course_id:
            return Response(
                {'detail': 'Не указан ID курса'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_favorited = FavoriteCourse.objects.filter(
            user=request.user,
            course_id=course_id
        ).exists()
        
        return Response({
            'course_id': int(course_id),
            'is_favorited': is_favorited
        })
    
    @action(detail=False, methods=['get'], url_path='count')
    def favorite_count(self, request):
        """Получить количество избранных курсов"""
        count = self.get_queryset().count()
        return Response({'count': count})
    
    def _get_course_rating(self, course):
        from django.db.models import Avg, Q
        rating = course.review_set.filter(is_approved=True).aggregate(
            avg=Avg('rating')
        )['avg']
        return float(rating) if rating else 0.0
    
    def _get_student_count(self, course):
        return course.usercourse_set.filter(is_active=True).count()


class DeactivateAccountView(APIView):
    """
    Деактивация аккаунта пользователя (установка is_active=False)
    Мягкое удаление - все связанные записи деактивируются, но не удаляются
    """
    permission_classes = [IsAuthenticated]
    
    @transaction.atomic
    def post(self, request):
        serializer = DeactivateAccountSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(
                {'errors': serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user = request.user
        
        if not user.is_active:
            return Response(
                {'detail': 'Аккаунт уже деактивирован'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            UserCourse.objects.filter(user=user, is_active=True).update(
                is_active=False,
                status_course=False
            )

            FavoriteCourse.objects.filter(user=user).delete()
            
            UserPracticalAssignment.objects.filter(user=user).update(
                submission_status=AssignmentStatus.objects.get(assignment_status_name='отклонено')
            )
            
            Review.objects.filter(user=user).update(
                comment_review="[Аккаунт удалён]",
                is_approved=False
            )
            
            user.first_name = f"Deleted"
            user.last_name = f"User"
            user.patronymic = None
            
            user.username = f"deleted_{user.id}_{int(timezone.now().timestamp())}"
            
            user.email = f"deleted_{user.id}@deleted.unireax"
            
            user.position = None
            user.educational_institution = None
            
            if user.certificate_file:
                try:
                    user.certificate_file.delete(save=False)
                except:
                    pass
                user.certificate_file = None
            
            user.is_active = False
            
            user.save(update_fields=['first_name', 'last_name', 'patronymic', 'username', 
                                      'email', 'position', 'educational_institution', 
                                      'certificate_file', 'is_active'])
            
            try:
                subject = 'Аккаунт деактивирован - UNIREAX'
                message = f"""
Здравствуйте!

Ваш аккаунт на платформе UNIREAX был деактивирован.

Что произошло:
- Все ваши персональные данные были анонимизированы
- Все активные записи на курсы отменены
- Избранные курсы удалены
- Отзывы обезличены

Вы больше не сможете войти в аккаунт.

Если вы хотите восстановить доступ, пожалуйста, свяжитесь с поддержкой: unireax@mail.ru

С уважением,
Команда UNIREAX
"""
                send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=True,
                )
            except Exception as e:
                print(f"Ошибка отправки письма: {e}")

            logout(request)
            
            return Response({
                'success': True,
                'detail': 'Ваш аккаунт успешно деактивирован. Все ваши данные были анонимизированы.',
                'redirect': '/auth'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Ошибка деактивации аккаунта: {e}")
            return Response(
                {'detail': f'Ошибка при деактивации аккаунта: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class GetDeactivateInfoView(APIView):
    """Получить информацию о деактивации аккаунта"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        active_courses = UserCourse.objects.filter(user=user, is_active=True).count()
        favorites_count = FavoriteCourse.objects.filter(user=user).count()
        reviews_count = Review.objects.filter(user=user).count()
        assignments_count = UserPracticalAssignment.objects.filter(user=user).count()
        test_results_count = TestResult.objects.filter(user=user).count()
        
        return Response({
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'active_courses_count': active_courses,
            'favorites_count': favorites_count,
            'reviews_count': reviews_count,
            'assignments_count': assignments_count,
            'test_results_count': test_results_count,
            'has_certificate': bool(user.certificate_file),
            'warning': 'Все ваши данные будут анонимизированы или деактивированы. Это действие нельзя отменить.',
        })


# 29. посты и комментарии курсов
class CoursePostViewSet(viewsets.ModelViewSet):
    """ViewSet для работы с постами курсов"""
    serializer_class = CoursePostSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = PaginationPage
    
    def get_queryset(self):
        user = self.request.user
        course_id = self.request.query_params.get('course')
        
        queryset = CoursePost.objects.filter(is_active=True)
        
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        
        return queryset.select_related('author', 'course').prefetch_related('comments').order_by('-is_pinned', '-created_at')
    
    @action(detail=False, methods=['get'], url_path='by-course/(?P<course_id>[^/.]+)')
    def by_course(self, request, course_id=None):
        """Получить посты курса"""
        user = request.user
        
        course = get_object_or_404(Course, id=course_id)

        has_access = user.is_admin or course.is_user_enrolled(user.id) or CourseTeacher.objects.filter(course=course, teacher=user, is_active=True).exists()
        
        if not has_access:
            return Response(
                {'detail': 'У вас нет доступа к этому курсу'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        posts = CoursePost.objects.filter(course=course, is_active=True).select_related('author').prefetch_related('comments')
        
        page = self.paginate_queryset(posts)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(posts, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'], url_path='create')
    def create_post(self, request):
        """Создать пост в курсе"""
        course_id = request.data.get('course_id')
        course = get_object_or_404(Course, id=course_id)
        
        can_create = request.user.is_admin or CourseTeacher.objects.filter(course=course, teacher=request.user, is_active=True).exists()
        
        if not can_create:
            return Response(
                {'detail': 'У вас нет прав на создание постов в этом курсе'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreatePostSerializer(data=request.data)
        if serializer.is_valid():
            post = CoursePost.objects.create(
                course=course,
                author=request.user,
                title=serializer.validated_data['title'],
                content=serializer.validated_data['content'],
                post_type=serializer.validated_data.get('post_type', 'announcement'),
                is_pinned=serializer.validated_data.get('is_pinned', False)
            )
            
            return Response(CoursePostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], url_path='comment')
    def add_comment(self, request, pk=None):
        """Добавить комментарий к посту"""
        post = self.get_object()
        course = post.course
        
        has_access = request.user.is_admin or course.is_user_enrolled(request.user.id) or CourseTeacher.objects.filter(course=course, teacher=request.user, is_active=True).exists()
        
        if not has_access:
            return Response(
                {'detail': 'У вас нет доступа к этому курсу'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        content = request.data.get('content')
        parent_id = request.data.get('parent')
        
        if not content:
            return Response(
                {'detail': 'Текст комментария обязателен'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        parent = None
        if parent_id:
            try:
                parent = CoursePostComment.objects.get(id=parent_id)
            except CoursePostComment.DoesNotExist:
                return Response(
                    {'detail': f'Комментарий с id={parent_id} не найден'},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        comment = CoursePostComment.objects.create(
            post=post,
            author=request.user,
            parent=parent,
            content=content
        )
        
        return Response(
            CoursePostCommentSerializer(comment, context={'request': request}).data,
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'], url_path='delete-comment/(?P<comment_id>[^/.]+)')
    def delete_comment(self, request, pk=None, comment_id=None):
        """Удалить комментарий"""
        post = self.get_object()
        comment = get_object_or_404(CoursePostComment, id=comment_id, post=post)
        
        can_delete = request.user.is_admin or comment.author == request.user
        
        if not can_delete:
            return Response(
                {'detail': 'У вас нет прав на удаление этого комментария'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        comment.delete()
        
        return Response({'detail': 'Комментарий удалён'})
    
    @action(detail=True, methods=['put', 'patch'], url_path='edit')
    def edit_post(self, request, pk=None):
        """Редактировать пост"""
        post = self.get_object()
        
        can_edit = request.user.is_admin or post.author == request.user
        
        if not can_edit:
            return Response(
                {'detail': 'У вас нет прав на редактирование этого поста'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = CreatePostSerializer(post, data=request.data, partial=True)
        if serializer.is_valid():
            for key, value in serializer.validated_data.items():
                setattr(post, key, value)
            post.save()
            return Response(CoursePostSerializer(post, context={'request': request}).data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['delete'], url_path='delete')
    def delete_post(self, request, pk=None):
        """Удалить пост (мягкое удаление)"""
        post = self.get_object()
        
        can_delete = request.user.is_admin or post.author == request.user
        
        if not can_delete:
            return Response(
                {'detail': 'У вас нет прав на удаление этого поста'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        post.is_active = False
        post.save()
        
        return Response({'detail': 'Пост удалён'})