import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.contrib.auth import logout, update_session_auth_hash
from django.db.models import F, Count, Avg, Q, Max
from django.urls import reverse
from django.utils import timezone
from unireax_main.models import ApplicationStatus, PostType
from django.db import transaction
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.db.models import Q, Count, Sum, Avg, FloatField
from django.db.models.functions import Coalesce
from django.core.paginator import Paginator
from unireax_main.utils.email_utils import send_new_teacher_application_notification

from unireax_main.models import (
    AssignmentStatus, TeacherApplication, User, Course, CourseCategory, CourseType, Lecture, 
    PracticalAssignment, Test, Question, ChoiceOption, 
    MatchingPair, AnswerType, UserCourse, Review, CourseTeacher, UserPracticalAssignment
)
from unireax_main.forms import ProfileInfoForm, ProfilePasswordChangeForm
from .forms import (
    CourseForm, LectureForm, PracticalAssignmentForm, 
    TestForm, QuestionForm
)
from .export_utils import export_statistics_csv, export_statistics_pdf


def is_methodist(user):
    """Проверка, является ли пользователь методистом"""
    return user.is_authenticated and user.role and user.role.role_name.lower() == "методист"

def is_methodist_or_admin(user):
    """Проверка, является ли пользователь методистом или администратором"""
    if not user.is_authenticated:
        return False
    role_name = user.role.role_name.lower() if user.role else ''
    return role_name in ["методист", "администратор"]

def is_methodist_or_teacher(user):
    """Проверка, является ли пользователь методистом или преподавателем"""
    return user.is_authenticated and user.role and user.role.role_name.lower() in ["методист", "преподаватель"]


def user_can_edit_course(user, course):
    """Проверяет, может ли пользователь редактировать курс"""
    if not user.is_authenticated:
        return False
    
    if user.role and user.role.role_name.lower() == "администратор":
        return True
    if course.created_by == user:
        return True
    
    if CourseTeacher.objects.filter(
        course=course, 
        teacher=user, 
        is_active=True
    ).exists():
        return True
    
    return False


def user_can_view_course(user, course):
    """Проверяет, может ли пользователь просматривать курс (для чтения)"""
    if not user.is_authenticated:
        return False
    
    if user.role and user.role.role_name.lower() == "администратор":
        return True
    
    if course.created_by == user:
        return True

    if CourseTeacher.objects.filter(
        course=course, 
        teacher=user, 
        is_active=True
    ).exists():
        return True
    
    return False

@login_required
@user_passes_test(is_methodist)
def methodist_profile(request):
    user = request.user
    
    if request.method == 'POST' and 'update_profile' in request.POST:
        form = ProfileInfoForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Личная информация успешно обновлена!')
            return redirect('methodist_app:profile')
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
            return redirect('methodist_app:profile')
        else:
            for error in password_form.errors.values():
                messages.error(request, error)
    
    my_courses = Course.objects.filter(created_by=user).order_by('-created_at')
    
    total_courses = my_courses.count()
    total_students = UserCourse.objects.filter(course__in=my_courses, is_active=True).count()
    total_completed = UserCourse.objects.filter(course__in=my_courses, status_course=True).count()
    avg_completion = (total_completed / total_students * 100) if total_students > 0 else 0
    
    context = {
        'user': user,
        'full_name': user.get_full_name() or user.username,
        'date_joined': user.date_joined.strftime('%d.%m.%Y'),
        'is_verified': user.is_verified,
        'form': form,
        'password_form': password_form,
        'my_courses': my_courses,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_completed': total_completed,
        'avg_completion': avg_completion,
    }
    return render(request, 'methodist_profile.html', context)


@login_required
@user_passes_test(is_methodist)
def methodist_deactivate_account(request):
    """Деактивация аккаунта методиста"""
    if request.method == 'POST':
        password = request.POST.get('password')
        user = request.user
        
        if not user.check_password(password):
            messages.error(request, 'Неверный пароль')
            return redirect('methodist_app:profile')
        
        try:
            with transaction.atomic():
                Course.objects.filter(created_by=user, is_active=True).update(is_active=False,is_find_teacher=False)
                CourseTeacher.objects.filter(teacher=user, is_active=True).update(is_active=False)
                Lecture.objects.filter(course__created_by=user, is_active=True).update(is_active=False)
                PracticalAssignment.objects.filter(lecture__course__created_by=user, is_active=True).update(is_active=False)
                Test.objects.filter(lecture__course__created_by=user, is_active=True).update(is_active=False)
                
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
            return redirect('methodist_app:profile')
    
    return redirect('methodist_app:profile')

@login_required
@user_passes_test(is_methodist)
def methodist_dashboard(request):
    courses = Course.objects.filter(
        Q(created_by=request.user) | 
        Q(courseteacher__teacher=request.user, courseteacher__is_active=True)
    ).annotate(
        student_count=Count(
            'usercourse', 
            filter=Q(usercourse__is_active=True),
            distinct=True
        ),
        completed_count=Count(
            'usercourse',
            filter=Q(usercourse__status_course=True),
            distinct=True
        )
    ).order_by('-created_at').distinct()

    stats = courses.aggregate(
        total_courses=Count('id', distinct=True),
        total_students=Sum('student_count'),
        total_completed=Sum('completed_count'),
    )
    
    total_courses = stats['total_courses'] or 0
    total_students = stats['total_students'] or 0
    total_completed = stats['total_completed'] or 0
    
    avg_completion = (total_completed / total_students * 100) if total_students > 0 else 0
    
    for course in courses:
        course.is_creator = (course.created_by == request.user)
        student_count = getattr(course, 'student_count', 0)
        completed_count = getattr(course, 'completed_count', 0)
        course.completion_percent = (completed_count / student_count * 100) if student_count > 0 else 0
    
    context = {
        'courses': courses,
        'total_courses': total_courses,
        'total_students': total_students,
        'total_completed': total_completed,
        'avg_completion': avg_completion,
    }
    return render(request, 'methodist_dashboard.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_course_builder(request, course_id=None):
    if course_id:

        try:
            course = Course.objects.get(id=course_id)
            
            if not user_can_edit_course(request.user, course):
                messages.error(request, 'У вас нет доступа к редактированию этого курса')
                return redirect('methodist_app:dashboard')
                
        except Course.DoesNotExist:
            messages.error(request, f'Курс с ID {course_id} не найден')
            return redirect('methodist_app:dashboard')
    else:
        course = None
    
    if request.method == 'POST':
        form = CourseForm(request.POST, request.FILES, instance=course)
        if form.is_valid():
            new_course = form.save(commit=False)
            if not course:
                new_course.created_by = request.user
            new_course.save()
            
            if course is None and request.user != new_course.created_by:
                CourseTeacher.objects.get_or_create(
                    course=new_course,
                    teacher=request.user,
                    defaults={'is_active': True}
                )
            
            messages.success(request, f'Курс "{new_course.course_name}" успешно сохранен!')
            return redirect('methodist_app:course_detail', course_id=new_course.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = CourseForm(instance=course)
    
    context = {
        'form': form,
        'course': course,
        'categories': CourseCategory.objects.all(),
        'types': CourseType.objects.all(),
        'can_edit': True,
    }
    return render(request, 'methodist_course_builder.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_course_detail(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
        
        if not user_can_view_course(request.user, course):
            messages.error(request, 'У вас нет доступа к этому курсу')
            return redirect('methodist_app:dashboard')
            
    except Course.DoesNotExist:
        messages.error(request, f'Курс с ID {course_id} не найден')
        return redirect('methodist_app:dashboard')

    can_edit = user_can_edit_course(request.user, course)
    
    enrollments = UserCourse.objects.filter(course=course, is_active=True)
    total_students = enrollments.count()
    completed_students = enrollments.filter(status_course=True).count()
    completion_rate = (completed_students / total_students * 100) if total_students > 0 else 0
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    assignments = PracticalAssignment.objects.filter(lecture__course=course, is_active=True).select_related('lecture')
    tests = Test.objects.filter(lecture__course=course, is_active=True).select_related('lecture')
    avg_rating = Review.objects.filter(course=course, is_approved=True).aggregate(avg=Avg('rating'))['avg'] or 0
    
    context = {
        'course': course,
        'total_students': total_students,
        'completed_students': completed_students,
        'completion_rate': completion_rate,
        'lectures': lectures,
        'assignments': assignments,
        'tests': tests,
        'avg_rating': avg_rating,
        'can_edit': can_edit,
    }
    return render(request, 'methodist_course_detail.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_course_delete(request, course_id):
    try:
        course = Course.objects.get(id=course_id)

        if course.created_by != request.user:
            messages.error(request, 'Только автор курса может его удалить')
            return redirect('methodist_app:course_detail', course_id=course_id)
            
    except Course.DoesNotExist:
        messages.error(request, f'Курс с ID {course_id} не найден')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        course_name = course.course_name
        course.delete()
        messages.success(request, f'Курс "{course_name}" успешно удален!')
        return redirect('methodist_app:dashboard')
    
    context = {
        'object_name': course.course_name,
        'cancel_url': reverse('methodist_app:course_detail', kwargs={'course_id': course_id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)

@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_lecture_create(request, course_id):
    try:
        course = Course.objects.get(id=course_id)
        
        if not user_can_edit_course(request.user, course):
            messages.error(request, 'У вас нет доступа к созданию лекций в этом курсе')
            return redirect('methodist_app:dashboard')
            
    except Course.DoesNotExist:
        messages.error(request, f'Курс с ID {course_id} не найден')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        form = LectureForm(request.POST, request.FILES)
        if form.is_valid():
            lecture = form.save(commit=False)
            lecture.course = course
            lecture.save()
            messages.success(request, f'Лекция "{lecture.lecture_name}" успешно создана!')
            return redirect('methodist_app:course_detail', course_id=course.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = LectureForm()
    
    context = {'form': form, 'course': course, 'lecture': None}
    return render(request, 'methodist_lecture_form.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_lecture_edit(request, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id)
    
    if not user_can_edit_course(request.user, lecture.course):
        messages.error(request, 'У вас нет доступа к этой лекции')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        form = LectureForm(request.POST, request.FILES, instance=lecture)
        if form.is_valid():
            form.save()
            messages.success(request, f'Лекция "{lecture.lecture_name}" успешно обновлена!')
            return redirect('methodist_app:course_detail', course_id=lecture.course.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = LectureForm(instance=lecture)
    
    context = {'form': form, 'course': lecture.course, 'lecture': lecture}
    return render(request, 'methodist_lecture_form.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_lecture_delete(request, lecture_id):
    lecture = get_object_or_404(Lecture, id=lecture_id)
    
    if not user_can_edit_course(request.user, lecture.course):
        messages.error(request, 'У вас нет доступа к этой лекции')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        course_id = lecture.course.id
        lecture_name = lecture.lecture_name
        lecture.delete()
        messages.success(request, f'Лекция "{lecture_name}" успешно удалена!')
        return redirect('methodist_app:course_detail', course_id=course_id)
    
    context = {
        'object_name': lecture.lecture_name,
        'cancel_url': reverse('methodist_app:course_detail', kwargs={'course_id': lecture.course.id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_assignment_create(request, course_id):
    try:
        course = Course.objects.get(id=course_id)

        if not user_can_edit_course(request.user, course):
            messages.error(request, 'У вас нет доступа к созданию заданий в этом курсе')
            return redirect('methodist_app:dashboard')
            
    except Course.DoesNotExist:
        messages.error(request, f'Курс с ID {course_id} не найден')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        form = PracticalAssignmentForm(request.POST, request.FILES, course_id=course.id)
        if form.is_valid():
            assignment = form.save(commit=False)
            assignment.save()
            messages.success(request, f'Задание "{assignment.practical_assignment_name}" успешно создано!')
            return redirect('methodist_app:course_detail', course_id=course.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field in form.fields:
                        messages.error(request, f'{form.fields[field].label}: {error}')
                    else:
                        messages.error(request, error)
    else:
        form = PracticalAssignmentForm(course_id=course.id)
    
    context = {
        'form': form,
        'course': course,
        'assignment': None,
        'lectures': Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order'),
    }
    return render(request, 'methodist_assignment_form.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_assignment_edit(request, assignment_id):
    assignment = get_object_or_404(PracticalAssignment, id=assignment_id)
    
    if not user_can_edit_course(request.user, assignment.lecture.course):
        messages.error(request, 'У вас нет доступа к этому заданию')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        form = PracticalAssignmentForm(
            request.POST, 
            request.FILES, 
            instance=assignment,
            course_id=assignment.lecture.course.id
        )
        if form.is_valid():
            form.save()
            messages.success(request, f'Задание "{assignment.practical_assignment_name}" успешно обновлено!')
            return redirect('methodist_app:course_detail', course_id=assignment.lecture.course.id)
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    if field in form.fields:
                        messages.error(request, f'{form.fields[field].label}: {error}')
                    else:
                        messages.error(request, error)
    else:
        form = PracticalAssignmentForm(
            instance=assignment,
            course_id=assignment.lecture.course.id
        )
    
    context = {
        'form': form,
        'assignment': assignment,
        'course': assignment.lecture.course,
        'lectures': Lecture.objects.filter(course=assignment.lecture.course, is_active=True).order_by('lecture_order'),
    }
    return render(request, 'methodist_assignment_form.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_assignment_delete(request, assignment_id):
    assignment = get_object_or_404(PracticalAssignment, id=assignment_id)
    
    if not user_can_edit_course(request.user, assignment.lecture.course):
        messages.error(request, 'У вас нет доступа к этому заданию')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        course_id = assignment.lecture.course.id
        assignment_name = assignment.practical_assignment_name
        assignment.delete()
        messages.success(request, f'Задание "{assignment_name}" успешно удалено!')
        return redirect('methodist_app:course_detail', course_id=course_id)
    
    context = {
        'object_name': assignment.practical_assignment_name,
        'cancel_url': reverse('methodist_app:course_detail', kwargs={'course_id': assignment.lecture.course.id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_test_create(request, course_id):
    """Создание теста (для методиста или преподавателя)"""
    try:
        course = Course.objects.get(id=course_id)
        
        if not user_can_edit_course(request.user, course):
            messages.error(request, 'У вас нет доступа к созданию тестов в этом курсе')
            return redirect('methodist_app:dashboard')
            
    except Course.DoesNotExist:
        messages.error(request, f'Курс с ID {course_id} не найден')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        form = TestForm(request.POST, course_id=course.id)
        if form.is_valid():
            test = form.save(commit=False)
            test.save()
            messages.success(request, f'Тест "{test.test_name}" успешно создан!')
            return redirect('methodist_app:test_builder', test_id=test.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = TestForm(course_id=course.id)
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    
    context = {
        'form': form,
        'course': course,
        'test': None,
        'lectures': lectures,
    }
    return render(request, 'methodist_test_form.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_test_edit(request, test_id):
    """Редактирование теста (для методиста или преподавателя)"""
    test = get_object_or_404(Test, id=test_id)
    course = test.lecture.course
    
    if not user_can_edit_course(request.user, course):
        messages.error(request, 'У вас нет доступа к этому тесту')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        form = TestForm(request.POST, instance=test)
        if form.is_valid():
            test = form.save()
            messages.success(request, f'Тест "{test.test_name}" успешно обновлен!')
            return redirect('methodist_app:test_builder', test_id=test.id)
        else:
            for error in form.errors.values():
                messages.error(request, error)
    else:
        form = TestForm(instance=test)
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    context = {
        'form': form,
        'test': test,
        'course': course,
        'lectures': lectures,
    }
    return render(request, 'methodist_test_form.html', context)

@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_test_delete(request, test_id):
    test = get_object_or_404(Test, id=test_id)
    
    if not user_can_edit_course(request.user, test.lecture.course):
        messages.error(request, 'У вас нет доступа к этому тесту')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        course_id = test.lecture.course.id
        test_name = test.test_name
        test.delete()
        messages.success(request, f'Тест "{test_name}" успешно удален!')
        return redirect('methodist_app:course_detail', course_id=course_id)
    
    context = {
        'object_name': test.test_name,
        'cancel_url': reverse('methodist_app:course_detail', kwargs={'course_id': test.lecture.course.id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)

@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_test_builder(request, test_id):
    """Конструктор теста - добавление вопросов с поддержкой всех типов"""
    test = get_object_or_404(Test, id=test_id)
    course = test.lecture.course  
    
    if not user_can_edit_course(request.user, course):
        messages.error(request, 'У вас нет доступа к этому тесту')
        return redirect('methodist_app:dashboard')
    
    questions = Question.objects.filter(test=test).order_by('question_order')
    answer_types = AnswerType.objects.all()
    
    if request.method == 'POST':
        question_form = QuestionForm(request.POST)
        
        if question_form.is_valid():
            question = question_form.save(commit=False)
            question.test = test
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
            return redirect('methodist_app:test_builder', test_id=test.id)
        else:
            for error in question_form.errors.values():
                messages.error(request, error)
    else:
        max_order = questions.aggregate(max=Max('question_order'))['max'] or 0
        question_form = QuestionForm(initial={'question_order': max_order + 1})
    
    context = {
        'test': test,
        'course': course,  
        'questions': questions,
        'question_form': question_form,
        'answer_types': answer_types,
    }
    return render(request, 'methodist_test_builder.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_question_edit(request, question_id):
    """Редактирование вопроса"""
    question = get_object_or_404(Question, id=question_id)
    test = question.test

    if not user_can_edit_course(request.user, test.lecture.course):
        messages.error(request, 'У вас нет доступа к этому вопросу')
        return redirect('methodist_app:dashboard')
    
    answer_type_name = question.answer_type.answer_type_name if question.answer_type else ''
    options = []
    pairs = []

    if answer_type_name in ['один ответ', 'несколько ответов']:
        options = ChoiceOption.objects.filter(question=question)
        print(f"[DEBUG] Найдено вариантов: {options.count()}")
        for opt in options:
            print(f"  - {opt.option_text} (правильный: {opt.is_correct})")
    elif answer_type_name == 'сопоставление':
        pairs = MatchingPair.objects.filter(question=question)
        print(f"[DEBUG] Найдено пар: {pairs.count()}")
    
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
                    is_correct_value = request.POST.get('is_correct')
                    print(f"[DEBUG] Одиночный выбор, правильный вариант: {is_correct_value}")
                    
                    for i, text in enumerate(option_texts):
                        if text and text.strip():
                            is_correct = (str(i) == is_correct_value)
                            ChoiceOption.objects.create(
                                question=question,
                                option_text=text.strip(),
                                is_correct=is_correct
                            )
                            print(f"  Создан вариант {i}: {text.strip()} (правильный: {is_correct})")
                
                else:  
                    is_correct_list = request.POST.getlist('is_correct[]')
                    print(f"[DEBUG] Множественный выбор, правильные варианты: {is_correct_list}")
                    
                    for i, text in enumerate(option_texts):
                        if text and text.strip():
                            is_correct = str(i) in is_correct_list
                            ChoiceOption.objects.create(
                                question=question,
                                option_text=text.strip(),
                                is_correct=is_correct
                            )
                            print(f"  Создан вариант {i}: {text.strip()} (правильный: {is_correct})")
            
            elif answer_type_name == 'сопоставление':
                MatchingPair.objects.filter(question=question).delete()
                left_texts = request.POST.getlist('left_text[]')
                right_texts = request.POST.getlist('right_text[]')
                
                for left, right in zip(left_texts, right_texts):
                    if left and left.strip() and right and right.strip():
                        MatchingPair.objects.create(
                            question=question,
                            left_text=left.strip(),
                            right_text=right.strip()
                        )
                        print(f"  Создана пара: {left.strip()} -> {right.strip()}")
            
            messages.success(request, 'Вопрос успешно обновлен!')
            if request.user.role.role_name == 'методист':
                return redirect('methodist_app:test_builder', test_id=test.id)
            else:
                return redirect('teacher_app:test_builder', test_id=test.id)
        else:
            print(f"[DEBUG] Ошибки формы: {form.errors}")
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
@user_passes_test(is_methodist_or_teacher)
def methodist_question_delete(request, question_id):
    question = get_object_or_404(Question, id=question_id)
    test = question.test
    
    if not user_can_edit_course(request.user, test.lecture.course):
        messages.error(request, 'У вас нет доступа к этому вопросу')
        return redirect('methodist_app:dashboard')
    
    if request.method == 'POST':
        question.delete()
        messages.success(request, 'Вопрос успешно удален!')
        return redirect('methodist_app:test_builder', test_id=test.id)
    
    context = {
        'object_name': question.question_text[:50],
        'cancel_url': reverse('methodist_app:test_builder', kwargs={'test_id': test.id}),
    }
    return render(request, 'methodist_delete_confirm.html', context)


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_choice_option_delete(request, option_id):
    option = get_object_or_404(ChoiceOption, id=option_id)
    question = option.question
    test = question.test
    
    if not user_can_edit_course(request.user, test.lecture.course):
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    option.delete()
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_methodist_or_teacher)
def methodist_matching_pair_delete(request, pair_id):
    pair = get_object_or_404(MatchingPair, id=pair_id)
    question = pair.question
    test = question.test
    
    if not user_can_edit_course(request.user, test.lecture.course):
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    pair.delete()
    return JsonResponse({'success': True})


@login_required
@user_passes_test(is_methodist)
def methodist_statistics(request):
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    
    if not start_date:
        start_date = (timezone.now() - timedelta(days=30)).date()
    if not end_date:
        end_date = timezone.now().date()
    
    my_courses = Course.objects.filter(
        Q(created_by=request.user) | 
        Q(courseteacher__teacher=request.user, courseteacher__is_active=True)
    ).distinct()
    
    course_stats = []
    for course in my_courses:
        enrollments = UserCourse.objects.filter(course=course)
        
        if start_date:
            enrollments = enrollments.filter(registration_date__gte=start_date)
        if end_date:
            enrollments = enrollments.filter(registration_date__lte=end_date)
        
        completed = enrollments.filter(status_course=True).count()
        in_progress = enrollments.filter(status_course=False, is_active=True).count()
        total = enrollments.count()
        completion_rate = (completed / total * 100) if total > 0 else 0
        avg_rating = Review.objects.filter(course=course, is_approved=True).aggregate(avg=Avg('rating'))['avg'] or 0
        
        course_stats.append({
            'course': course,
            'total_enrollments': total,
            'completed': completed,
            'in_progress': in_progress,
            'completion_rate': completion_rate,
            'avg_rating': avg_rating,
        })
    
    popular_courses = Course.objects.annotate(
        total_students=Count('usercourse', filter=Q(usercourse__is_active=True)),
        avg_rating=Avg('review__rating', filter=Q(review__is_approved=True))
    ).filter(is_active=True).order_by('-total_students')[:10]
    
    course_names = [stat['course'].course_name[:20] for stat in course_stats]
    total_data = [stat['total_enrollments'] for stat in course_stats]
    completed_data = [stat['completed'] for stat in course_stats]
    
    popular_names = [course.course_name[:20] for course in popular_courses]
    popular_ratings = [float(course.avg_rating or 0) for course in popular_courses]
    popular_students = [course.total_students for course in popular_courses]
    
    context = {
        'course_stats': course_stats,
        'popular_courses': popular_courses,
        'start_date': start_date,
        'end_date': end_date,
        'course_names_json': json.dumps(course_names),
        'total_data_json': json.dumps(total_data),
        'completed_data_json': json.dumps(completed_data),
        'popular_names_json': json.dumps(popular_names),
        'popular_ratings_json': json.dumps(popular_ratings),
        'popular_students_json': json.dumps(popular_students),
    }
    return render(request, 'methodist_statistics.html', context)


@login_required
@user_passes_test(is_methodist)
def export_statistics(request, export_type, format_type):
    """Экспорт статистики в CSV или PDF"""
    start_date_str = request.GET.get('start_date')
    end_date_str = request.GET.get('end_date')
    today = datetime.now().date()
    
    try:
        if start_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        else:
            start_date = today - timedelta(days=30)
        
        if end_date_str:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        else:
            end_date = today
    except ValueError:
        start_date = today - timedelta(days=30)
        end_date = today
    
    if format_type == 'csv':
        return export_statistics_csv(request, export_type, start_date, end_date)
    elif format_type == 'pdf':
        return export_statistics_pdf(request, export_type, start_date, end_date)
    
    messages.error(request, 'Неверный формат экспорта')
    return redirect('methodist_app:statistics')


@login_required
@user_passes_test(is_methodist_or_admin)
def methodist_teacher_applications(request):
    """Страница управления заявками преподавателей"""
    my_courses = Course.objects.filter(
        Q(created_by=request.user) |
        Q(courseteacher__teacher=request.user, courseteacher__is_active=True)
    ).distinct()
    
    course_filter = request.GET.get('course', '')
    status_filter = request.GET.get('status', '')
    search_query = request.GET.get('search', '')
    applications = TeacherApplication.objects.filter(course__in=my_courses)
    
    if course_filter:
        applications = applications.filter(course_id=course_filter)
    if status_filter:
        applications = applications.filter(status__code=status_filter)
    if search_query:
        applications = applications.filter(
            Q(teacher__last_name__icontains=search_query) |
            Q(teacher__first_name__icontains=search_query) |
            Q(teacher__email__icontains=search_query)
        )
    
    applications = applications.select_related('teacher', 'course', 'status').order_by('-created_at')
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    all_statuses = ApplicationStatus.objects.all()
    
    context = {
        'applications': page_obj,
        'courses': my_courses,
        'course_filter': course_filter,
        'status_filter': status_filter,
        'search_query': search_query,
        'all_statuses': all_statuses, 
    }
    return render(request, 'methodist_teacher_applications.html', context)


@login_required
@user_passes_test(is_methodist_or_admin)
def methodist_application_detail(request, application_id):
    """Детальный просмотр заявки преподавателя"""
    application = get_object_or_404(TeacherApplication, id=application_id)
    
    my_courses = Course.objects.filter(
        Q(created_by=request.user) |
        Q(courseteacher__teacher=request.user, courseteacher__is_active=True)
    ).values_list('id', flat=True)
    
    if application.course_id not in my_courses:
        messages.error(request, 'У вас нет доступа к этой заявке')
        return redirect('methodist_app:teacher_applications')
    
    is_active_teacher = CourseTeacher.objects.filter(
        course=application.course,
        teacher=application.teacher,
        is_active=True
    ).exists()
    
    if request.method == 'POST':
        action = request.POST.get('action')
        comment = request.POST.get('comment', '')
        
        if action == 'approve':
            application.approve(request)
            messages.success(request, f'Заявка преподавателя {application.teacher.get_full_name()} одобрена!')
            return redirect('methodist_app:teacher_applications')
        
        elif action == 'reject':
            application.reject(comment, request)
            messages.success(request, f'Заявка преподавателя {application.teacher.get_full_name()} отклонена')
            return redirect('methodist_app:teacher_applications')
        
        elif action == 'remove':
            course_teacher = CourseTeacher.objects.filter(
                course=application.course,
                teacher=application.teacher,
                is_active=True
            ).first()
            
            if course_teacher:
                course_teacher.delete()
                messages.success(request, f'Преподаватель {application.teacher.get_full_name()} удален с курса "{application.course.course_name}"')
            else:
                messages.warning(request, 'Преподаватель не найден на этом курсе')
            
            return redirect('methodist_app:teacher_applications')
    
    context = {
        'application': application,
        'is_active_teacher': is_active_teacher,
    }
    return render(request, 'methodist_application_detail.html', context)