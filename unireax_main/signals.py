from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import UserPracticalAssignment, TestResult, UserCourse
from .utils.course_progress import check_course_completion
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from .models import Feedback
import pytz

@receiver(post_save, sender=UserPracticalAssignment)
@receiver(post_save, sender=TestResult)
def check_and_update_course_completion(sender, instance, created, **kwargs):
    """Автоматически обновляет статус курса при сдаче заданий или тестов"""
    
    if sender == UserPracticalAssignment:
        user = instance.user
        course = instance.practical_assignment.lecture.course
    else:
        user = instance.user
        course = instance.test.lecture.course
    
    try:
        user_course = UserCourse.objects.get(user=user, course=course, is_active=True)
        completion_check = check_course_completion(user.id, course.id)
        
        if completion_check['completed'] and not user_course.status_course:
            user_course.status_course = True
            user_course.completion_date = timezone.now().date()
            user_course.save(update_fields=['status_course', 'completion_date'])
            print(f"Курс '{course.course_name}' завершен для {user.username}")
            
    except UserCourse.DoesNotExist:
        pass

@receiver(post_save, sender=Feedback)
def send_assignment_feedback_email_on_save(sender, instance, created, **kwargs):
    """
    Отправляет email студенту при создании или изменении оценки
    """
    if not instance.given_by:
        return
    
    user_assignment = instance.user_practical_assignment
    assignment = user_assignment.practical_assignment
    student = user_assignment.user
    course = assignment.lecture.course
    
    moscow_tz = pytz.timezone('Europe/Moscow')
    given_at_moscow = instance.given_at.astimezone(moscow_tz)
    feedback_date = given_at_moscow.strftime('%d.%m.%Y в %H:%M')
    
    if assignment.grading_type == 'points':
        if instance.score is not None:
            score_display = f"{instance.score} / {assignment.max_score}"
            if assignment.passing_score:
                is_passed = instance.score >= assignment.passing_score
            else:
                is_passed = instance.score >= (assignment.max_score / 2)
        else:
            score_display = "Не оценено"
            is_passed = False
    else:
        if instance.is_passed is True:
            score_display = "Зачтено"
            is_passed = True
        elif instance.is_passed is False:
            score_display = "Не зачтено"
            is_passed = False
        else:
            score_display = "Не оценено"
            is_passed = False
    
    is_changed = False
    old_score_display = None
    
    if not created:
        try:
            old = Feedback.objects.get(pk=instance.pk)
            
            if assignment.grading_type == 'points':
                if old.score is not None:
                    old_score_display = f"{old.score} / {assignment.max_score}"
                else:
                    old_score_display = "Не оценено"
            else:
                if old.is_passed is True:
                    old_score_display = "Зачтено"
                elif old.is_passed is False:
                    old_score_display = "Не зачтено"
                else:
                    old_score_display = "Не оценено"
            
            if (old.score != instance.score) or (old.is_passed != instance.is_passed):
                is_changed = True
                
        except Feedback.DoesNotExist:
            pass
    
    context = {
        'user': student,
        'assignment': assignment,
        'course': course,
        'feedback': instance,
        'score_display': score_display,
        'old_score_display': old_score_display,
        'is_passed': is_passed,
        'is_changed': is_changed,
        'grading_type': assignment.grading_type,
        'max_score': assignment.max_score if assignment.grading_type == 'points' else None,
        'feedback_date': feedback_date,
        'course_url': f"{settings.SITE_URL}/listener/course/{course.id}/",
    }
    
    html_content = render_to_string('emails/assignment_feedback.html', context)
    text_content = render_to_string('emails/assignment_feedback.txt', context)
    
    try:
        email = EmailMultiAlternatives(
            subject=f'Результаты проверки работы: {assignment.practical_assignment_name}',
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[student.email],
        )
        email.attach_alternative(html_content, "text/html")
        email.send()
        print(f"Email отправлен студенту {student.email}")
    except Exception as e:
        print(f"Ошибка отправки email: {e}")