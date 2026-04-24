import json
import os
from datetime import datetime, timedelta
from io import BytesIO
from urllib.parse import quote
from django.contrib.auth import logout, update_session_auth_hash
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.core.paginator import Paginator
from django.db import connection
from django.db.models import Avg, Count, F, Q, Sum
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from reportlab.lib import colors
from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from unireax_main.models import (
    AnswerType, AssignmentStatus, AssignmentSubmissionFile, Certificate,
    ChoiceOption, Course, CourseCategory, CourseTeacher, CourseType, Feedback,
    Lecture, MatchingPair, PracticalAssignment, Question, Review, Role, Test,
    TestResult, User, UserAnswer, UserCourse, UserMatchingAnswer,
    UserPracticalAssignment, UserSelectedChoice, FavoriteCourse
)
from unireax_main.utils.payments import YookassaPayment
from unireax_main.utils.additional_function import *
from unireax_main.utils.certificate_generator import generate_certificate_number, generate_certificate_pdf
from unireax_main.utils.course_progress import check_course_completion



HAS_CUSTOM_FONT = False
try:
    font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial_black.ttf')
    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Arial-Black', font_path))
        HAS_CUSTOM_FONT = True
except:
    pass


def is_listener(user):
    """Проверка, является ли пользователь слушателем курсов"""
    return (user.is_authenticated and 
            user.role and 
            user.role.role_name.lower() == "слушатель курсов" and 
            user.is_verified)


def check_course_completion_after_test(user, course):
    """Проверяет завершение курса после прохождения теста и обновляет статус"""
    from unireax_main.utils.course_progress import check_course_completion, calculate_total_course_score
    
    completion_data = check_course_completion(user.id, course.id)
    
    if completion_data['completed']:
        try:
            user_course = UserCourse.objects.get(user=user, course=course)
            if not user_course.status_course:
                user_course.status_course = True
                user_course.completion_date = timezone.now().date()
                user_course.save()
                
                score_data = calculate_total_course_score(user.id, course.id)
                
                if score_data['with_honors']:
                    messages.success(user, 
                        f'Поздравляем! Вы успешно завершили курс "{course.course_name}" С ОТЛИЧИЕМ!\n'
                        f'Ваш результат: {score_data["total_earned"]} из {score_data["total_max"]} баллов ({score_data["percentage"]}%)')
                else:
                    messages.success(user, 
                        f'Поздравляем! Вы успешно завершили курс "{course.course_name}"!\n'
                        f'Ваш результат: {score_data["total_earned"]} из {score_data["total_max"]} баллов ({score_data["percentage"]}%)')
                return True
        except UserCourse.DoesNotExist:
            pass
    return False


@login_required
@user_passes_test(is_listener)
def listener_dashboard(request):
    """Дашборд слушателя"""
    user = request.user
    
    active_courses = UserCourse.objects.filter(
        user=user,
        is_active=True
    ).select_related('course').order_by('-enrolled_at')
    
    inactive_courses = UserCourse.objects.filter(
        user=user,
        is_active=False
    ).select_related('course').order_by('-enrolled_at')[:5]

    
    total_courses = active_courses.count()
    completed_courses = active_courses.filter(status_course=True).count()
    
    courses_with_progress = []
    for user_course in active_courses:
        progress = calculate_course_completion(user.id, user_course.course.id)
        courses_with_progress.append({
            'course': user_course.course,
            'progress': progress,
            'enrolled_at': user_course.enrolled_at
        })
    
    recommended = Course.objects.filter(
        is_active=True,
        is_completed=True
    ).annotate(
        student_count=Count('usercourse', filter=Q(usercourse__is_active=True))
    ).order_by('-student_count')[:6]
    
    context = {
        'active_courses': courses_with_progress,
        'inactive_courses': inactive_courses,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'recommended_courses': recommended,
    }
    
    return render(request, 'listener_dashboard.html', context)

@login_required
@user_passes_test(is_listener)
def create_payment(request, course_id):
    """Создание платежа через ЮKassa"""
    course = get_object_or_404(Course, id=course_id, is_active=True)
    user = request.user
    
    if UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'Вы уже записаны на этот курс')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    existing = UserCourse.objects.filter(user=user, course=course).first()
    if existing and not existing.is_active:
        messages.info(request, 'Вы уже были записаны на этот курс. Вы можете вернуться бесплатно.')
        return redirect('listener_app:return_to_course', course_id=course_id)
    
    if course.course_price <= 0:
        messages.error(request, 'Этот курс бесплатный')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    try:
        payment_processor = YookassaPayment()
        
        return_url = request.build_absolute_uri(
            reverse('listener_app:payment_success', kwargs={'course_id': course_id, 'payment_id': 'PAYMENT_ID'})
        )
        return_url = return_url.replace('PAYMENT_ID', '{payment_id}')
        
        payment = payment_processor.create_payment(course, user, return_url)
        
        request.session['yookassa_payment_id'] = payment.id
        request.session['payment_course_id'] = course_id
        
        return redirect(payment.confirmation.confirmation_url)
        
    except Exception as e:
        print(f"Payment error: {e}")
        messages.error(request, f'Ошибка при создании платежа: {str(e)}')
        return redirect('listener_app:course_detail', course_id=course_id)

@login_required
@user_passes_test(is_listener)
def listener_profile(request):
    """Профиль слушателя"""
    user = request.user
    
    if request.method == 'POST':
        if 'profile_update' in request.POST:
            user.first_name = request.POST.get('first_name', '')
            user.last_name = request.POST.get('last_name', '')
            user.patronymic = request.POST.get('patronymic', '')
            user.username = request.POST.get('username', '')
            user.email = request.POST.get('email', '')
            
            try:
                user.save()
                messages.success(request, 'Профиль успешно обновлен!')
                return redirect('listener_app:listener_profile')
            except Exception as e:
                messages.error(request, f'Ошибка при обновлении профиля: {str(e)}')
        
        elif 'password_change' in request.POST:
            old_password = request.POST.get('old_password')
            new_password1 = request.POST.get('new_password1')
            new_password2 = request.POST.get('new_password2')
            
            if user.check_password(old_password):
                if new_password1 == new_password2:
                    if len(new_password1) >= 8:
                        user.set_password(new_password1)
                        user.save()
                        update_session_auth_hash(request, user)
                        messages.success(request, 'Пароль успешно изменен!')
                        return redirect('listener_app:listener_profile')
                    else:
                        messages.error(request, 'Пароль должен содержать минимум 8 символов')
                else:
                    messages.error(request, 'Новые пароли не совпадают')
            else:
                messages.error(request, 'Неверный текущий пароль')
    
    total_courses = UserCourse.objects.filter(user=user, is_active=True).count()
    completed_courses = UserCourse.objects.filter(user=user, status_course=True).count()
    
    total_assignments = UserPracticalAssignment.objects.filter(user=user).count()
    graded_assignments = UserPracticalAssignment.objects.filter(
        user=user,
        submission_status__assignment_status_name='завершено'
    ).count()

    total_tests = Test.objects.filter(
        lecture__course__in=UserCourse.objects.filter(user=user, is_active=True).values('course'),
        is_active=True
    ).count()

    passed_tests = TestResult.objects.filter(user=user, is_passed=True).count()
    
    paid_courses = UserCourse.objects.filter(
        user=user,
        course_price__isnull=False,
        course_price__gt=0
    ).select_related('course').order_by('-payment_date', '-enrolled_at')
    
    total_spent = paid_courses.aggregate(total=Sum('course_price'))['total'] or 0
    
    payments_data = []
    for user_course in paid_courses:
        payment_id = user_course.payment_id
        if not payment_id or payment_id == '':
            date_str = user_course.enrolled_at.strftime('%Y%m%d') if user_course.enrolled_at else timezone.now().strftime('%Y%m%d')
            payment_id = f"MANUAL-{user_course.id}-{date_str}"
        payment_date = user_course.payment_date if user_course.payment_date else user_course.enrolled_at
        
        payments_data.append({
            'id': user_course.id,
            'course': user_course.course,
            'course_price': user_course.course_price,
            'payment_date': payment_date,
            'payment_id': payment_id,
            'enrolled_at': user_course.enrolled_at,
        })
    
    context = {
        'user': user,
        'total_courses': total_courses,
        'completed_courses': completed_courses,
        'total_assignments': total_assignments,
        'graded_assignments': graded_assignments,
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'paid_courses': payments_data,
        'total_spent': total_spent,
        'paid_courses_count': len(payments_data),
    }
    
    return render(request, 'listener_profile.html', context)


@login_required
@user_passes_test(is_listener)
def listener_deactivate_account(request):
    """Деактивация аккаунта слушателя"""
    if request.method == 'POST':
        password = request.POST.get('password')
        user = request.user
        
        if not user.check_password(password):
            messages.error(request, 'Неверный пароль')
            return redirect('listener_app:listener_profile')
        
        try:
            with transaction.atomic():
                UserCourse.objects.filter(user=user, is_active=True).update(
                    is_active=False,
                    status_course=False
                )
                FavoriteCourse.objects.filter(user=user).delete()
                pending_status = AssignmentStatus.objects.get(assignment_status_name='на проверке')
                UserPracticalAssignment.objects.filter(
                    user=user,
                    submission_status=pending_status
                ).update(
                    submission_status=AssignmentStatus.objects.get(assignment_status_name='отклонено')
                )
                
                Review.objects.filter(user=user).update(
                    comment_review="[Аккаунт удалён]",
                    is_approved=False
                )
                
                user.first_name = "Deleted"
                user.last_name = "User"
                user.patronymic = None
                user.username = f"deleted_{user.id}_{int(timezone.now().timestamp())}"
                user.email = f"deleted_{user.id}@deleted.unireax"
                user.is_active = False
                user.save()
                
                logout(request)
                
                messages.success(request, 'Ваш аккаунт успешно деактивирован')
                return redirect('main_page')
                
        except Exception as e:
            messages.error(request, f'Ошибка при деактивации: {str(e)}')
            return redirect('listener_app:listener_profile')
    
    return redirect('listener_app:listener_profile')

@login_required
@user_passes_test(is_listener)
def my_courses(request):
    """Все курсы слушателя"""
    user = request.user
    
    active_courses = UserCourse.objects.filter(
        user=user,
        is_active=True
    ).select_related('course').order_by('-enrolled_at')
    
    inactive_courses = UserCourse.objects.filter(
        user=user,
        is_active=False
    ).select_related('course').order_by('-enrolled_at')
    
    for user_course in active_courses:
        user_course.progress = calculate_course_completion(user.id, user_course.course.id)
    
    context = {
        'active_courses': active_courses,
        'inactive_courses': inactive_courses,
    }
    
    return render(request, 'my_courses.html', context)


@login_required
@user_passes_test(is_listener)
def listener_course_detail(request, course_id):
    """Редирект на общую страницу курса"""
    return redirect('course_detail', course_id=course_id)


@login_required
@user_passes_test(is_listener)
def course_study(request, course_id):
    """Страница изучения курса"""
    course = get_object_or_404(Course, id=course_id, is_active=True)
    user = request.user
    
    user_course = get_object_or_404(UserCourse, user=user, course=course, is_active=True)
    
    progress = calculate_course_completion(user.id, course.id)
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    
    practical_works = PracticalAssignment.objects.filter(
        lecture__course=course,
        is_active=True
    ).select_related('lecture').order_by('lecture__lecture_order')
    
    tests = Test.objects.filter(
        lecture__course=course,
        is_active=True
    ).select_related('lecture').order_by('lecture__lecture_order')
    
    user_assignments = {}
    for assignment in practical_works:
        user_assignment = UserPracticalAssignment.objects.filter(
            user=user,
            practical_assignment=assignment
        ).order_by('-attempt_number').first()
        
        if user_assignment:
            user_assignments[assignment.id] = {
                'status': user_assignment.submission_status.assignment_status_name,
                'attempt': user_assignment.attempt_number,
                'feedback_exists': Feedback.objects.filter(user_practical_assignment=user_assignment).exists()
            }
        else:
            user_assignments[assignment.id] = {'status': 'not_submitted', 'attempt': 0, 'feedback_exists': False}
    
    test_results = {}
    for test in tests:
        all_results = TestResult.objects.filter(user=user, test=test)
        
        best_result = None
        if test.grading_form == 'points':
            best_result = all_results.order_by('-final_score').first()
        else:
            passed_result = all_results.filter(is_passed=True).first()
            best_result = passed_result if passed_result else all_results.first()
        
        is_passed = False
        if best_result:
            if test.grading_form == 'points':
                is_passed = best_result.final_score >= (test.passing_score or 0) if best_result.final_score is not None else False
            else:
                is_passed = best_result.is_passed if best_result.is_passed is not None else False
        
        test_results[test.id] = {
            'passed': is_passed,
            'score': best_result.final_score if best_result and test.grading_form == 'points' else None,
            'attempt': best_result.attempt_number if best_result else None,
            'has_attempts': all_results.exists()
        }
    
    current_time = timezone.now()
    upcoming_deadlines = []
    
    for assignment in practical_works:
        if assignment.assignment_deadline and assignment.assignment_deadline > current_time:
            upcoming_deadlines.append({
                'type': 'practical',
                'id': assignment.id,
                'title': assignment.practical_assignment_name,
                'lecture': assignment.lecture.lecture_name,
                'deadline': assignment.assignment_deadline
            })
    
    upcoming_deadlines.sort(key=lambda x: x['deadline'])
    
    from unireax_main.utils.additional_function import calculate_certificate_eligibility
    from unireax_main.models import Certificate
    
    certificate_data = calculate_certificate_eligibility(user.id, course.id)
    course_has_certificate = course.has_certificate
    
    existing_certificate = None
    if user_course.status_course and course_has_certificate:
        try:
            existing_certificate = Certificate.objects.get(user_course=user_course)
        except Certificate.DoesNotExist:
            pass
    
    from unireax_main.models import CoursePost, CoursePostComment

    course_posts = CoursePost.objects.filter(
        course=course,
        is_active=True
    ).order_by('-is_pinned', '-created_at')
    
    posts_data = []
    for post in course_posts:
        comments = CoursePostComment.objects.filter(
            post=post,
            parent__isnull=True  
        ).select_related('author').order_by('created_at')
        
        comments_data = []
        for comment in comments:
            replies = CoursePostComment.objects.filter(
                parent=comment
            ).select_related('author').order_by('created_at')
            
            replies_data = []
            for reply in replies:
                replies_data.append({
                    'id': reply.id,
                    'content': reply.content,
                    'author_name': reply.author.get_full_name() or reply.author.username,
                    'created_at': reply.created_at.strftime('%d.%m.%Y %H:%M'),
                    'can_delete': reply.author == user or user.is_teacher_or_methodist
                })
            
            comments_data.append({
                'id': comment.id,
                'content': comment.content,
                'author_name': comment.author.get_full_name() or comment.author.username,
                'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
                'can_delete': comment.author == user or user.is_teacher_or_methodist,
                'replies': replies_data
            })
        
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'post_type': post.post_type,
            'post_type_display': post.get_post_type_display(),
            'is_pinned': post.is_pinned,
            'author_name': post.author.get_full_name() or post.author.username,
            'created_at': post.created_at.strftime('%d.%m.%Y %H:%M'),
            'comments': comments_data,
            'can_edit': post.author == user or user.is_teacher_or_methodist,
            'total_comments': CoursePostComment.objects.filter(post=post).count()
        })
    
    context = {
        'course': course,
        'progress': progress,
        'lectures': lectures,
        'practical_works': practical_works,
        'tests': tests,
        'user_assignments': user_assignments,
        'test_results': test_results,
        'upcoming_deadlines': upcoming_deadlines[:5],
        'current_time': current_time,
        'course_has_certificate': course_has_certificate,
        'certificate_data': certificate_data,
        'existing_certificate': existing_certificate,
        'course_posts': posts_data,
    }
    
    return render(request, 'course_study.html', context)


@login_required
@user_passes_test(is_listener)
def continue_course(request, course_id):
    """Продолжить обучение (редирект на последнюю непросмотренную лекцию)"""
    course = get_object_or_404(Course, id=course_id, is_active=True)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'Вы не записаны на этот курс')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    first_lecture = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order').first()
    
    if first_lecture:
        return redirect('listener_app:lecture_detail', lecture_id=first_lecture.id)
    
    return redirect('listener_app:course_study', course_id=course_id)


@login_required
@user_passes_test(is_listener)
def exit_course(request, course_id):
    """Выход из курса"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    try:
        user_course = UserCourse.objects.get(user=user, course=course, is_active=True)
        user_course.is_active = False
        user_course.save()
        
        messages.success(request, f'Вы вышли из курса "{course.course_name}". Ваш прогресс сохранен.')
        return redirect('listener_app:my_courses')
        
    except UserCourse.DoesNotExist:
        messages.error(request, 'Вы не записаны на этот курс')
        return redirect('listener_app:course_detail', course_id=course_id)


@login_required
@user_passes_test(is_listener)
def return_to_course(request, course_id):
    """Вернуться на курс (активировать заново) - для бесплатных курсов и возврата"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    user_course = UserCourse.objects.filter(user=user, course=course).first()
    
    if user_course:
        if not user_course.is_active:
            user_course.is_active = True
            user_course.save()
            messages.success(request, f'Вы успешно записаны на курс "{course.course_name}"!')
        else:
            messages.info(request, f'Вы уже записаны на курс "{course.course_name}".')
        return redirect('listener_app:course_study', course_id=course.id)
    else:
        user_course = UserCourse.objects.create(
            user=user,
            course=course,
            course_price=course.course_price or 0,
            status_course=False,
            is_active=True
        )
        messages.success(request, f'Вы успешно записаны на бесплатный курс "{course.course_name}"!')
        return redirect('listener_app:course_study', course_id=course.id)


@login_required
@user_passes_test(is_listener)
def lecture_detail(request, lecture_id):
    """Детальная страница лекции"""
    lecture = get_object_or_404(Lecture, id=lecture_id, is_active=True)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=lecture.course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этой лекции')
        return redirect('listener_app:course_detail', course_id=lecture.course.id)
    
    next_lecture = Lecture.objects.filter(
        course=lecture.course,
        lecture_order__gt=lecture.lecture_order,
        is_active=True
    ).order_by('lecture_order').first()
    
    prev_lecture = Lecture.objects.filter(
        course=lecture.course,
        lecture_order__lt=lecture.lecture_order,
        is_active=True
    ).order_by('-lecture_order').first()
    
    context = {
        'lecture': lecture,
        'next_lecture': next_lecture,
        'prev_lecture': prev_lecture,
    }
    
    return render(request, 'lecture_detail.html', context)


@login_required
@user_passes_test(is_listener)
def test_start(request, test_id):
    """Страница начала теста"""
    test = get_object_or_404(Test, id=test_id, is_active=True)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=test.lecture.course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому тесту')
        return redirect('listener_app:course_detail', course_id=test.lecture.course.id)
    
    attempts_count = TestResult.objects.filter(user=user, test=test).count()
    if test.max_attempts and attempts_count >= test.max_attempts:
        messages.error(request, 'Вы исчерпали все попытки для этого теста')
        return redirect('listener_app:course_study', course_id=test.lecture.course.id)
    
    questions = Question.objects.filter(test=test).select_related('answer_type').prefetch_related(
        'choiceoption_set', 'matchingpair_set'
    ).order_by('question_order')
    
    context = {
        'test': test,
        'questions': questions,
        'attempt_number': attempts_count + 1,
    }
    
    return render(request, 'test_start.html', context)


@login_required
@user_passes_test(is_listener)
def test_submit(request, test_id):
    """Обработка отправки теста - бэкенд сам вычисляет номер попытки по БД"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Метод не разрешен'})
    
    test = get_object_or_404(Test, id=test_id, is_active=True)
    user = request.user
    
    try:
        data = json.loads(request.body)
        answers = data.get('answers', {})
        
        if not UserCourse.objects.filter(user=user, course=test.lecture.course, is_active=True).exists():
            return JsonResponse({'success': False, 'error': 'Нет доступа к тесту'})
        
        existing_attempts = TestResult.objects.filter(user=user, test=test)
        next_attempt_number = existing_attempts.count() + 1
        
        if test.max_attempts and existing_attempts.count() >= test.max_attempts:
            return JsonResponse({'success': False, 'error': 'Исчерпаны все попытки'})

        total_score = save_test_answers(user, test, answers, next_attempt_number)
        max_score = calculate_test_max_score(test)
        if test.grading_form == 'points':
            is_passed = total_score >= (test.passing_score or 0)
            test_result = TestResult(
                user=user,
                test=test,
                attempt_number=next_attempt_number,
                final_score=total_score,
                is_passed=None,
                completion_date=timezone.now()
            )
        else:
            is_passed = total_score >= (max_score * 0.7) if max_score > 0 else False
            test_result = TestResult(
                user=user,
                test=test,
                attempt_number=next_attempt_number,
                final_score=None,
                is_passed=is_passed,
                completion_date=timezone.now()
            )
        
        test_result.save()
        
        check_course_completion_after_test(user, test.lecture.course)
        best_passed = test.is_passed_by_user(user)
        best_result = test.get_best_result_for_user(user)
        best_score = best_result.final_score if best_result and test.grading_form == 'points' else None
        
        return JsonResponse({
            'success': True,
            'score': total_score,
            'max_score': max_score,
            'passed': is_passed,
            'best_passed': best_passed,
            'best_score': best_score,
            'attempt_number': next_attempt_number,
            'total_attempts': next_attempt_number,
            'grading_form': test.grading_form,
            'passing_score': test.passing_score if test.grading_form == 'points' else None,
            'course_id': test.lecture.course.id
        })
        
    except json.JSONDecodeError as e:
        return JsonResponse({'success': False, 'error': f'Ошибка данных: {str(e)}'})
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'error': str(e)})


def save_test_answers(user, test, answers, attempt_number):
    """Сохраняет ответы пользователя и возвращает количество баллов"""
    total_score = 0
    questions = Question.objects.filter(test=test).select_related('answer_type').prefetch_related(
        'choiceoption_set', 'matchingpair_set'
    )
    
    for question in questions:
        question_id_str = str(question.id)
        if question_id_str not in answers:
            continue
        
        user_answer_data = answers[question_id_str]
        score = 0
        
        UserAnswer.objects.filter(
            user=user, 
            question=question, 
            attempt_number=attempt_number
        ).delete()
        
        user_answer = UserAnswer.objects.create(
            user=user,
            question=question,
            attempt_number=attempt_number,
            answer_text=None
        )
        
        answer_type = question.answer_type.answer_type_name.lower()
        
        if 'один ответ' in answer_type or 'single' in answer_type:
            score = check_single_choice(question, user_answer_data, user_answer)
            
        elif 'несколько ответов' in answer_type or 'multiple' in answer_type:
            score = check_multiple_choice(question, user_answer_data, user_answer)
            
        elif 'текст' in answer_type or 'text' in answer_type:
            score = check_text_answer(question, user_answer_data, user_answer)
            
        elif 'сопоставление' in answer_type or 'matching' in answer_type:
            score = check_matching_answer(question, user_answer_data, user_answer)
            
        else:
            if question.choiceoption_set.exists():
                score = check_single_choice(question, user_answer_data, user_answer)
            else:
                score = 0
        
        user_answer.score = score
        user_answer.save()
        total_score += score
        
        print(f"Question {question.id}: score={score}, total={total_score}")
    
    return total_score


def check_single_choice(question, user_answer, user_answer_obj):
    """Проверка одиночного выбора"""
    try:
        selected_option_id = int(user_answer)
        correct_option = question.choiceoption_set.filter(is_correct=True).first()
        
        if correct_option and correct_option.id == selected_option_id:
            UserSelectedChoice.objects.create(
                user_answer=user_answer_obj,
                choice_option_id=selected_option_id
            )
            return question.question_score
    except (ValueError, TypeError):
        pass
    return 0


def check_multiple_choice(question, user_answer, user_answer_obj):
    """Проверка множественного выбора"""
    try:
        if not isinstance(user_answer, list):
            return 0
        
        selected_option_ids = [int(opt_id) for opt_id in user_answer]
        correct_options = set(question.choiceoption_set.filter(is_correct=True).values_list('id', flat=True))
        user_options = set(selected_option_ids)
        
        for option_id in selected_option_ids:
            UserSelectedChoice.objects.create(
                user_answer=user_answer_obj,
                choice_option_id=option_id
            )
        
        if correct_options == user_options:
            return question.question_score
    except (ValueError, TypeError):
        pass
    return 0


def check_text_answer(question, user_answer, user_answer_obj):
    """Проверка текстового ответа"""
    if user_answer and len(str(user_answer).strip()) > 0:
        user_answer_obj.answer_text = str(user_answer)
        user_answer_obj.save()
        return question.question_score
    return 0


def check_matching_answer(question, user_answer, user_answer_obj):
    """Проверка сопоставлений"""
    if not isinstance(user_answer, dict):
        return 0
    
    UserMatchingAnswer.objects.filter(user_answer=user_answer_obj).delete()
    
    correct_count = 0
    total_pairs = question.matchingpair_set.count()
    
    if total_pairs == 0:
        return 0
    
    for field_name, selected_right_text in user_answer.items():
        try:
            pair_id = int(field_name.split('_')[-1])
            pair = question.matchingpair_set.get(id=pair_id)
            
            UserMatchingAnswer.objects.create(
                user_answer=user_answer_obj,
                matching_pair=pair,
                user_selected_right_text=selected_right_text
            )
            
            if selected_right_text.strip() == pair.right_text.strip():
                correct_count += 1
                
        except (ValueError, MatchingPair.DoesNotExist, IndexError):
            continue

    if total_pairs > 0:
        score = int((correct_count / total_pairs) * question.question_score)
    else:
        score = 0
    
    return score


def calculate_test_max_score(test):
    """Подсчет максимального балла за тест"""
    result = Question.objects.filter(test=test).aggregate(total=Sum('question_score'))
    return result['total'] or 0


@login_required
@user_passes_test(is_listener)
def test_result_detail(request, result_id):
    """Детальный просмотр конкретного результата теста с ответами"""
    result = get_object_or_404(TestResult, id=result_id)
    test = result.test
    user = request.user
    
    if result.user != user:
        messages.error(request, 'У вас нет доступа к этому результату')
        return redirect('listener_app:test_results_list', course_id=test.lecture.course.id)
    
    questions = Question.objects.filter(test=test).select_related('answer_type').prefetch_related(
        'choiceoption_set', 'matchingpair_set'
    ).order_by('question_order')
    
    user_answers = UserAnswer.objects.filter(
        user=user,
        question__test=test,
        attempt_number=result.attempt_number
    ).select_related('question', 'question__answer_type')
    
    answers_dict = {}
    for ua in user_answers:
        answers_dict[ua.question_id] = ua
    
    questions_data = []
    for question in questions:
        user_answer = answers_dict.get(question.id)
        
        selected_choices = []
        if user_answer:
            selected_choices = UserSelectedChoice.objects.filter(
                user_answer=user_answer
            ).values_list('choice_option_id', flat=True)
        
        correct_choices = list(question.choiceoption_set.filter(is_correct=True).values_list('id', flat=True))
        
        matching_answers = {}
        if user_answer and question.answer_type.answer_type_name == 'matching':
            matching_pairs = UserMatchingAnswer.objects.filter(user_answer=user_answer)
            for pair in matching_pairs:
                matching_answers[pair.matching_pair_id] = pair.user_selected_right_text
        
        correct_matching = {}
        for pair in question.matchingpair_set.all():
            correct_matching[pair.id] = pair.right_text
        
        is_correct = False
        if user_answer and user_answer.score and user_answer.score > 0:
            is_correct = user_answer.score == question.question_score
        elif user_answer and user_answer.score == 0:
            is_correct = False
        
        questions_data.append({
            'question': question,
            'user_answer': user_answer,
            'selected_choices': selected_choices,
            'correct_choices': correct_choices,
            'matching_answers': matching_answers,
            'correct_matching': correct_matching,
            'is_correct': is_correct,
            'earned_score': user_answer.score if user_answer else 0,
            'max_score': question.question_score
        })
    
    total_score = sum(q['earned_score'] for q in questions_data)
    max_total_score = sum(q['max_score'] for q in questions_data)
    
    if test.grading_form == 'points':
        is_passed = total_score >= (test.passing_score or 0)
    else:
        is_passed = result.is_passed if result.is_passed is not None else False
    
    context = {
        'result': result,
        'test': test,
        'course': test.lecture.course,
        'questions_data': questions_data,
        'total_score': total_score,
        'max_total_score': max_total_score,
        'is_passed': is_passed,
    }
    
    return render(request, 'test_result_detail.html', context)


@login_required
@user_passes_test(is_listener)
def test_results_list(request, course_id):
    """Список всех тестов курса с краткими результатами (лучшие попытки)"""
    course = get_object_or_404(Course, id=course_id, is_active=True)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    tests = Test.objects.filter(lecture__course=course, is_active=True).select_related('lecture').order_by('lecture__lecture_order')
    
    tests_data = []
    total_passed = 0
    
    for test in tests:
        is_passed = test.is_passed_by_user(user)
        best_result = test.get_best_result_for_user(user)
        
        max_score = test.question_set.aggregate(total=Sum('question_score'))['total'] or 0
        
        if is_passed:
            total_passed += 1
        
        tests_data.append({
            'test': test,
            'best_result': best_result,
            'max_score': max_score,
            'attempts_count': TestResult.objects.filter(user=user, test=test).count(),
            'is_passed': is_passed,
            'has_results': TestResult.objects.filter(user=user, test=test).exists()
        })
    
    total_tests = len(tests)
    success_rate = round((total_passed / total_tests) * 100, 1) if total_tests > 0 else 0
    
    context = {
        'course': course,
        'tests_data': tests_data,
        'total_tests': total_tests,
        'total_passed': total_passed,
        'success_rate': success_rate,
    }
    
    return render(request, 'all_test_results.html', context)

@login_required
@user_passes_test(is_listener)
def practical_submit(request, assignment_id):
    """Страница сдачи практической работы"""
    assignment = get_object_or_404(PracticalAssignment, id=assignment_id, is_active=True)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=assignment.lecture.course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому заданию')
        return redirect('listener_app:course_detail', course_id=assignment.lecture.course.id)
    
    is_overdue = assignment.assignment_deadline and assignment.assignment_deadline < timezone.now()
    if is_overdue and not assignment.is_can_pin_after_deadline:
        messages.error(request, 'Срок сдачи этого задания истек')
        return redirect('listener_app:course_study', course_id=assignment.lecture.course.id)
    
    user_assignment = UserPracticalAssignment.objects.filter(
        user=user,
        practical_assignment=assignment
    ).order_by('-attempt_number').first()
    
    feedback = None
    if user_assignment:
        try:
            feedback = Feedback.objects.get(user_practical_assignment=user_assignment)
        except Feedback.DoesNotExist:
            pass
    
    if request.method == 'POST':
        submitted_files = request.FILES.getlist('submission_files')
        comment = request.POST.get('comment', '')
        
        if not submitted_files:
            messages.error(request, 'Пожалуйста, прикрепите хотя бы один файл')
            return redirect('listener_app:practical_submit', assignment_id=assignment_id)
        
        try:
            attempt_number = user_assignment.attempt_number + 1 if user_assignment else 1
            
            checking_status = get_object_or_404(AssignmentStatus, assignment_status_name='на проверке')
            
            new_assignment = UserPracticalAssignment.objects.create(
                user=user,
                practical_assignment=assignment,
                submission_date=timezone.now(),
                submission_status=checking_status,
                attempt_number=attempt_number,
                comment=comment
            )
            
            for uploaded_file in submitted_files:
                if uploaded_file.size > 50 * 1024 * 1024:
                    messages.error(request, f'Файл {uploaded_file.name} слишком большой. Максимум 50 МБ')
                    new_assignment.delete()
                    return redirect('listener_app:practical_submit', assignment_id=assignment_id)
                
                AssignmentSubmissionFile.objects.create(
                    user_assignment=new_assignment,
                    file=uploaded_file,
                    file_name=uploaded_file.name,
                    file_size=uploaded_file.size
                )
            
            messages.success(request, 'Работа успешно отправлена на проверку!')
            return redirect('listener_app:course_study', course_id=assignment.lecture.course.id)
            
        except Exception as e:
            messages.error(request, f'Ошибка при отправке: {str(e)}')
    
    context = {
        'assignment': assignment,
        'user_assignment': user_assignment,
        'feedback': feedback,
        'is_overdue': is_overdue,
        'current_time': timezone.now(),
    }
    
    return render(request, 'practical_submit.html', context)


@login_required
@user_passes_test(is_listener)
def graded_assignments(request, course_id):
    """Оцененные работы слушателя"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    completed_status = get_object_or_404(AssignmentStatus, assignment_status_name='завершено')
    
    user_assignments = UserPracticalAssignment.objects.filter(
        user=user,
        practical_assignment__lecture__course=course,
        submission_status=completed_status
    ).select_related('practical_assignment', 'practical_assignment__lecture', 'submission_status')
    
    graded_list = []
    for assignment in user_assignments:
        try:
            feedback = Feedback.objects.get(user_practical_assignment=assignment)
            graded_list.append({
                'assignment': assignment,
                'feedback': feedback,
                'practical': assignment.practical_assignment
            })
        except Feedback.DoesNotExist:
            continue
    
    graded_list.sort(key=lambda x: x['assignment'].submission_date or timezone.now(), reverse=True)
    
    context = {
        'course': course,
        'graded_assignments': graded_list,
    }
    
    return render(request, 'graded_assignments.html', context)

@login_required
@user_passes_test(is_listener)
def student_statistics(request, course_id):
    """Статистика слушателя по курсу"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    progress = calculate_course_completion(user.id, course.id)
    
    tests = Test.objects.filter(lecture__course=course, is_active=True)
    total_tests = tests.count()
    passed_tests = 0
    test_scores = []
    
    for test in tests:
        if test.is_passed_by_user(user):
            passed_tests += 1

        if test.grading_form == 'points':
            best_result = test.get_best_result_for_user(user)
            if best_result and best_result.final_score is not None:
                test_scores.append(best_result.final_score)
    
    avg_test_score = sum(test_scores) / len(test_scores) if test_scores else 0

    practicals = PracticalAssignment.objects.filter(lecture__course=course, is_active=True)
    total_practicals = practicals.count()
    completed_practicals = 0
    practical_scores = []
    
    for practical in practicals:
        user_assignments = UserPracticalAssignment.objects.filter(
            user=user,
            practical_assignment=practical
        ).order_by('-attempt_number')
        
        found_completed = False
        best_score_for_this = None
        
        for assignment in user_assignments:
            try:
                feedback = Feedback.objects.get(user_practical_assignment=assignment)
                
                if practical.grading_type == 'points':
                    if feedback.score is not None:
                        if best_score_for_this is None or feedback.score > best_score_for_this:
                            best_score_for_this = feedback.score
                        
                        passing_score = practical.passing_score or (practical.max_score * 0.6 if practical.max_score else 0)
                        if feedback.score >= passing_score:
                            found_completed = True
                            break
                else:
                    if feedback.is_passed:
                        found_completed = True
                        break
                        
            except Feedback.DoesNotExist:
                continue
        
        if found_completed:
            completed_practicals += 1
            if best_score_for_this is not None:
                practical_scores.append(best_score_for_this)
    
    avg_practical_score = sum(practical_scores) / len(practical_scores) if practical_scores else 0
    
    context = {
        'course': course,
        'progress': progress,
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'total_practicals': total_practicals,
        'completed_practicals': completed_practicals,
        'avg_test_score': avg_test_score,
        'avg_practical_score': avg_practical_score,
        'test_results_count': TestResult.objects.filter(user=user, test__lecture__course=course).count(),
    }
    
    return render(request, 'student_statistics.html', context)

@login_required
@user_passes_test(is_listener)
def my_certificates(request):
    """Страница со всеми сертификатами пользователя"""
    user_courses = UserCourse.objects.filter(user=request.user, is_active=True)
    certificates = Certificate.objects.filter(
        user_course__in=user_courses
    ).select_related('user_course', 'user_course__course')
    
    eligible_courses = []
    for user_course in user_courses:
        if (user_course.course.has_certificate and 
            user_course.status_course and
            not Certificate.objects.filter(user_course=user_course).exists()):
            
            progress = calculate_course_completion(request.user.id, user_course.course.id)
            if progress >= 100:
                eligible_courses.append({
                    'course': user_course.course,
                    'user_course': user_course,
                    'progress': progress
                })
    
    context = {
        'certificates': certificates,
        'eligible_courses': eligible_courses,
    }
    
    return render(request, 'my_certificates.html', context)


@login_required
@user_passes_test(is_listener)
def certificate_detail(request, certificate_id):
    """Страница просмотра сертификата"""
    certificate = get_object_or_404(Certificate, id=certificate_id)
    
    if certificate.user_course.user != request.user:
        messages.error(request, 'У вас нет доступа к этому сертификату')
        return redirect('listener_app:my_certificates')
    
    from unireax_main.utils.certificate_generator import calculate_total_course_score
    score_data = calculate_total_course_score(request.user.id, certificate.user_course.course.id)
    show_regenerate_button = True
    
    context = {
        'certificate': certificate,
        'score_data': score_data,
        'show_regenerate_button': show_regenerate_button,
    }
    
    return render(request, 'certificate_detail.html', context)

@login_required
@user_passes_test(is_listener)
def download_certificate(request, certificate_id):
    """Скачивание сертификата"""
    certificate = get_object_or_404(Certificate, id=certificate_id)
    
    if certificate.user_course.user != request.user:
        messages.error(request, 'У вас нет доступа к этому сертификату')
        return redirect('listener_app:my_certificates')
    
    if not certificate.certificate_file_path:
        try:
            pdf_path = generate_certificate_pdf(certificate)
            certificate.certificate_file_path = pdf_path
            certificate.save()
        except Exception as e:
            messages.error(request, f'Ошибка при генерации сертификата: {str(e)}')
            return redirect('listener_app:certificate_detail', certificate_id=certificate_id)
    
    file_path = os.path.join(settings.MEDIA_ROOT, certificate.certificate_file_path)
    if os.path.exists(file_path):
        with open(file_path, 'rb') as fh:
            response = HttpResponse(fh.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="certificate_{certificate.certificate_number}.pdf"'
            return response
    else:
        messages.error(request, 'Файл сертификата не найден')
        return redirect('listener_app:certificate_detail', certificate_id=certificate_id)


@login_required
@user_passes_test(is_listener)
def check_certificate_eligibility(request, course_id):
    """Проверка возможности получения сертификата"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        return JsonResponse({'eligible': False, 'error': 'Вы не записаны на этот курс'})
    
    progress = calculate_course_completion(user.id, course.id)
    user_course = UserCourse.objects.get(user=user, course=course)
    existing_certificate = Certificate.objects.filter(user_course=user_course).first()
    
    eligible = (progress >= 100 and course.has_certificate and user_course.status_course and not existing_certificate)
    
    return JsonResponse({
        'eligible': eligible,
        'progress': progress,
        'has_certificate': existing_certificate is not None,
        'course_has_certificate': course.has_certificate,
        'course_completed': user_course.status_course
    })


@login_required
@user_passes_test(is_listener)
def generate_certificate(request, course_id):
    """Генерация сертификата"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'Вы не записаны на этот курс')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    progress = calculate_course_completion(user.id, course.id)
    user_course = UserCourse.objects.get(user=user, course=course)
    
    if progress < 100:
        messages.error(request, f'Необходимо завершить курс на 100% (текущий прогресс: {progress}%)')
        return redirect('listener_app:course_study', course_id=course_id)
    
    if not course.has_certificate:
        messages.error(request, 'Для этого курса не предусмотрены сертификаты')
        return redirect('listener_app:course_study', course_id=course_id)
    
    if not user_course.status_course:
        messages.error(request, 'Курс не завершен')
        return redirect('listener_app:course_study', course_id=course_id)
    
    existing = Certificate.objects.filter(user_course=user_course).first()
    if existing:
        messages.info(request, 'Сертификат уже выдан')
        return redirect('listener_app:certificate_detail', certificate_id=existing.id)
    
    try:
        certificate = Certificate.objects.create(
            user_course=user_course,
            issue_date=timezone.now().date(),
            certificate_number=generate_certificate_number()
        )
        
        pdf_path = generate_certificate_pdf(certificate)
        certificate.certificate_file_path = pdf_path
        certificate.save()
        
        messages.success(request, 'Сертификат успешно сгенерирован!')
        return redirect('listener_app:certificate_detail', certificate_id=certificate.id)
        
    except Exception as e:
        messages.error(request, f'Ошибка при генерации сертификата: {str(e)}')
        return redirect('listener_app:course_study', course_id=course_id)


@login_required
@user_passes_test(is_listener)
def course_progress(request, course_id):
    """Детальный прогресс по курсу"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'У вас нет доступа к этому курсу')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    completion_data = check_course_completion(user.id, course.id)
    
    lectures = Lecture.objects.filter(course=course, is_active=True).order_by('lecture_order')
    
    lectures_progress = []
    for lecture in lectures:
        assignments = PracticalAssignment.objects.filter(lecture=lecture, is_active=True)
        assignments_data = []
        assignments_completed = 0
        
        for assignment in assignments:
            user_assignments = UserPracticalAssignment.objects.filter(
                user=user,
                practical_assignment=assignment
            ).order_by('-attempt_number')
            
            is_completed = False

            for user_assignment in user_assignments:
                if user_assignment.submission_status.assignment_status_name == 'завершено':
                    is_completed = True
                    break
                else:
                    try:
                        feedback = Feedback.objects.get(user_practical_assignment=user_assignment)
                        if assignment.grading_type == 'points':
                            passing_score = assignment.passing_score or (assignment.max_score * 0.6 if assignment.max_score else 0)
                            if feedback.score and feedback.score >= passing_score:
                                is_completed = True
                                break
                        else:
                            if feedback.is_passed:
                                is_completed = True
                                break
                    except Feedback.DoesNotExist:
                        continue
            
            assignments_data.append({
                'id': assignment.id,
                'name': assignment.practical_assignment_name,
                'is_completed': is_completed
            })
            if is_completed:
                assignments_completed += 1
        
        tests = Test.objects.filter(lecture=lecture, is_active=True)
        tests_data = []
        tests_passed = 0
        
        for test in tests:
            is_passed = test.is_passed_by_user(user)
            
            tests_data.append({
                'id': test.id,
                'name': test.test_name,
                'is_passed': is_passed
            })
            if is_passed:
                tests_passed += 1
        
        total_items = len(assignments) + len(tests)
        completed_items = assignments_completed + tests_passed
        lecture_progress = (completed_items / total_items * 100) if total_items > 0 else 100
        
        lectures_progress.append({
            'lecture': lecture,
            'assignments': assignments_data,
            'tests': tests_data,
            'progress': round(lecture_progress, 1),
            'assignments_completed': assignments_completed,
            'tests_passed': tests_passed,
            'total_assignments': len(assignments),
            'total_tests': len(tests)
        })
    
    context = {
        'course': course,
        'completion_data': completion_data,
        'lectures_progress': lectures_progress,
    }
    
    return render(request, 'course_progress.html', context)


@login_required
@user_passes_test(is_listener)
def add_review(request, course_id):
    """Добавление отзыва на курс"""
    if request.method != 'POST':
        return redirect('listener_app:course_detail', course_id=course_id)
    
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if not UserCourse.objects.filter(user=user, course=course, is_active=True).exists():
        messages.error(request, 'Вы не записаны на этот курс')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    if Review.objects.filter(user=user, course=course).exists():
        messages.error(request, 'Вы уже оставляли отзыв на этот курс')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    rating = request.POST.get('rating')
    comment = request.POST.get('comment', '')
    
    if not rating:
        messages.error(request, 'Пожалуйста, поставьте оценку')
        return redirect('listener_app:course_detail', course_id=course_id)
    
    try:
        review = Review.objects.create(
            course=course,
            user=user,
            rating=int(rating),
            comment_review=comment,
            publish_date=timezone.now(),
            is_approved=True
        )
        messages.success(request, 'Ваш отзыв успешно опубликован!')
    except Exception as e:
        messages.error(request, f'Ошибка при добавлении отзыва: {str(e)}')
    
    return redirect('listener_app:course_detail', course_id=course_id)


@login_required
@user_passes_test(is_listener)
def payment_success(request, course_id, payment_id):
    """Страница успешной оплаты"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    session_payment_id = request.session.get('yookassa_payment_id')
    
    if session_payment_id:
        try:
            payment_processor = YookassaPayment()
            payment_status = payment_processor.check_payment_status(session_payment_id)
            
            if payment_status == 'succeeded':
                success = payment_processor.process_successful_payment(session_payment_id)
                
                if success:
                    user_course = UserCourse.objects.get(user=user, course=course)
                    
                    if 'yookassa_payment_id' in request.session:
                        del request.session['yookassa_payment_id']
                    if 'payment_course_id' in request.session:
                        del request.session['payment_course_id']
                    
                    return render(request, 'payment_success.html', {
                        'course': course,
                        'payment_id': session_payment_id,
                        'user_course': user_course
                    })
                else:
                    messages.error(request, 'Ошибка при записи на курс после оплаты.')
            else:
                messages.warning(request, f'Статус платежа: {payment_status}')
                
        except Exception as e:
            messages.error(request, f'Ошибка при подтверждении платежа: {str(e)}')
    
    return redirect('listener_app:course_detail', course_id=course_id)


def register_pdf_fonts():
    """регистрация шрифтов для PDF с поддержкой кириллицы"""
    fonts_loaded = False
    
    regular_font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial.ttf')
    bold_font_path = os.path.join(settings.BASE_DIR, 'static', 'fonts', 'arial_black.ttf')
    
    if os.path.exists(regular_font_path):
        try:
            pdfmetrics.registerFont(TTFont('Arial', regular_font_path))
            fonts_loaded = True
        except Exception as e:
            print(f"Error registering regular font: {e}")
    
    if os.path.exists(bold_font_path):
        try:
            pdfmetrics.registerFont(TTFont('Arial-Bold', bold_font_path))
            fonts_loaded = True
        except Exception as e:
            print(f"Error registering bold font: {e}")
    
    return fonts_loaded

PDF_FONTS_LOADED = register_pdf_fonts()

def get_pdf_font(is_bold=False):
    """Получение имени шрифта для PDF"""
    if PDF_FONTS_LOADED:
        return 'Arial-Bold' if is_bold else 'Arial'
    else:
        return 'Helvetica-Bold' if is_bold else 'Helvetica'


@login_required
@user_passes_test(is_listener)
def download_receipt(request, course_id, payment_id):
    """Скачивание чека об оплате в формате PDF (красивый дизайн)"""
    course = get_object_or_404(Course, id=course_id)
    user = request.user
    
    if payment_id == '{payment_id}' or payment_id.startswith('{'):
        user_course = UserCourse.objects.filter(user=user, course=course, payment_id__startswith='test_').first()
        if user_course:
            payment_id = user_course.payment_id
        else:
            messages.error(request, 'Чек не найден')
            return redirect('listener_app:course_detail', course_id=course_id)
    else:
        user_course = get_object_or_404(
            UserCourse,
            user=user,
            course=course,
            payment_id=payment_id
        )
    
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="receipt_{payment_id}.pdf"'
    
    doc = SimpleDocTemplate(
        response,
        pagesize=A4,
        topMargin=25*mm,
        bottomMargin=25*mm,
        leftMargin=25*mm,
        rightMargin=25*mm
    )
    
    elements = []
    
    font_regular = get_pdf_font(is_bold=False)
    font_bold = get_pdf_font(is_bold=True)
    
    styles = getSampleStyleSheet()
    
    styles.add(ParagraphStyle(
        name='LogoTitle',
        fontName=font_bold,
        fontSize=32,
        textColor=colors.white,
        alignment=1,
        spaceAfter=5
    ))
    
    styles.add(ParagraphStyle(
        name='LogoSubtitle',
        fontName=font_regular,
        fontSize=14,
        textColor=colors.white,
        alignment=1,
        spaceAfter=0
    ))
    
    styles.add(ParagraphStyle(
        name='ReceiptTitle',
        fontName=font_bold,
        fontSize=22,
        textColor=HexColor('#151D49'),
        alignment=1,
        spaceAfter=25
    ))
    
    styles.add(ParagraphStyle(
        name='SectionTitle',
        fontName=font_bold,
        fontSize=14,
        textColor=HexColor('#5864F1'),
        spaceAfter=12,
        leftIndent=0
    ))
    
    styles.add(ParagraphStyle(
        name='LabelText',
        fontName=font_bold,
        fontSize=10,
        textColor=HexColor('#555555'),
    ))
    
    styles.add(ParagraphStyle(
        name='ValueText',
        fontName=font_regular,
        fontSize=10,
        textColor=HexColor('#333333'),
    ))
    
    styles.add(ParagraphStyle(
        name='TotalLabel',
        fontName=font_bold,
        fontSize=14,
        textColor=HexColor('#7B7FD5'),
    ))
    
    styles.add(ParagraphStyle(
        name='TotalValue',
        fontName=font_bold,
        fontSize=18,
        textColor=HexColor('#151D49'),
    ))
    
    styles.add(ParagraphStyle(
        name='FooterText',
        fontName=font_regular,
        fontSize=9,
        textColor=HexColor('#999999'),
        alignment=1
    ))
    
    page_width = A4[0] - 50*mm
    col1_width = 80*mm
    col2_width = page_width - col1_width
    
    header_bg = Table([[Paragraph("UNIREAX", styles['LogoTitle'])]], colWidths=[page_width])
    header_bg.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#7B7FD5')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 30),   
        ('BOTTOMPADDING', (0, 0), (-1, -1), 35),   
    ]))
    elements.append(header_bg)
    
    header_sub = Table([[Paragraph("Образовательная платформа", styles['LogoSubtitle'])]], colWidths=[page_width])
    header_sub.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#7B7FD5')),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),      
        ('BOTTOMPADDING', (0, 0), (-1, -1), 30),   
    ]))
    elements.append(header_sub)
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph("ЧЕК ОБ ОПЛАТЕ КУРСА", styles['ReceiptTitle']))
    
    section_header = Table([[Paragraph("Информация о платеже", styles['SectionTitle'])]], colWidths=[page_width])
    section_header.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8F9FF')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(section_header)
    
    from datetime import timedelta
    payment_date_local = user_course.payment_date + timedelta(hours=3)
    formatted_date = payment_date_local.strftime('%d.%m.%Y %H:%M')
    
    payment_data = [
        ["Номер платежа:", str(payment_id)],
        ["Дата оплаты:", formatted_date],
        ["Статус:", "Оплачено"],
    ]
    
    for label, value in payment_data:
        row = Table([[Paragraph(label, styles['LabelText']), Paragraph(value, styles['ValueText'])]], colWidths=[col1_width, col2_width])
        row.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8F9FF')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(row)
    elements.append(Spacer(1, 10))
    
    section_header2 = Table([[Paragraph("Информация о курсе", styles['SectionTitle'])]], colWidths=[page_width])
    section_header2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8F9FF')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(section_header2)
    
    course_data = [
        ["Название курса:", course.course_name],
        ["Сумма (в рублях):", f"{course.course_price}"],
    ]
    
    for label, value in course_data:
        row = Table([[Paragraph(label, styles['LabelText']), Paragraph(value, styles['ValueText'])]], colWidths=[col1_width, col2_width])
        row.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8F9FF')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(row)
    elements.append(Spacer(1, 10))
    
    section_header3 = Table([[Paragraph("Информация о пользователе", styles['SectionTitle'])]], colWidths=[page_width])
    section_header3.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8F9FF')),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(section_header3)
    
    user_data = [
        ["ФИО:", user.get_full_name() or user.username],
        ["Email:", user.email],
    ]
    
    for label, value in user_data:
        row = Table([[Paragraph(label, styles['LabelText']), Paragraph(value, styles['ValueText'])]], colWidths=[col1_width, col2_width])
        row.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), HexColor('#F8F9FF')),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('LEFTPADDING', (0, 0), (-1, -1), 12),
            ('RIGHTPADDING', (0, 0), (-1, -1), 12),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(row)
    elements.append(Spacer(1, 20))
    
    total_data = [[
        Paragraph("Итоговая сумма (в рублях):", styles['TotalLabel']),
        Paragraph(f"{course.course_price}", styles['TotalValue'])
    ]]
    total_row = Table(total_data, colWidths=[col1_width + 40*mm, col2_width - 40*mm])
    total_row.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ('TOPPADDING', (0, 0), (-1, -1), 15),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 15),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(total_row)
    elements.append(Spacer(1, 30))
    
    receipt_number = f"ЧК-{user_course.payment_date.strftime('%Y%m%d')}-{str(payment_id)[-8:].upper()}"
    
    footer_line = Table([[Paragraph("_" * 80, styles['FooterText'])]], colWidths=[page_width])
    footer_line.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(footer_line)
    
    footer_number = Table([[Paragraph(f"Чек №{receipt_number}", styles['FooterText'])]], colWidths=[page_width])
    footer_number.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(footer_number)
    
    footer_auto = Table([[Paragraph("Документ сгенерирован автоматически", styles['FooterText'])]], colWidths=[page_width])
    footer_auto.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    elements.append(footer_auto)
    
    doc.build(elements)
    
    return response

@login_required
@user_passes_test(is_listener)
def payment_cancel(request, course_id):
    """Страница отмены оплаты"""
    messages.info(request, 'Оплата отменена')
    return redirect('listener_app:course_detail', course_id=course_id)


@login_required
@user_passes_test(is_listener)
def edit_review(request, course_id, review_id):
    """Редактирование отзыва"""
    course = get_object_or_404(Course, id=course_id)
    review = get_object_or_404(Review, id=review_id, course=course, user=request.user)
    
    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment', '')
        
        if rating:
            review.rating = int(rating)
            review.comment_review = comment
            review.publish_date = timezone.now()
            review.save()
            messages.success(request, 'Ваш отзыв успешно обновлен!')
        else:
            messages.error(request, 'Пожалуйста, поставьте оценку')
        
        return redirect('listener_app:course_detail', course_id=course.id)
    
    return redirect('listener_app:course_detail', course_id=course.id)


@login_required
@user_passes_test(is_listener)
def delete_review(request, course_id, review_id):
    """Удаление отзыва"""
    course = get_object_or_404(Course, id=course_id)
    review = get_object_or_404(Review, id=review_id, course=course, user=request.user)
    
    if request.method == 'POST':
        review.delete()
        messages.success(request, 'Ваш отзыв успешно удален!')
    
    return redirect('listener_app:course_detail', course_id=course.id)


@login_required
def toggle_favorite(request, course_id):
    """
    Добавление/удаление курса в избранное (переключатель)
    """
    course = get_object_or_404(Course, id=course_id, is_active=True)
    
    favorite = FavoriteCourse.objects.filter(user=request.user, course=course).first()
    
    if favorite:
        favorite.delete()
        messages.success(request, f'Курс "{course.course_name}" удалён из избранного')
    else:
        FavoriteCourse.objects.create(user=request.user, course=course)
        messages.success(request, f'Курс "{course.course_name}" добавлен в избранное')
    next_url = request.META.get('HTTP_REFERER', reverse('listener_app:course_detail', args=[course_id]))
    return redirect(next_url)


@login_required
def favorite_courses(request):
    """
    Страница избранных курсов пользователя
    """
    from django.db.models import Avg, Count, Q
    favorites = FavoriteCourse.objects.filter(
        user=request.user,
        course__is_active=True
    ).select_related('course').order_by('-added_at')
    
    course_ids = favorites.values_list('course_id', flat=True)
    courses_with_stats = Course.objects.filter(
        id__in=course_ids,
        is_active=True
    ).annotate(
        avg_rating=Avg('review__rating', filter=Q(review__is_approved=True)),
        student_count=Count('usercourse', filter=Q(usercourse__is_active=True))
    )

    courses_dict = {course.id: course for course in courses_with_stats}
    favorite_items = []
    for fav in favorites:
        course = courses_dict.get(fav.course_id)
        if course:
            favorite_items.append({
                'id': fav.id,
                'course': course,
                'added_at': fav.added_at,
                'avg_rating': course.avg_rating or 0,
                'student_count': course.student_count or 0
            })
    
    context = {
        'favorites': favorite_items,
        'title': 'Избранные курсы',
        'favorites_count': len(favorite_items)
    }
    
    return render(request, 'favorite_courses.html', context)

@login_required
@require_POST
def remove_favorite(request, favorite_id):
    """
    Удаление курса из избранного (с POST запросом)
    """
    favorite = get_object_or_404(FavoriteCourse, id=favorite_id, user=request.user)
    course_name = favorite.course.course_name
    favorite.delete()
    
    messages.success(request, f'Курс "{course_name}" удалён из избранного')
    return redirect('listener_app:favorite_courses')

@login_required
def check_favorite_status(request, course_id):
    """
    AJAX функция для проверки статуса избранного (для динамических обновлений)
    Возвращает JSON: {'is_favorited': True/False}
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        course = get_object_or_404(Course, id=course_id)
        is_favorited = FavoriteCourse.objects.filter(
            user=request.user, 
            course=course
        ).exists()
        return JsonResponse({'is_favorited': is_favorited})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def get_favorite_count(request):
    """
    AJAX функция для получения количества избранных курсов
    Возвращает JSON: {'count': число}
    """
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        count = FavoriteCourse.objects.filter(
            user=request.user,
            course__is_active=True
        ).count()
        return JsonResponse({'count': count})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
@user_passes_test(is_listener)
def regenerate_certificate(request, certificate_id):
    """Перегенерация сертификата с актуальными баллами"""
    certificate = get_object_or_404(Certificate, id=certificate_id)
    
    if certificate.user_course.user != request.user:
        messages.error(request, 'У вас нет доступа к этому сертификату')
        return redirect('listener_app:my_certificates')
    try:
        if certificate.certificate_file_path:
            old_path = os.path.join(settings.MEDIA_ROOT, certificate.certificate_file_path)
            if os.path.exists(old_path):
                os.remove(old_path)
        pdf_path = generate_certificate_pdf(certificate)
        certificate.certificate_file_path = pdf_path
        certificate.save()
        
        messages.success(request, 'Сертификат успешно обновлён с актуальной статистикой!')
    except Exception as e:
        messages.error(request, f'Ошибка при обновлении сертификата: {str(e)}')
    
    return redirect('listener_app:certificate_detail', certificate_id=certificate.id)

@login_required
@user_passes_test(is_listener)
def payment_history(request):
    """История оплат слушателя"""
    user = request.user
    paid_courses = UserCourse.objects.filter(
        user=user,
        course_price__isnull=False,
        course_price__gt=0
    ).select_related('course').order_by('-payment_date', '-enrolled_at')
    
    print(f"Найдено курсов для пользователя {user.username}: {paid_courses.count()}")
    for pc in paid_courses:
        print(f"  - {pc.course.course_name}: {pc.course_price} руб.")

    total_spent = paid_courses.aggregate(
        total=Sum('course_price')
    )['total'] or 0
    
    payments_data = []
    for user_course in paid_courses:
        payment_id = user_course.payment_id
        if not payment_id or payment_id == '':
            date_str = user_course.enrolled_at.strftime('%Y%m%d') if user_course.enrolled_at else timezone.now().strftime('%Y%m%d')
            payment_id = f"MANUAL-{user_course.id}-{date_str}"

        payment_date = user_course.payment_date if user_course.payment_date else user_course.enrolled_at
        payments_data.append({
            'id': user_course.id,
            'course': user_course.course,
            'course_price': user_course.course_price,
            'payment_date': payment_date,
            'payment_id': payment_id,
            'enrolled_at': user_course.enrolled_at,
        })
    
    context = {
        'paid_courses': payments_data,
        'total_spent': total_spent,
        'paid_courses_count': len(payments_data),
    }
    
    return render(request, 'listener_payment_history.html', context)

@login_required
def get_course_posts(request, course_id):
    """Получить все посты курса"""
    from unireax_main.models import CoursePost, CoursePostComment, CourseTeacher
    from django.http import JsonResponse
    from django.utils import timezone
    
    course = get_object_or_404(Course, id=course_id)
    
    if not course.is_user_enrolled(request.user.id) and not request.user.is_admin:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    posts = CoursePost.objects.filter(course=course, is_active=True).select_related('author').prefetch_related('comments')
    
    is_teacher = CourseTeacher.objects.filter(course=course, teacher=request.user, is_active=True).exists() or request.user.is_admin
    
    def format_date(dt):
        """Форматирует дату с учетом временной зоны"""
        local_dt = timezone.localtime(dt)
        return local_dt.strftime('%d.%m.%Y %H:%M')
    
    posts_data = []
    for post in posts:
        posts_data.append({
            'id': post.id,
            'title': post.title,
            'content': post.content,
            'post_type': post.post_type,
            'post_type_display': post.get_post_type_display(),
            'is_pinned': post.is_pinned,
            'author_name': post.author.get_full_name() or post.author.username,
            'created_at': format_date(post.created_at),
            'can_edit': is_teacher or post.author == request.user,
            'comments': [
                {
                    'id': c.id,
                    'author_name': c.author.get_full_name() or c.author.username,
                    'content': c.content,
                    'created_at': format_date(c.created_at),
                    'can_delete': is_teacher or c.author == request.user
                }
                for c in post.comments.all()
            ]
        })
    
    return JsonResponse({
        'posts': posts_data,
        'can_create': is_teacher
    })

@login_required
def create_course_post(request, course_id):
    """Создать пост (AJAX)"""
    from unireax_main.models import CoursePost, CourseTeacher
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    course = get_object_or_404(Course, id=course_id)
    
    is_teacher = CourseTeacher.objects.filter(course=course, teacher=request.user, is_active=True).exists() or request.user.is_admin
    
    if not is_teacher:
        return JsonResponse({'error': 'Нет прав'}, status=403)
    
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    post_type = request.POST.get('post_type', 'announcement')
    is_pinned = request.POST.get('is_pinned') == 'true'
    
    if not title or len(title) < 3:
        return JsonResponse({'error': 'Заголовок слишком короткий'}, status=400)
    if not content or len(content) < 10:
        return JsonResponse({'error': 'Содержание слишком короткое'}, status=400)
    
    post = CoursePost.objects.create(
        course=course,
        author=request.user,
        title=title,
        content=content,
        post_type=post_type,
        is_pinned=is_pinned
    )
    
    return JsonResponse({
        'success': True,
        'post_id': post.id,
        'message': 'Объявление создано!'
    })


@login_required
def edit_course_post(request, post_id):
    """Редактировать пост (AJAX)"""
    from unireax_main.models import CoursePost, CourseTeacher
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    post = get_object_or_404(CoursePost, id=post_id, is_active=True)
    
    is_teacher = CourseTeacher.objects.filter(course=post.course, teacher=request.user, is_active=True).exists() or request.user.is_admin
    
    if not is_teacher and post.author != request.user:
        return JsonResponse({'error': 'Нет прав'}, status=403)
    
    title = request.POST.get('title', '').strip()
    content = request.POST.get('content', '').strip()
    post_type = request.POST.get('post_type', post.post_type)
    is_pinned = request.POST.get('is_pinned') == 'true'
    
    if not title or len(title) < 3:
        return JsonResponse({'error': 'Заголовок слишком короткий'}, status=400)
    if not content or len(content) < 10:
        return JsonResponse({'error': 'Содержание слишком короткое'}, status=400)
    
    post.title = title
    post.content = content
    post.post_type = post_type
    post.is_pinned = is_pinned
    post.save()
    
    return JsonResponse({'success': True, 'message': 'Объявление обновлено!'})


@login_required
def delete_course_post(request, post_id):
    """Удалить пост (AJAX)"""
    from unireax_main.models import CoursePost, CourseTeacher
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    post = get_object_or_404(CoursePost, id=post_id)
    
    is_teacher = CourseTeacher.objects.filter(course=post.course, teacher=request.user, is_active=True).exists() or request.user.is_admin
    
    if not is_teacher and post.author != request.user:
        return JsonResponse({'error': 'Нет прав'}, status=403)
    
    post.is_active = False
    post.save()
    
    return JsonResponse({'success': True, 'message': 'Объявление удалено!'})


@login_required
def add_course_comment(request, post_id):
    """Добавить комментарий к посту (AJAX)"""
    from unireax_main.models import CoursePost, CoursePostComment
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    post = get_object_or_404(CoursePost, id=post_id, is_active=True)
    
    if not post.course.is_user_enrolled(request.user.id) and not request.user.is_admin:
        return JsonResponse({'error': 'Нет доступа'}, status=403)
    
    content = request.POST.get('content', '').strip()
    parent_id = request.POST.get('parent_id')
    
    if not content or len(content) < 2:
        return JsonResponse({'error': 'Комментарий слишком короткий'}, status=400)
    
    parent_comment = None
    if parent_id:
        try:
            parent_comment = CoursePostComment.objects.get(id=parent_id)
        except CoursePostComment.DoesNotExist:
            return JsonResponse({'error': 'Родительский комментарий не найден'}, status=400)
    
    comment = CoursePostComment.objects.create(
        post=post,
        author=request.user,
        content=content,
        parent=parent_comment
    )
    
    return JsonResponse({
        'success': True,
        'comment': {
            'id': comment.id,
            'author_name': comment.author.get_full_name() or comment.author.username,
            'content': comment.content,
            'created_at': comment.created_at.strftime('%d.%m.%Y %H:%M'),
            'can_delete': comment.author == request.user
        }
    })


@login_required
def delete_course_comment(request, comment_id):
    """Удалить комментарий"""
    from unireax_main.models import CoursePostComment, CourseTeacher
    from django.http import JsonResponse
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Метод не разрешен'}, status=405)
    
    comment = get_object_or_404(CoursePostComment, id=comment_id)
    
    is_teacher = CourseTeacher.objects.filter(course=comment.post.course, teacher=request.user, is_active=True).exists() or request.user.is_admin
    
    if not is_teacher and comment.author != request.user:
        return JsonResponse({'error': 'Нет прав'}, status=403)
    
    comment.delete()
    
    return JsonResponse({'success': True, 'message': 'Комментарий удалён!'})