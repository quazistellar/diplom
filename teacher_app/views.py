import json
from datetime import datetime, timedelta
from urllib.parse import quote

from django.db import models
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.db.models import Count, Avg, Q, Sum, Max
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.db import transaction

import csv
import random
import string
from io import StringIO
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

from unireax_main.models import (
    User, Course, CourseCategory, CourseType, CourseTeacher,
    Lecture, PracticalAssignment, Test, Question, ChoiceOption,
    MatchingPair, AnswerType, UserCourse, UserPracticalAssignment,
    Feedback, AssignmentStatus, TestResult, Review, Role
)
from unireax_main.forms import ProfileInfoForm, ProfilePasswordChangeForm
from .forms import TeacherCourseForm, TeacherGradeForm
from .export_utils import export_statistics_csv, export_statistics_pdf
from .utils import send_account_credentials_email, send_bulk_emails, send_existing_user_added_to_course_email

from methodist_app.forms import (
    LectureForm, PracticalAssignmentForm, TestForm, QuestionForm
)

from unireax_main.utils.email_utils import send_new_teacher_application_notification
from unireax_main.models import Course, TeacherApplication, CourseTeacher


def is_teacher(user):
    """Проверка, является ли пользователь преподавателем"""
    return (user.is_authenticated and 
            user.role and 
            user.role.role_name.lower() == "преподаватель" and
            user.is_verified)


def get_teacher_courses(user):
    """Получает курсы преподавателя с разделением на созданные и ведомые"""

    created_courses = Course.objects.filter(
        created_by=user,
        course_type__course_type_name="классная комната",
        is_active=True
    )

    teaching_courses = Course.objects.filter(
        courseteacher__teacher=user,
        courseteacher__is_active=True,
        is_active=True
    ).exclude(id__in=created_courses.values_list('id', flat=True))
    
    return {
        'created_courses': created_courses,
        'teaching_courses': teaching_courses,
        'all_courses': list(created_courses) + list(teaching_courses)
    }


def can_edit_course(user, course):
    """Проверяет, может ли преподаватель редактировать курс (создатель)"""
    return course.created_by == user and course.course_type.course_type_name == "классная комната"


def can_teach_course(user, course):
    """Проверяет, может ли преподаватель вести курс (быть преподавателем)"""
    return CourseTeacher.objects.filter(course=course, teacher=user, is_active=True).exists()


def calculate_student_progress(student_id, course_id):
    """Расчет прогресса слушателя через SQL функцию"""
    from django.db import connection
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT calculate_course_completion(%s, %s)",
                [student_id, course_id]
            )
            result = cursor.fetchone()
            return float(result[0]) if result and result[0] else 0.0
    except Exception:
        return 0.0


def calculate_course_avg_progress(course_id):
    """Расчет среднего прогресса по курсу (использует метод модели)"""
    course = Course.objects.get(id=course_id)
    return course.get_average_progress()

@login_required
@user_passes_test(is_teacher)
def teacher_deactivate_account(request):
    """Деактивация аккаунта преподавателя"""
    if request.method == 'POST':
        password = request.POST.get('password')
        user = request.user
        
        if not user.check_password(password):
            messages.error(request, 'Неверный пароль')
            return redirect('teacher_app:profile')
        
        try:
            with transaction.atomic():
                Course.objects.filter(created_by=user, is_active=True).update(
                    is_active=False,
                    is_find_teacher=False
                )
                
                CourseTeacher.objects.filter(teacher=user, is_active=True).update(
                    is_active=False
                )
                
                Lecture.objects.filter(course__created_by=user, is_active=True).update(
                    is_active=False
                )
                
                PracticalAssignment.objects.filter(
                    lecture__course__created_by=user, 
                    is_active=True
                ).update(is_active=False)
                
                Test.objects.filter(
                    lecture__course__created_by=user, 
                    is_active=True
                ).update(is_active=False)

                pending_status = AssignmentStatus.objects.get(assignment_status_name='на проверке')
                UserPracticalAssignment.objects.filter(
                    practical_assignment__lecture__course__created_by=user,
                    submission_status=pending_status
                ).update(
                    submission_status=AssignmentStatus.objects.get(assignment_status_name='отклонено')
                )
                
                user.first_name = "Deleted"
                user.last_name = "User"
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
                user.save()
                
                logout(request)
                
                messages.success(request, 'Ваш аккаунт успешно деактивирован')
                return redirect('main_page')
                
        except Exception as e:
            messages.error(request, f'Ошибка при деактивации: {str(e)}')
            return redirect('teacher_app:profile')
    
    return redirect('teacher_app:profile')


@login_required
@user_passes_test(is_teacher)
def teacher_profile(request):
    """Профиль преподавателя"""
    user = request.user
    
    if request.method == 'POST' and 'update_profile' in request.POST:
        form = ProfileInfoForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Личная информация успешно обновлена!')
            return redirect('teacher_app:profile')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{form.fields[field].label}: {error}')
    else:
        form = ProfileInfoForm(instance=user)
    
    password_form = ProfilePasswordChangeForm(user)
    if request.method == 'POST' and 'change_password' in request.POST:
        password_form = ProfilePasswordChangeForm(user, request.POST)
        if password_form.is_valid():
            user = password_form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменен!')
            return redirect('teacher_app:profile')
        else:
            for error in password_form.errors.values():
                messages.error(request, error)
    
    courses_data = get_teacher_courses(user)
    
    total_courses = len(courses_data['all_courses'])
    total_created = len(courses_data['created_courses'])
    total_teaching = len(courses_data['teaching_courses'])
    total_students = UserCourse.objects.filter(
        course__in=courses_data['all_courses'],
        is_active=True
    ).count()
    total_submissions = UserPracticalAssignment.objects.filter(
        practical_assignment__lecture__course__in=courses_data['all_courses']
    ).count()
    pending_reviews = UserPracticalAssignment.objects.filter(
        practical_assignment__lecture__course__in=courses_data['all_courses'],
        submission_status__assignment_status_name='на проверке'
    ).count()
    
    context = {
        'user': user,
        'full_name': user.get_full_name() or user.username,
        'date_joined': user.date_joined.strftime('%d.%m.%Y'),
        'is_verified': user.is_verified,
        'form': form,
        'password_form': password_form,
        'teacher_courses': courses_data['all_courses'],
        'total_courses': total_courses,
        'total_created': total_created,
        'total_teaching': total_teaching,
        'total_students': total_students,
        'total_submissions': total_submissions,
        'pending_reviews': pending_reviews,
    }
    return render(request, 'teacher_profile.html', context)

@login_required
@user_passes_test(is_teacher)
def teacher_dashboard(request):
    """Дашборд преподавателя"""
    courses_data = get_teacher_courses(request.user)
    
    inactive_created_courses = Course.objects.filter(
        created_by=request.user,
        course_type__course_type_name="классная комната",
        is_active=False  
    )
    
    inactive_teaching_courses = Course.objects.filter(
        courseteacher__teacher=request.user,
        courseteacher__is_active=True,
        is_active=False  
    ).exclude(id__in=inactive_created_courses.values_list('id', flat=True))
    
    created_courses_stats = []
    teaching_courses_stats = []
    total_pending = 0
    total_students = 0
    
    for course in courses_data['created_courses']:
        students_count = UserCourse.objects.filter(course=course, is_active=True).count()
        pending_count = UserPracticalAssignment.objects.filter(
            practical_assignment__lecture__course=course,
            submission_status__assignment_status_name='на проверке'
        ).count()
        avg_progress = course.get_average_progress() 
        
        created_courses_stats.append({
            'course': course,
            'students_count': students_count,
            'pending_count': pending_count,
            'avg_progress': avg_progress,
            'can_edit': True,
            'is_active': True, 
        })
        total_students += students_count
        total_pending += pending_count
    
    for course in inactive_created_courses:
        created_courses_stats.append({
            'course': course,
            'students_count': 0,
            'pending_count': 0,
            'avg_progress': 0,
            'can_edit': True,
            'is_active': False, 
        })
    
    for course in courses_data['teaching_courses']:
        students_count = UserCourse.objects.filter(course=course, is_active=True).count()
        pending_count = UserPracticalAssignment.objects.filter(
            practical_assignment__lecture__course=course,
            submission_status__assignment_status_name='на проверке'
        ).count()
        avg_progress = course.get_average_progress()  
        
        teaching_courses_stats.append({
            'course': course,
            'students_count': students_count,
            'pending_count': pending_count,
            'avg_progress': avg_progress,
            'can_edit': False,
            'is_active': True,  
        })
        total_students += students_count
        total_pending += pending_count
    
    for course in inactive_teaching_courses:
        teaching_courses_stats.append({
            'course': course,
            'students_count': 0,
            'pending_count': 0,
            'avg_progress': 0,
            'can_edit': False,
            'is_active': False, 
        })
    
    all_active_courses_ids = list(courses_data['created_courses'].values_list('id', flat=True)) + \
                            list(courses_data['teaching_courses'].values_list('id', flat=True))
    
    pending_submissions = UserPracticalAssignment.objects.filter(
        practical_assignment__lecture__course_id__in=all_active_courses_ids,
        submission_status__assignment_status_name='на проверке'
    ).select_related(
        'user',
        'practical_assignment',
        'practical_assignment__lecture',
        'practical_assignment__lecture__course'
    ).prefetch_related(
        'assignmentsubmissionfile_set'
    ).order_by('submitted_at')[:10]
    
    pending_submissions_count = UserPracticalAssignment.objects.filter(
        practical_assignment__lecture__course_id__in=all_active_courses_ids,
        submission_status__assignment_status_name='на проверке'
    ).count()
    
    context = {
        'created_courses': created_courses_stats,
        'teaching_courses': teaching_courses_stats,
        'total_created_courses': len(created_courses_stats),
        'total_teaching_courses': len(teaching_courses_stats),
        'total_courses': len(created_courses_stats) + len(teaching_courses_stats),
        'total_students': total_students,
        'total_pending': total_pending,
        'pending_submissions': pending_submissions,
        'pending_submissions_count': pending_submissions_count,
    }
    return render(request, 'teacher_dashboard.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_course_create(request):
    """Создание курса (только для преподавателя-создателя)"""
    try:
        classroom_type = CourseType.objects.get(course_type_name="классная комната")
    except CourseType.DoesNotExist:
        messages.error(request, 'Тип курса "Классная комната" не найден в системе')
        return redirect('teacher_app:dashboard')
    
    if request.method == 'POST':
        form = TeacherCourseForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                with transaction.atomic():
                    course = form.save(commit=False)
                    course.course_type = classroom_type
                    course.created_by = request.user
                    course.is_active = True
                    course.save()
                    
                    CourseTeacher.objects.create(
                        course=course,
                        teacher=request.user,
                        start_date=timezone.now().date(),
                        is_active=True
                    )
                    
                    messages.success(request, f'Курс "{course.course_name}" успешно создан!')
                    return redirect('teacher_app:course_detail', course_id=course.id)
                    
            except Exception as e:
                messages.error(request, f'Ошибка при создании курса: {str(e)}')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = TeacherCourseForm()
    
    context = {
        'form': form,
        'categories': CourseCategory.objects.all(),
    }
    return render(request, 'teacher_course_create.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_course_edit(request, course_id):
    """Редактирование курса (только для создателя)"""
    course = get_object_or_404(Course, id=course_id)
    
    if not can_edit_course(request.user, course):
        messages.error(request, 'Только создатель курса может его редактировать')
        return redirect('teacher_app:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        form = TeacherCourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            form.save()
            messages.success(request, f'Курс "{course.course_name}" успешно обновлен!')
            return redirect('teacher_app:course_detail', course_id=course.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = TeacherCourseForm(instance=course)
    
    context = {
        'form': form,
        'course': course,
        'categories': CourseCategory.objects.all(),
    }
    return render(request, 'teacher_course_edit.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_course_delete(request, course_id):
    """Удаление курса"""
    course = get_object_or_404(Course, id=course_id)
    
    if not can_edit_course(request.user, course):
        messages.error(request, 'Только создатель курса может его удалить')
        return redirect('teacher_app:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        course_name = course.course_name
        course.is_active = False
        course.save()
        messages.success(request, f'Курс "{course_name}" успешно деактивирован!')
        return redirect('teacher_app:dashboard')
    
    context = {
        'object_name': course.course_name,
        'cancel_url': reverse('teacher_app:course_detail', kwargs={'course_id': course.id}),
    }
    return render(request, 'teacher_delete_confirm.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_course_detail(request, course_id):
    """Детальная страница курса"""
    course = get_object_or_404(Course, id=course_id)
    
    is_creator = can_edit_course(request.user, course)
    is_teacher_only = can_teach_course(request.user, course)
    
    if not (is_creator or is_teacher_only):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('teacher_app:dashboard')

    students_count = UserCourse.objects.filter(course=course, is_active=True).count()
    avg_progress = course.get_average_progress()
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    
    assignments = PracticalAssignment.objects.filter(
        lecture__course=course, is_active=True
    ).select_related('lecture').order_by('lecture__lecture_order', 'id')
    
    tests = Test.objects.filter(
        lecture__course=course, is_active=True
    ).select_related('lecture').order_by('lecture__lecture_order', 'id')
    
    if not is_creator:
        pending_assignments = UserPracticalAssignment.objects.filter(
            practical_assignment__lecture__course=course,
            submission_status__assignment_status_name='на проверке'
        ).select_related(
            'user', 
            'practical_assignment',
            'practical_assignment__lecture',
            'submission_status'
        ).prefetch_related(
            'assignmentsubmissionfile_set'
        ).order_by('submitted_at')
        
        reviewed_assignments = UserPracticalAssignment.objects.filter(
            practical_assignment__lecture__course=course,
            feedback__isnull=False
        ).select_related(
            'user',
            'practical_assignment',
            'practical_assignment__lecture',
            'submission_status',
            'feedback'
        ).prefetch_related(
            'assignmentsubmissionfile_set'
        ).order_by('-submitted_at')[:50]
        
        pending_count = pending_assignments.count()
    else:
        pending_assignments = []
        reviewed_assignments = []
        pending_count = 0
    
    context = {
        'course': course,
        'students_count': students_count,
        'pending_count': pending_count,
        'avg_progress': avg_progress,
        'lectures': lectures,
        'assignments': assignments,
        'tests': tests,
        'pending_assignments': pending_assignments,
        'reviewed_assignments': reviewed_assignments,
        'can_edit': is_creator,  # Только создатель может добавлять/удалять
        'can_grade': not is_creator,  # Преподаватель может ставить оценки
        'can_edit_assignments': True,  # ВСЕ преподаватели могут редактировать задания!
        'is_teacher_only': is_teacher_only,
    }
    return render(request, 'teacher_course_detail.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_lecture_create(request, course_id):
    """Создание лекции (только для создателя)"""
    course = get_object_or_404(Course, id=course_id)
    
    if not can_edit_course(request.user, course):
        messages.error(request, 'Только создатель курса может добавлять лекции')
        return redirect('teacher_app:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        form = LectureForm(request.POST, request.FILES, course_id=course.id)  # ← передаём course_id
        if form.is_valid():
            lecture = form.save(commit=False)
            lecture.course = course
            lecture.save()
            messages.success(request, f'Лекция "{lecture.lecture_name}" успешно создана!')
            return redirect('teacher_app:course_detail', course_id=course.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = LectureForm(course_id=course.id)  # ← передаём course_id
    
    context = {
        'form': form,
        'course': course,
        'lecture': None,
    }
    return render(request, 'methodist_lecture_form.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_lecture_edit(request, lecture_id):
    """Редактирование лекции (только для создателя)"""
    lecture = get_object_or_404(Lecture, id=lecture_id)
    course = lecture.course
    
    if not can_edit_course(request.user, course):
        messages.error(request, 'Только создатель курса может редактировать лекции')
        return redirect('teacher_app:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        form = LectureForm(request.POST, request.FILES, instance=lecture)  # при редактировании course_id не нужен, т.к. есть instance
        if form.is_valid():
            form.save()
            messages.success(request, f'Лекция "{lecture.lecture_name}" успешно обновлена!')
            return redirect('teacher_app:course_detail', course_id=course.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = LectureForm(instance=lecture)
    
    context = {
        'form': form,
        'course': course,
        'lecture': lecture,
    }
    return render(request, 'methodist_lecture_form.html', context)

@login_required
@user_passes_test(is_teacher)
def teacher_lecture_delete(request, lecture_id):
    """Удаление лекции (только для создателя)"""
    lecture = get_object_or_404(Lecture, id=lecture_id)
    
    if not can_edit_course(request.user, lecture.course):
        messages.error(request, 'Только создатель курса может удалять лекции')
        return redirect('teacher_app:course_detail', course_id=lecture.course.id)
    
    if request.method == 'POST':
        course_id = lecture.course.id
        lecture_name = lecture.lecture_name
        lecture.delete()
        messages.success(request, f'Лекция "{lecture_name}" успешно удалена!')
        return redirect('teacher_app:course_detail', course_id=course_id)
    
    context = {
        'object_name': lecture.lecture_name,
        'cancel_url': reverse('teacher_app:course_detail', kwargs={'course_id': lecture.course.id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_assignment_create(request, course_id):
    """Создание практического задания (только для создателя)"""
    course = get_object_or_404(Course, id=course_id)
    
    if not can_edit_course(request.user, course):
        messages.error(request, 'Только создатель курса может добавлять задания')
        return redirect('teacher_app:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        form = PracticalAssignmentForm(request.POST, request.FILES, course_id=course.id)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.save()
            messages.success(request, f'Задание "{assignment.practical_assignment_name}" успешно создано!')
            return redirect('teacher_app:course_detail', course_id=course.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PracticalAssignmentForm(course_id=course.id)
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    
    context = {
        'form': form,
        'course': course,
        'assignment': None,
        'lectures': lectures,
    }
    return render(request, 'methodist_assignment_form.html', context)

@login_required
@user_passes_test(is_teacher)
def teacher_assignment_edit(request, assignment_id):
    """Редактирование практического задания (для создателя ИЛИ преподавателя, ведущего курс)"""
    assignment = get_object_or_404(PracticalAssignment, id=assignment_id)
    course = assignment.lecture.course
    
    if not (can_edit_course(request.user, course) or can_teach_course(request.user, course)):
        messages.error(request, 'У вас нет прав на редактирование этого задания')
        return redirect('teacher_app:course_detail', course_id=course.id) 
    
    if request.method == 'POST':
        form = PracticalAssignmentForm(request.POST, request.FILES, instance=assignment, course_id=course.id)
        if form.is_valid():
            form.save()
            messages.success(request, f'Задание "{assignment.practical_assignment_name}" успешно обновлено!')
            return redirect('teacher_app:course_detail', course_id=course.id) 
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = PracticalAssignmentForm(instance=assignment, course_id=course.id)
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    
    context = {
        'form': form,
        'assignment': assignment,
        'course': course,
        'lectures': lectures,
    }
    return render(request, 'methodist_assignment_form.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_assignment_delete(request, assignment_id):
    """Удаление практического задания (только для создателя)"""
    assignment = get_object_or_404(PracticalAssignment, id=assignment_id)
    
    if not can_edit_course(request.user, assignment.lecture.course):
        messages.error(request, 'Только создатель курса может удалять задания')
        return redirect('teacher_app:course_detail', course_id=assignment.lecture.course.id)
    
    if request.method == 'POST':
        course_id = assignment.lecture.course.id
        assignment_name = assignment.practical_assignment_name
        assignment.delete()
        messages.success(request, f'Задание "{assignment_name}" успешно удалено!')
        return redirect('teacher_app:course_detail', course_id=course_id)
    
    context = {
        'object_name': assignment.practical_assignment_name,
        'cancel_url': reverse('teacher_app:course_detail', kwargs={'course_id': assignment.lecture.course.id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_test_create(request, course_id):
    """Создание теста (только для создателя)"""
    course = get_object_or_404(Course, id=course_id)
    
    if not can_edit_course(request.user, course):
        messages.error(request, 'Только создатель курса может добавлять тесты')
        return redirect('teacher_app:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        form = TestForm(request.POST, course_id=course.id)
        if form.is_valid():
            test = form.save(commit=False)
            test.save()
            messages.success(request, f'Тест "{test.test_name}" успешно создан!')
            return redirect('teacher_app:test_builder', test_id=test.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = TestForm(course_id=course.id)
    
    lectures = Lecture.objects.filter(course=course, is_active=True)
    
    context = {
        'form': form,
        'course': course,
        'test': None,
        'lectures': lectures,
    }
    return render(request, 'methodist_test_form.html', context)

@login_required
@user_passes_test(is_teacher)
def teacher_test_edit(request, test_id):
    """Редактирование теста (только для создателя курса)"""
    test = get_object_or_404(Test, id=test_id)
    course = test.lecture.course
    
    if not can_edit_course(request.user, course):
        messages.error(request, 'Только создатель курса может редактировать тесты')
        return redirect('teacher_app:course_detail', course_id=course.id)
    
    if request.method == 'POST':
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            form.save()
            messages.success(request, f'Тест "{test.test_name}" успешно обновлен!')
            return redirect('teacher_app:test_builder', test_id=test.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = TestForm(instance=test)
    
    lectures = Lecture.objects.filter(course=course, is_active=True)
    
    context = {
        'form': form,
        'test': test,
        'course': course,
        'lectures': lectures,
    }
    return render(request, 'methodist_test_form.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_test_delete(request, test_id):
    """Удаление теста (только для создателя)"""
    test = get_object_or_404(Test, id=test_id)
    
    if not can_edit_course(request.user, test.lecture.course):
        messages.error(request, 'Только создатель курса может удалять тесты')
        return redirect('teacher_app:course_detail', course_id=test.lecture.course.id)
    
    if request.method == 'POST':
        course_id = test.lecture.course.id
        test_name = test.test_name
        test.delete()
        messages.success(request, f'Тест "{test_name}" успешно удален!')
        return redirect('teacher_app:course_detail', course_id=course_id)
    
    context = {
        'object_name': test.test_name,
        'cancel_url': reverse('teacher_app:course_detail', kwargs={'course_id': test.lecture.course.id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_test_builder(request, test_id):
    """Конструктор теста (только для создателя)"""
    test = get_object_or_404(Test, id=test_id)
    course = test.lecture.course
    
    if not can_edit_course(request.user, course):
        messages.error(request, 'Только создатель курса может редактировать тесты')
        return redirect('teacher_app:course_detail', course_id=course.id)
    
    questions = Question.objects.filter(test=test).order_by('question_order')
    answer_types = AnswerType.objects.all()
    
    max_order = questions.aggregate(max_order=models.Max('question_order'))['max_order'] or 0
    next_order = max_order + 1
    
    if request.method == 'POST':
        question_form = QuestionForm(request.POST, test_id=test.id)
        
        if question_form.is_valid():
            try:
                with transaction.atomic():
                    question = question_form.save(commit=False)
                    question.test = test

                    if question.question_order is None:
                        question.question_order = next_order
                    
                    question.save()
                    
                    answer_type_name = question.answer_type.answer_type_name
                    print(f"[DEBUG] Создание вопроса, тип: {answer_type_name}")
                    
                    if answer_type_name in ['один ответ', 'несколько ответов']:
                        option_texts = request.POST.getlist('option_text[]')
                        is_correct_list = request.POST.getlist('is_correct[]')
                        
                        for i, text in enumerate(option_texts):
                            if text.strip():
                                is_correct = False
                                if answer_type_name == 'один ответ':
                                    if len(is_correct_list) > 0 and str(i) == is_correct_list[0]:
                                        is_correct = True
                                else:  
                                    is_correct = str(i) in is_correct_list
                                
                                ChoiceOption.objects.create(
                                    question=question,
                                    option_text=text.strip(),
                                    is_correct=is_correct
                                )
                    
                    elif answer_type_name == 'сопоставление':
                        left_texts = request.POST.getlist('left_text[]')
                        right_texts = request.POST.getlist('right_text[]')
                        
                        for left, right in zip(left_texts, right_texts):
                            if left.strip() and right.strip():
                                MatchingPair.objects.create(
                                    question=question,
                                    left_text=left.strip(),
                                    right_text=right.strip()
                                )
                    
                    messages.success(request, 'Вопрос успешно добавлен!')
                    return redirect('teacher_app:test_builder', test_id=test.id)
                    
            except ValidationError as e:
                for field, errors in e.message_dict.items():
                    for error in errors:
                        messages.error(request, error)
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении вопроса: {str(e)}')
        else:
            for field, errors in question_form.errors.items():
                for error in errors:
                    if field == '__all__':
                        messages.error(request, error)
                    else:
                        messages.error(request, error)
    else:
        question_form = QuestionForm(test_id=test.id, initial={'question_order': next_order})
    
    context = {
        'test': test,
        'course': course,
        'questions': questions,
        'question_form': question_form,
        'answer_types': answer_types,
        'next_order': next_order,
    }
    return render(request, 'methodist_test_builder.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_question_edit(request, question_id):
    """Редактирование вопроса"""
    question = get_object_or_404(Question, id=question_id)
    test = question.test

    if not can_edit_course(request.user, test.lecture.course):
        messages.error(request, 'Только создатель курса может редактировать вопросы')
        return redirect('teacher_app:course_detail', course_id=test.lecture.course.id)

    answer_type_name = question.answer_type.answer_type_name if question.answer_type else ''

    options = []
    pairs = []

    if answer_type_name in ['один ответ', 'несколько ответов']:
        options = ChoiceOption.objects.filter(question=question)
        for opt in options:
            print(f"  - {opt.option_text} (правильный: {opt.is_correct})")

    elif answer_type_name == 'сопоставление':
        pairs = MatchingPair.objects.filter(question=question)

    if request.method == 'POST':
        
        form = QuestionForm(request.POST, instance=question)

        if form.is_valid():
            question = form.save()
            answer_type_name = question.answer_type.answer_type_name
            print(f"[DEBUG] Вопрос сохранен, тип: {answer_type_name}")

            if answer_type_name in ['один ответ', 'несколько ответов']:
                ChoiceOption.objects.filter(question=question).delete()
                option_texts = request.POST.getlist('option_text[]')

                if answer_type_name == 'один ответ':
                    correct_value = request.POST.get('is_correct')

                    for i, text in enumerate(option_texts):
                        if text and text.strip():
                            is_correct = (str(i) == correct_value)
                            ChoiceOption.objects.create(
                                question=question,
                                option_text=text.strip(),
                                is_correct=is_correct
                            )

                else:  
                    correct_list = request.POST.getlist('is_correct[]')
                    print(f"[DEBUG] Множественный выбор, правильные варианты: {correct_list}")

                    for i, text in enumerate(option_texts):
                        if text and text.strip():
                            is_correct = str(i) in correct_list
                            ChoiceOption.objects.create(
                                question=question,
                                option_text=text.strip(),
                                is_correct=is_correct
                            )

            elif answer_type_name == 'сопоставление':
                MatchingPair.objects.filter(question=question).delete()
                left = request.POST.getlist('left_text[]')
                right = request.POST.getlist('right_text[]')

                for l, r in zip(left, right):
                    if l.strip() and r.strip():
                        MatchingPair.objects.create(
                            question=question,
                            left_text=l.strip(),
                            right_text=r.strip()
                        )
                        print(f"  Создана пара: {l.strip()} -> {r.strip()}")

            messages.success(request, 'Вопрос успешно обновлен!')
            return redirect('teacher_app:test_builder', test_id=test.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = QuestionForm(instance=question)

    context = {
        'form': form,
        'question': question,
        'test': test,
        'answer_type_name': answer_type_name,  # 'один ответ', 'несколько ответов', 'текст', 'сопоставление'
        'options': options,
        'pairs': pairs,
    }
    return render(request, 'methodist_question_edit.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_question_delete(request, question_id):
    """Удаление вопроса (только для создателя)"""
    question = get_object_or_404(Question, id=question_id)
    test = question.test
    
    if not can_edit_course(request.user, test.lecture.course):
        messages.error(request, 'Только создатель курса может удалять вопросы')
        return redirect('teacher_app:course_detail', course_id=test.lecture.course.id)
    
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Вопрос успешно удален!')
        return redirect('teacher_app:test_builder', test_id=test.id)
    
    context = {
        'object_name': question.question_text[:50],
        'cancel_url': reverse('teacher_app:test_builder', kwargs={'test_id': test.id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_choice_option_delete(request, option_id):
    """Удаление варианта ответа (AJAX)"""
    option = get_object_or_404(ChoiceOption, id=option_id)
    test = option.question.test
    
    if not can_edit_course(request.user, test.lecture.course):
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    option.delete()
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_teacher)
def teacher_matching_pair_delete(request, pair_id):
    """Удаление пары соответствия (AJAX)"""
    pair = get_object_or_404(MatchingPair, id=pair_id)
    test = pair.question.test
    
    if not can_edit_course(request.user, test.lecture.course):
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    pair.delete()
    return JsonResponse({'success': True})


def calculate_student_progress(student_id, course_id):
    """Расчет прогресса слушателя через существующие методы"""
    try:
        course = Course.objects.get(id=course_id)
        return course.get_completion(student_id)
    except Exception as e:
        print(f"Ошибка расчета прогресса: {e}")
        return 0.0


@login_required
@user_passes_test(is_teacher)
def teacher_listeners_list(request, course_id):
    """Список всех слушателей курса (активные и неактивные)"""
    course = get_object_or_404(Course, id=course_id)
    
    if not (can_edit_course(request.user, course) or can_teach_course(request.user, course)):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('teacher_app:dashboard')
    
    all_students = UserCourse.objects.filter(
        course=course
    ).select_related('user')
    
    students_data = []
    for student_course in all_students:
        student = student_course.user
        progress = course.get_completion(student.id)
        
        students_data.append({
            'user': student,
            'progress': progress,
            'registered_at': student_course.registration_date,
            'is_active': student_course.is_active,
            'user_course_id': student_course.id,
        })
    
    active_students = [s for s in students_data if s['is_active']]
    inactive_students = [s for s in students_data if not s['is_active']]
    
    context = {
        'course': course,
        'active_students': active_students,
        'inactive_students': inactive_students,
        'active_count': len(active_students),
        'inactive_count': len(inactive_students),
        'total_count': len(students_data),
        'can_edit': can_edit_course(request.user, course),
    }
    return render(request, 'teacher_listeners_list.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_remove_listener_from_course(request, course_id, user_id):
    """Удаление слушателя с курса (установка is_active=False)"""
    course = get_object_or_404(Course, id=course_id)
    
    if not (can_edit_course(request.user, course) or can_teach_course(request.user, course)):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('teacher_app:dashboard')
    
    try:
        user_course = UserCourse.objects.get(course=course, user_id=user_id)
        student_name = f"{user_course.user.last_name} {user_course.user.first_name}"
        
        user_course.is_active = False
        user_course.save()
        
        messages.success(
            request, 
            f'Слушатель "{student_name}" удален с курса "{course.course_name}".'
        )
    except UserCourse.DoesNotExist:
        messages.error(request, 'Слушатель не найден на этом курсе')
    except Exception as e:
        messages.error(request, f'Ошибка при удалении слушателя: {str(e)}')
    
    return redirect('teacher_app:listeners_list', course_id=course_id)

@login_required
@user_passes_test(is_teacher)
def teacher_restore_listener_to_course(request, course_id, user_course_id):
    """Восстановление слушателя на курс (установка is_active=True)"""
    course = get_object_or_404(Course, id=course_id)
    
    if not (can_edit_course(request.user, course) or can_teach_course(request.user, course)):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('teacher_app:dashboard')
    
    try:
        user_course = UserCourse.objects.get(id=user_course_id, course=course)
        student_name = f"{user_course.user.last_name} {user_course.user.first_name}"
        user_course.is_active = True
        user_course.save()
        
        messages.success(
            request, 
            f'Слушатель "{student_name}" восстановлен на курс "{course.course_name}".'
        )
    except UserCourse.DoesNotExist:
        messages.error(request, 'Запись слушателя не найдена')
    except Exception as e:
        messages.error(request, f'Ошибка при восстановлении слушателя: {str(e)}')
    
    return redirect('teacher_app:listeners_list', course_id=course_id)


@login_required
@user_passes_test(is_teacher)
def teacher_listener_progress(request, course_id, student_id):
    """Детальный прогресс слушателя"""
    course = get_object_or_404(Course, id=course_id)
    student = get_object_or_404(User, id=student_id)
    
    if not (can_edit_course(request.user, course) or can_teach_course(request.user, course)):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('teacher_app:dashboard')
    
    if not UserCourse.objects.filter(user=student, course=course, is_active=True).exists():
        messages.error(request, 'Слушатель не записан на этот курс')
        return redirect('teacher_app:listeners_list', course_id=course.id)
    
    progress = course.get_completion(student.id)
    

    submissions = UserPracticalAssignment.objects.filter(
        user=student,
        practical_assignment__lecture__course=course
    ).select_related(
        'practical_assignment',
        'practical_assignment__lecture',
        'submission_status',
        'feedback'
    ).prefetch_related('assignmentsubmissionfile_set').order_by('-submitted_at')
    
    submissions_data = []
    for submission in submissions:
        assignment = submission.practical_assignment
        
        is_passed = None
        if hasattr(submission, 'feedback') and submission.feedback:
            fb = submission.feedback
            if assignment.grading_type == 'points':
                if fb.score is not None:
                    if assignment.passing_score:
                        is_passed = fb.score >= assignment.passing_score
                    elif assignment.max_score:
                        is_passed = fb.score >= (assignment.max_score * 0.5)
            else:
                is_passed = fb.is_passed
        
        submissions_data.append({
            'submission': submission,
            'assignment': assignment,
            'status': {
                'status_name': submission.submission_status.assignment_status_name,
                'attempt_number': submission.attempt_number,
                'score': submission.feedback.score if hasattr(submission, 'feedback') and submission.feedback else None,
                'max_score': assignment.max_score,
                'is_passed': is_passed,
                'feedback_comment': submission.feedback.comment_feedback if hasattr(submission, 'feedback') and submission.feedback else None,
            }
        })
    
    test_results = TestResult.objects.filter(
        user=student,
        test__lecture__course=course
    ).select_related('test', 'test__lecture').order_by('test__id', '-attempt_number')
    
    latest_results = {}
    for result in test_results:
        if result.test.id not in latest_results:
            latest_results[result.test.id] = result
    
    test_results_data = []
    for test_result in latest_results.values():
        test = test_result.test
        
        is_passed = None
        if test.grading_form == 'points':
            if test_result.final_score is not None and test.passing_score is not None:
                is_passed = test_result.final_score >= test.passing_score
        else:
            is_passed = test_result.is_passed
        
        test_results_data.append({
            'test': test,
            'result': {
                'is_passed': is_passed,
                'final_score': test_result.final_score,
                'passing_score': test.passing_score,
                'attempt_number': test_result.attempt_number,
                'completion_date': test_result.completion_date,
                'grading_form': test.grading_form,
            }
        })
    
    context = {
        'course': course,
        'student': student,
        'progress': progress,
        'submissions': submissions_data,
        'test_results': test_results_data,
        'current_time': timezone.now(),
    }
    return render(request, 'teacher_listener_progress.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_grade_assignment(request, submission_id):
    """Оценивание работы слушателя (доступно всем преподавателям курса)"""
    submission = get_object_or_404(UserPracticalAssignment, id=submission_id)
    course = submission.practical_assignment.lecture.course
    
    if not (can_edit_course(request.user, course) or can_teach_course(request.user, course)):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('teacher_app:dashboard')
    
    assignment = submission.practical_assignment

    is_overdue = False
    overdue_text = ""
    if assignment.assignment_deadline and submission.submission_date:
        if submission.submission_date > assignment.assignment_deadline:
            is_overdue = True
            delta = submission.submission_date - assignment.assignment_deadline
            total_minutes = int(delta.total_seconds() / 60)
            
            if total_minutes < 60:
                overdue_text = f"{total_minutes} минут(ы)"
            elif total_minutes < 1440:
                hours = total_minutes // 60
                minutes = total_minutes % 60
                if minutes == 0:
                    overdue_text = f"{hours} час(ов)"
                else:
                    overdue_text = f"{hours} час(ов) {minutes} минут(ы)"
            else:
                days = total_minutes // 1440
                hours = (total_minutes % 1440) // 60
                if hours == 0:
                    if days % 10 == 1 and days != 11:
                        overdue_text = f"{days} день"
                    elif 2 <= days % 10 <= 4 and not (11 <= days % 100 <= 14):
                        overdue_text = f"{days} дня"
                    else:
                        overdue_text = f"{days} дней"
                else:
                    overdue_text = f"{days} дн. {hours} ч."
    
    try:
        feedback = Feedback.objects.get(user_practical_assignment=submission)
    except Feedback.DoesNotExist:
        feedback = None
    
    current_status = submission.submission_status.assignment_status_name
    is_rejected = current_status == 'отклонено'
    
    if request.method == 'POST':
        if 'rehabilitate' in request.POST:
            try:
                with transaction.atomic():
                    on_rework_status = AssignmentStatus.objects.get(assignment_status_name='на доработке')
                    submission.submission_status = on_rework_status
                    submission.save()
                    
                    if not feedback:
                        feedback = Feedback(user_practical_assignment=submission)
                    
                    rehabilitate_comment = request.POST.get('comment_feedback', '')
                    if rehabilitate_comment:
                        old_comment = feedback.comment_feedback or ''
                        if old_comment:
                            feedback.comment_feedback = f"{old_comment}\n\n[принято в работу заново] {rehabilitate_comment}"
                        else:
                            feedback.comment_feedback = f"[принято в работу заново] {rehabilitate_comment}"
                        feedback.save()
                    
                    messages.success(request, f'Работа "{assignment.practical_assignment_name}" принята в работу! Слушатель может исправить её.')
                    return redirect('teacher_app:listener_progress', course_id=course.id, student_id=submission.user.id)
                    
            except AssignmentStatus.DoesNotExist:
                messages.error(request, 'Статус "на доработке" не найден в системе')
            except Exception as e:
                messages.error(request, f'Ошибка при повторном принятии работы без статуса отклонено: {str(e)}')
            
            return redirect('teacher_app:grade_assignment', submission_id=submission.id)
        
        if 'reject' in request.POST:
            try:
                with transaction.atomic():
                    rejected_status = AssignmentStatus.objects.get(assignment_status_name='отклонено')
                    
                    if not feedback:
                        feedback = Feedback(user_practical_assignment=submission)
                    
                    if assignment.grading_type == 'points':
                        feedback.score = 0
                        feedback.is_passed = None
                    else:
                        feedback.score = None
                        feedback.is_passed = False
                    
                    feedback.comment_feedback = request.POST.get('comment_feedback', 'Работа отклонена преподавателем')
                    feedback.given_by = request.user
                    feedback.given_at = timezone.now()
                    feedback.save()
                    
                    submission.submission_status = rejected_status
                    submission.save()
                    
                    messages.warning(request, f'Работа "{assignment.practical_assignment_name}" отклонена!')
                    return redirect('teacher_app:listener_progress', course_id=course.id, student_id=submission.user.id)
                    
            except AssignmentStatus.DoesNotExist:
                messages.error(request, 'Статус "отклонено" не найден в системе')
            except Exception as e:
                messages.error(request, f'Ошибка при отклонении работы: {str(e)}')
            
            return redirect('teacher_app:grade_assignment', submission_id=submission.id)
        
        form = TeacherGradeForm(request.POST)
        
        if form.is_valid():
            try:
                with transaction.atomic():
                    completed_status = AssignmentStatus.objects.get(assignment_status_name='завершено')
                    on_rework_status = AssignmentStatus.objects.get(assignment_status_name='на доработке')
                    
                    if not feedback:
                        feedback = Feedback(user_practical_assignment=submission)
                    
                    if assignment.grading_type == 'points':
                        score = form.cleaned_data.get('score')
                        if score is not None:
                            feedback.score = score
                            feedback.is_passed = None
                            
                            passing_score = assignment.passing_score
                            if passing_score is not None:
                                if score >= passing_score:
                                    submission.submission_status = completed_status
                                else:
                                    submission.submission_status = on_rework_status
                            else:
                                min_score = assignment.max_score * 0.5 if assignment.max_score else 0
                                if score >= min_score:
                                    submission.submission_status = completed_status
                                else:
                                    submission.submission_status = on_rework_status
                        else:
                            messages.error(request, 'Для балльной системы необходимо указать баллы')
                            return render(request, 'teacher_grade_assignment.html', {
                                'submission': submission,
                                'feedback': feedback,
                                'course': course,
                                'assignment': assignment,
                                'form': form,
                                'is_overdue': is_overdue,
                                'overdue_text': overdue_text,
                                'is_rejected': is_rejected,
                            })
                    else:
                        is_passed_str = form.cleaned_data.get('is_passed')
                        if is_passed_str is not None:
                            feedback.is_passed = (is_passed_str == 'true')
                            feedback.score = None
                            
                            if feedback.is_passed:
                                submission.submission_status = completed_status
                            else:
                                submission.submission_status = on_rework_status
                        else:
                            messages.error(request, 'Для системы "зачёт/незачёт" необходимо выбрать оценку')
                            return render(request, 'teacher_grade_assignment.html', {
                                'submission': submission,
                                'feedback': feedback,
                                'course': course,
                                'assignment': assignment,
                                'form': form,
                                'is_overdue': is_overdue,
                                'overdue_text': overdue_text,
                                'is_rejected': is_rejected,
                            })
                    
                    feedback.comment_feedback = form.cleaned_data.get('comment_feedback', '')
                    feedback.given_by = request.user
                    feedback.given_at = timezone.now()
                    feedback.save()
                    submission.save()
                    
                    messages.success(request, 'Оценка успешно сохранена!')
                    return redirect('teacher_app:listener_progress', course_id=course.id, student_id=submission.user.id)
                    
            except AssignmentStatus.DoesNotExist:
                messages.error(request, 'Не найдены необходимые статусы работ')
            except Exception as e:
                messages.error(request, f'Ошибка при сохранении оценки: {str(e)}')
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        initial_data = {}
        if feedback:
            if assignment.grading_type == 'points':
                initial_data['score'] = feedback.score
            else:
                initial_data['is_passed'] = 'true' if feedback.is_passed else 'false'
            initial_data['comment_feedback'] = feedback.comment_feedback
        form = TeacherGradeForm(initial=initial_data)
    
    context = {
        'submission': submission,
        'feedback': feedback,
        'course': course,
        'assignment': assignment,
        'form': form,
        'passing_score': assignment.passing_score,
        'min_score': assignment.max_score * 0.5 if assignment.max_score and not assignment.passing_score else None,
        'is_overdue': is_overdue,
        'overdue_text': overdue_text,
        'is_rejected': is_rejected,
    }
    return render(request, 'teacher_grade_assignment.html', context)

@login_required
@user_passes_test(is_teacher)
def teacher_statistics(request):
    """Статистика для преподавателя (аналитика по слушателям)"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    today = timezone.now().date()
    
    if not start_date:
        start_date = (today - timedelta(days=30)).isoformat()
    if not end_date:
        end_date = today.isoformat()
    
    teacher_courses = CourseTeacher.objects.filter(
        teacher=request.user,
        is_active=True
    ).values_list('course_id', flat=True)
    
    courses_stats = []
    for course_id in teacher_courses:
        course = Course.objects.get(id=course_id)
        
        enrollments = UserCourse.objects.filter(course=course, is_active=True)
        if start_date:
            enrollments = enrollments.filter(registration_date__gte=start_date)
        if end_date:
            enrollments = enrollments.filter(registration_date__lte=end_date)
        
        total_students = enrollments.count()
        completed_students = enrollments.filter(status_course=True).count()
        avg_progress = course.get_average_progress()  
        avg_score = Feedback.objects.filter(
            user_practical_assignment__practical_assignment__lecture__course=course,
            score__isnull=False
        ).aggregate(avg=Avg('score'))['avg'] or 0
        
        courses_stats.append({
            'course': course,
            'total_students': total_students,
            'completed_students': completed_students,
            'avg_progress': avg_progress,
            'avg_score': avg_score,
        })
    
    grade_distribution = {
        'excellent': 0,
        'good': 0,
        'satisfactory': 0,
        'unsatisfactory': 0,
    }
    
    all_feedbacks = Feedback.objects.filter(
        user_practical_assignment__practical_assignment__lecture__course__in=teacher_courses,
        score__isnull=False
    )
    
    for fb in all_feedbacks:
        if fb.score and fb.user_practical_assignment.practical_assignment.max_score:
            percentage = (fb.score / fb.user_practical_assignment.practical_assignment.max_score) * 100
            if percentage >= 90:
                grade_distribution['excellent'] += 1
            elif percentage >= 75:
                grade_distribution['good'] += 1
            elif percentage >= 50:
                grade_distribution['satisfactory'] += 1
            else:
                grade_distribution['unsatisfactory'] += 1
    
    course_names = [stat['course'].course_name[:20] for stat in courses_stats]
    student_counts = [stat['total_students'] for stat in courses_stats]
    progress_data = [stat['avg_progress'] for stat in courses_stats]
    
    context = {
        'courses_stats': courses_stats,
        'grade_distribution': grade_distribution,
        'start_date': start_date,
        'end_date': end_date,
        'course_names_json': json.dumps(course_names),
        'student_counts_json': json.dumps(student_counts),
        'progress_data_json': json.dumps(progress_data),
    }
    return render(request, 'teacher_statistics.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_export_statistics(request, export_type, format_type):
    """Экспорт статистики в CSV или PDF"""
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    today = timezone.now().date()
    
    if start_date:
        try:
            start_date = datetime.strptime(start_date, '%Y-%m-%d').date()
        except ValueError:
            start_date = today - timedelta(days=30)
    else:
        start_date = today - timedelta(days=30)
    
    if end_date:
        try:
            end_date = datetime.strptime(end_date, '%Y-%m-%d').date()
        except ValueError:
            end_date = today
    else:
        end_date = today
    
    teacher_courses = CourseTeacher.objects.filter(
        teacher=request.user,
        is_active=True
    ).values_list('course_id', flat=True)
    
    if export_type == 'students':
        data = []
        for course_id in teacher_courses:
            course = Course.objects.get(id=course_id)
            enrollments = UserCourse.objects.filter(course=course, is_active=True)
            if start_date:
                enrollments = enrollments.filter(registration_date__gte=start_date)
            if end_date:
                enrollments = enrollments.filter(registration_date__lte=end_date)
            
            total = enrollments.count()
            completed = enrollments.filter(status_course=True).count()
            avg_progress = course.get_average_progress() 
            
            data.append({
                'course_name': course.course_name,
                'total_students': total,
                'completed_students': completed,
                'avg_progress': avg_progress,
            })
        
        if format_type == 'csv':
            return export_statistics_csv(request, data, 'students', start_date, end_date)
        else:
            return export_statistics_pdf(request, data, 'students', start_date, end_date)
    
    elif export_type == 'grades':
        data = []
        for course_id in teacher_courses:
            course = Course.objects.get(id=course_id)
            
            feedbacks = Feedback.objects.filter(
                user_practical_assignment__practical_assignment__lecture__course=course,
                score__isnull=False
            )
            
            if start_date:
                feedbacks = feedbacks.filter(given_at__date__gte=start_date)
            if end_date:
                feedbacks = feedbacks.filter(given_at__date__lte=end_date)
            
            total = feedbacks.count()
            avg_score = feedbacks.aggregate(avg=Avg('score'))['avg'] or 0
            
            data.append({
                'course_name': course.course_name,
                'total_grades': total,
                'avg_score': avg_score,
            })
        
        if format_type == 'csv':
            return export_statistics_csv(request, data, 'grades', start_date, end_date)
        else:
            return export_statistics_pdf(request, data, 'grades', start_date, end_date)
    
    messages.error(request, 'Неверный тип экспорта')
    return redirect('teacher_app:statistics')


@login_required
@user_passes_test(is_teacher)
def teacher_generate_listeners_csv(request, course_id):
    """Генерация CSV с паролями для слушателей и отправка email"""
    course = get_object_or_404(Course, id=course_id)
    
    if not (can_edit_course(request.user, course) or can_teach_course(request.user, course)):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('teacher_app:dashboard')
    
    if request.method == 'POST':
        response = HttpResponse(content_type='text/csv; charset=utf-8-sig')
        response['Content-Disposition'] = f'attachment; filename="students_{course_id}_{timezone.now().date()}.csv"'
        response.write('\ufeff')
        
        writer = csv.writer(response)
        writer.writerow(['first_name', 'last_name', 'patronymic', 'email', 'username', 'password', 'status', 'email_sent'])
        
        try:
            student_role = Role.objects.get(role_name='слушатель курсов')
        except Role.DoesNotExist:
            messages.error(request, 'Роль "слушатель курсов" не найдена в системе')
            return redirect('teacher_app:listeners_list', course_id=course_id)
        
        created_count = 0
        existing_count = 0
        users_to_notify = []  
        errors = []
        
        with transaction.atomic():
            i = 0
            while True:
                first_name = request.POST.get(f'first_name_{i}')
                if first_name is None:
                    break
                
                last_name = request.POST.get(f'last_name_{i}', '').strip()
                patronymic = request.POST.get(f'patronymic_{i}', '').strip()
                email = request.POST.get(f'email_{i}', '').strip().lower()
                
                if not (first_name and last_name and email):
                    i += 1
                    continue
                
                try:
                    existing_user = User.objects.filter(email=email).first()
                    
                    if existing_user:
                        user = existing_user
                        existing_count += 1
                        
                        user_course, created = UserCourse.objects.get_or_create(
                            user=user,
                            course=course,
                            defaults={
                                'registration_date': timezone.now().date(),
                                'status_course': False,
                                'course_price': course.course_price or 0,
                                'is_active': True,
                            }
                        )
                        
                        writer.writerow([
                            first_name,
                            last_name,
                            patronymic,
                            email,
                            user.username,
                            '(существующий)',
                            'Существующий пользователь',
                            'Будет отправлено'
                        ])
                        
                        users_to_notify.append((user, None, False))
                        
                    else:
                        username = email.split('@')[0]
                        base_username = username
                        counter = 1
                        while User.objects.filter(username=username).exists():
                            username = f"{base_username}{counter}"
                            counter += 1
                        
                        password_plain = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                        
                        user = User(
                            username=username,
                            email=email,
                            first_name=first_name,
                            last_name=last_name,
                            patronymic=patronymic or None,
                            role=student_role,
                            is_verified=True,
                            is_active=True,
                        )
                        user.set_password(password_plain)
                        user.save()
                        
                        created_count += 1

                        UserCourse.objects.create(
                            user=user,
                            course=course,
                            registration_date=timezone.now().date(),
                            status_course=False,
                            course_price=course.course_price or 0,
                            is_active=True
                        )
                        
                        writer.writerow([
                            first_name,
                            last_name,
                            patronymic,
                            email,
                            username,
                            password_plain,
                            'Новый пользователь',
                            'Будет отправлено'
                        ])
                        
                        users_to_notify.append((user, password_plain, True))
                        
                except Exception as e:
                    error_msg = f"Ошибка при создании {email}: {str(e)}"
                    errors.append(error_msg)
                    writer.writerow([
                        first_name,
                        last_name,
                        patronymic,
                        email,
                        '',
                        'ОШИБКА',
                        str(e),
                        'Нет'
                    ])
                
                i += 1
        
        if users_to_notify:
            send_bulk_emails(users_to_notify, course.course_name, request)
        if created_count:
            messages.success(request, f'Создано {created_count} новых аккаунтов.')
        if existing_count:
            messages.info(request, f'{existing_count} существующих пользователей добавлены на курс.')
        if errors:
            messages.warning(request, f'Ошибки: {" | ".join(errors[:5])}')
        
        return response
    
    return redirect('teacher_app:listeners_list', course_id=course_id)



@login_required
@user_passes_test(is_teacher)
def teacher_upload_listeners_csv(request, course_id):
    """Загрузка слушателей из CSV-файла с отправкой email"""
    course = get_object_or_404(Course, id=course_id)
    
    if not (can_edit_course(request.user, course) or can_teach_course(request.user, course)):
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('teacher_app:dashboard')
    
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        
        if not csv_file.name.lower().endswith('.csv'):
            messages.error(request, 'Файл должен иметь расширение .csv')
            return redirect('teacher_app:listeners_list', course_id=course_id)
        
        try:
            file_content = csv_file.read()
            if file_content.startswith(b'\xef\xbb\xbf'):
                file_content = file_content[3:]
            
            decoded_file = file_content.decode('utf-8')
            reader = csv.DictReader(StringIO(decoded_file))
            
            headers = [h.strip().replace('\ufeff', '').lower() for h in reader.fieldnames]
            
            required_fields = {'first_name', 'last_name', 'email'}
            if not required_fields.issubset(set(headers)):
                messages.error(request, f'CSV должен содержать колонки: {", ".join(required_fields)}')
                return redirect('teacher_app:listeners_list', course_id=course_id)
            
            try:
                student_role = Role.objects.get(role_name='слушатель курсов')
            except Role.DoesNotExist:
                messages.error(request, 'Роль "слушатель курсов" не найдена в системе')
                return redirect('teacher_app:listeners_list', course_id=course_id)
            
            created_count = 0
            existing_count = 0
            users_to_notify = []
            errors = []
            
            with transaction.atomic():
                for row_num, row in enumerate(reader, start=2):
                    row_data = {}
                    for key, value in row.items():
                        clean_key = key.strip().replace('\ufeff', '').lower()
                        row_data[clean_key] = value.strip() if value else ''
                    
                    email = row_data.get('email', '').lower()
                    first_name = row_data.get('first_name', '')
                    last_name = row_data.get('last_name', '')
                    patronymic = row_data.get('patronymic', '')
                    
                    if not (email and first_name and last_name):
                        errors.append(f"Строка {row_num}: не заполнены обязательные поля (email, first_name, last_name)")
                        continue

                    try:
                        validate_email(email)
                    except ValidationError:
                        errors.append(f"Строка {row_num}: неверный формат email {email}")
                        continue
                    
                    try:
                        existing_user = User.objects.filter(email=email).first()
                        
                        if existing_user:
                            user = existing_user
                            existing_count += 1
                            
                            user_course, created = UserCourse.objects.get_or_create(
                                user=user,
                                course=course,
                                defaults={
                                    'registration_date': timezone.now().date(),
                                    'status_course': False,
                                    'course_price': course.course_price or 0,
                                    'is_active': True,
                                }
                            )
                            
                            users_to_notify.append((user, None, False))
                            
                        else:
                            username = email.split('@')[0]
                            base_username = username
                            counter = 1
                            while User.objects.filter(username=username).exists():
                                username = f"{base_username}{counter}"
                                counter += 1
                            
                            password_plain = ''.join(random.choices(string.ascii_letters + string.digits, k=12))
                            
                            user = User(
                                username=username,
                                email=email,
                                first_name=first_name,
                                last_name=last_name,
                                patronymic=patronymic or None,
                                role=student_role,
                                is_verified=True,
                                is_active=True,
                            )
                            user.set_password(password_plain)
                            user.save()
                            
                            created_count += 1

                            UserCourse.objects.create(
                                user=user,
                                course=course,
                                registration_date=timezone.now().date(),
                                status_course=False,
                                course_price=course.course_price or 0,
                                is_active=True
                            )
                            
                            users_to_notify.append((user, password_plain, True))
                            
                    except Exception as e:
                        errors.append(f"Строка {row_num}: {str(e)}")

            if users_to_notify:
                send_bulk_emails(users_to_notify, course.course_name, request)
                messages.info(request, f'Уведомления отправляются на email-адреса пользователей')

            if created_count:
                messages.success(request, f'Добавлено новых слушателей: {created_count}')
            if errors:
                messages.warning(request, f'Ошибки в некоторых строках: {" | ".join(errors[:7])}')
                
        except Exception as e:
            messages.error(request, f'Ошибка обработки файла: {str(e)}')
    
    return redirect('teacher_app:listeners_list', course_id=course_id)


@login_required
@user_passes_test(is_teacher)
def teacher_pending_submissions(request):
    """Все работы на проверке по всем курсам преподавателя"""
    teacher_courses = CourseTeacher.objects.filter(
        teacher=request.user,
        is_active=True
    ).values_list('course_id', flat=True)
    
    pending_submissions = UserPracticalAssignment.objects.filter(
        practical_assignment__lecture__course_id__in=teacher_courses,
        submission_status__assignment_status_name='на проверке'
    ).select_related(
        'user',
        'practical_assignment',
        'practical_assignment__lecture',
        'practical_assignment__lecture__course',
        'submission_status'
    ).prefetch_related('assignmentsubmissionfile_set').order_by('-submission_date')
    
    context = {
        'pending_submissions': pending_submissions,
    }
    return render(request, 'teacher_pending_submissions.html', context)


@login_required
def apply_for_teaching(request, course_id):
    """
    Обработка заявки от преподавателя на преподавание курса
    """
    if not request.user.role or request.user.role.role_name.lower() != 'преподаватель':
        messages.error(request, 'Только преподаватели могут подавать заявки')
        return redirect('main_page')
    
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    if CourseTeacher.objects.filter(course=course, teacher=request.user, is_active=True).exists():
        messages.info(request, 'Вы уже преподаватель на этом курсе.')
        return redirect('course_detail', course_id=course_id)
    
    existing_app = TeacherApplication.objects.filter(teacher=request.user, course=course).first()
    if existing_app:
        if existing_app.status == 'pending':
            messages.warning(request, 'Заявка уже отправлена. Ожидайте решения методиста.')
        elif existing_app.status == 'approved':
            messages.info(request, 'Вы уже преподаватель на этом курсе.')
        elif existing_app.status == 'rejected':
            messages.warning(request, 'Ваша заявка была отклонена.')
        return redirect('course_detail', course_id=course_id)

    try:
        application = TeacherApplication.objects.create(
            teacher=request.user,
            course=course,
            status='pending'
        )
        
        methodist_email = None
        methodist_name = None
        
        if course.created_by and course.created_by.role and course.created_by.role.role_name.lower() == 'методист':
            methodist_email = course.created_by.email
            methodist_name = course.created_by.get_full_name() or course.created_by.username
        
        if methodist_email:
            try:
                send_new_teacher_application_notification(
                    methodist_email=methodist_email,
                    methodist_name=methodist_name,
                    teacher_name=request.user.get_full_name() or request.user.username,
                    teacher_email=request.user.email,
                    course_name=course.course_name,
                    application_id=application.id,
                    request=request
                )
            except Exception as e:
                print(f"Email error: {e}")
        
        messages.success(request, f'Заявка на преподавание курса "{course.course_name}" успешно отправлена! Методист рассмотрит её в ближайшее время.')
        
    except Exception as e:
        messages.error(request, f'Ошибка при отправке заявки: {str(e)}')
        return redirect('course_detail', course_id=course_id)
    
    return redirect('course_detail', course_id=course_id)


@login_required
@user_passes_test(is_teacher)
def teacher_course_posts_manage(request, course_id):
    """Страница управления постами курса для преподавателя"""
    from unireax_main.models import CoursePost
    
    course = get_object_or_404(Course, id=course_id)
    
    if not can_teach_course(request.user, course) and not can_edit_course(request.user, course):
        messages.error(request, 'У вас нет доступа к управлению этим курсом')
        return redirect('teacher_app:dashboard')
    
    posts = CoursePost.objects.filter(course=course, is_active=True).order_by('-is_pinned', '-created_at')
    
    context = {
        'course': course,
        'posts': posts,
        'post_types': CoursePost.POST_TYPES,
    }
    return render(request, 'course_posts_manage.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_course_post_create(request, course_id):
    """Создание нового поста"""
    from unireax_main.models import CoursePost
    
    course = get_object_or_404(Course, id=course_id)
    
    if not can_teach_course(request.user, course) and not can_edit_course(request.user, course):
        messages.error(request, 'У вас нет доступа')
        return redirect('teacher_app:dashboard')
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        post_type = request.POST.get('post_type', 'announcement')
        is_pinned = request.POST.get('is_pinned') == 'on'
        
        errors = []
        if not title or len(title) < 3:
            errors.append('Заголовок должен содержать минимум 3 символа')
        if not content or len(content) < 10:
            errors.append('Содержание должно содержать минимум 10 символов')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            CoursePost.objects.create(
                course=course,
                author=request.user,
                title=title,
                content=content,
                post_type=post_type,
                is_pinned=is_pinned
            )
            messages.success(request, 'Объявление успешно создано!')
            return redirect('teacher_app:course_posts_manage', course_id=course.id)
    
    context = {
        'course': course,
        'post_types': CoursePost.POST_TYPES,
    }
    return render(request, 'course_post_form.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_course_post_edit(request, post_id):
    """Редактирование поста"""
    from unireax_main.models import CoursePost
    
    post = get_object_or_404(CoursePost, id=post_id)
    course = post.course
    
    if not can_teach_course(request.user, course) and not can_edit_course(request.user, course):
        messages.error(request, 'У вас нет доступа')
        return redirect('teacher_app:dashboard')
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        content = request.POST.get('content', '').strip()
        post_type = request.POST.get('post_type', post.post_type)
        is_pinned = request.POST.get('is_pinned') == 'on'
        
        errors = []
        if not title or len(title) < 3:
            errors.append('Заголовок должен содержать минимум 3 символа')
        if not content or len(content) < 10:
            errors.append('Содержание должно содержать минимум 10 символов')
        
        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            post.title = title
            post.content = content
            post.post_type = post_type
            post.is_pinned = is_pinned
            post.save()
            messages.success(request, 'Объявление обновлено!')
            return redirect('teacher_app:course_posts_manage', course_id=course.id)
    
    context = {
        'post': post,
        'course': course,
        'post_types': CoursePost.POST_TYPES,
    }
    return render(request, 'course_post_form.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_course_post_delete(request, post_id):
    """Удаление поста (мягкое удаление)"""
    from unireax_main.models import CoursePost
    
    post = get_object_or_404(CoursePost, id=post_id)
    course = post.course
    
    if not can_teach_course(request.user, course) and not can_edit_course(request.user, course):
        messages.error(request, 'У вас нет доступа')
        return redirect('teacher_app:dashboard')
    
    if request.method == 'POST':
        post.is_active = False
        post.save()
        messages.success(request, 'Объявление удалено!')
        return redirect('teacher_app:course_posts_manage', course_id=course.id)
    
    context = {
        'post': post,
        'course': course,
    }
    return render(request, 'course_post_confirm_delete.html', context)


@login_required
@user_passes_test(is_teacher)
def teacher_add_comment_to_post(request, post_id):
    """Добавление комментария от преподавателя к посту (с поддержкой ответов)"""
    from unireax_main.models import CoursePost, CoursePostComment
    from django.http import JsonResponse
    from django.utils import timezone
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    post = get_object_or_404(CoursePost, id=post_id, is_active=True)
    course = post.course
    
    if not can_teach_course(request.user, course) and not can_edit_course(request.user, course):
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id')  
    
    if not content or len(content) < 2:
        return JsonResponse({'error': 'Комментарий слишком короткий'}, status=400)
    
    parent = None
    if parent_id:
        parent = get_object_or_404(CoursePostComment, id=parent_id)
    
    comment = CoursePostComment.objects.create(
        post=post,
        author=request.user,
        parent=parent,
        content=content
    )
    
    local_dt = timezone.localtime(comment.created_at)
    author_name = comment.author.get_full_name() or comment.author.username
    author_role = comment.author.role.role_name if comment.author.role else ''
    
    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.id,
            'author_name': author_name,
            'author_role': author_role,
            'content': comment.content,
            'created_at': local_dt.strftime('%d.%m.%Y %H:%M'),
            'can_delete': True,
            'is_teacher': True,
            'parent_id': parent_id
        }
    })


@login_required
@user_passes_test(is_teacher)
def teacher_delete_comment(request, comment_id):
    """Удаление комментария"""
    from unireax_main.models import CoursePostComment
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    comment = get_object_or_404(CoursePostComment, id=comment_id)
    course = comment.post.course
    
    if not can_teach_course(request.user, course) and not can_edit_course(request.user, course):
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    comment.delete()
    
    return JsonResponse({'success': True, 'message': 'Комментарий удалён!'})