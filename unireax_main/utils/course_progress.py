from django.db.models import Q, Count, Sum, F
from ..models import (
    Course, PracticalAssignment, Test, User, 
    UserPracticalAssignment, TestResult, Feedback,
    AssignmentStatus
)

def check_course_completion(user_id, course_id):
    """
    Проверяет, завершен ли курс пользователем.
    Возвращает:
        - completed: bool - завершен ли курс
        - progress: float - процент выполнения
        - details: dict - детальная статистика
    """
    
    total_assignments = PracticalAssignment.objects.filter(
        lecture__course_id=course_id,
        is_active=True
    ).count()
    
    user_assignments = UserPracticalAssignment.objects.filter(
        user_id=user_id,
        practical_assignment__lecture__course_id=course_id
    ).select_related('submission_status', 'practical_assignment')
    
    best_assignments = {}
    for ua in user_assignments:
        assignment_id = ua.practical_assignment_id
        
        if assignment_id not in best_assignments:
            best_assignments[assignment_id] = ua
        else:
            current = best_assignments[assignment_id]
            
            if ua.submission_status.assignment_status_name == 'завершено':
                best_assignments[assignment_id] = ua
            elif current.submission_status.assignment_status_name != 'завершено':
                if ua.attempt_number > current.attempt_number:
                    best_assignments[assignment_id] = ua
    
    completed_assignments = 0
    for assignment_id, ua in best_assignments.items():
        assignment = ua.practical_assignment
        
        if ua.submission_status.assignment_status_name == 'завершено':
            completed_assignments += 1
            continue

        try:
            feedback = Feedback.objects.get(user_practical_assignment=ua)
            
            if assignment.grading_type == 'points':
                if feedback.score is not None:
                    if assignment.passing_score:
                        if feedback.score >= assignment.passing_score:
                            completed_assignments += 1
                    else:
                        if assignment.max_score and feedback.score >= (assignment.max_score * 0.5):
                            completed_assignments += 1
            elif assignment.grading_type == 'pass_fail':
                if feedback.is_passed is True:
                    completed_assignments += 1
                    
        except Feedback.DoesNotExist:
            pass
    
    total_tests = Test.objects.filter(
        lecture__course_id=course_id,
        is_active=True
    ).count()
    
    test_results = TestResult.objects.filter(
        user_id=user_id,
        test__lecture__course_id=course_id
    ).select_related('test')
    
    best_tests = {}
    for tr in test_results:
        test_id = tr.test_id
        
        if test_id not in best_tests:
            best_tests[test_id] = tr
        else:
            current = best_tests[test_id]
            
            if tr.is_passed is True:
                best_tests[test_id] = tr
            elif current.is_passed is not True:
                if tr.final_score and current.final_score:
                    if tr.final_score > current.final_score:
                        best_tests[test_id] = tr
    
    passed_tests = 0
    for test_id, tr in best_tests.items():
        test = tr.test
        if test.grading_form == 'points':
            if test.passing_score:
                if tr.final_score and tr.final_score >= test.passing_score:
                    passed_tests += 1
            else:
                from django.db.models import Sum
                max_score = test.question_set.aggregate(total=Sum('question_score'))['total'] or 0
                if tr.final_score and tr.final_score >= (max_score * 0.5):
                    passed_tests += 1
        elif test.grading_form == 'pass_fail':
            if tr.is_passed is True:
                passed_tests += 1
    
    total_items = total_assignments + total_tests
    completed_items = completed_assignments + passed_tests
    
    progress = 0.0
    if total_items > 0:
        progress = (completed_items / total_items) * 100
    
    # курс считается завершенным, если:
    # 1. все практические задания выполнены (completed_assignments == total_assignments)
    # 2. все тесты пройдены (passed_tests == total_tests)
    # 3. прогресс = 100%
    
    all_assignments_done = total_assignments == 0 or completed_assignments == total_assignments
    all_tests_passed = total_tests == 0 or passed_tests == total_tests
    
    completed = (
        all_assignments_done and
        all_tests_passed and
        progress >= 99.9  
    )
    
    return {
        'completed': completed,
        'progress': round(progress, 2),
        'details': {
            'assignments': {
                'total': total_assignments,
                'completed': completed_assignments,
                'percentage': (completed_assignments / total_assignments * 100) if total_assignments > 0 else 0
            },
            'tests': {
                'total': total_tests,
                'passed': passed_tests,
                'percentage': (passed_tests / total_tests * 100) if total_tests > 0 else 0
            }
        }
    }


def calculate_total_course_score(user_id, course_id):
    """
    Рассчитывает общий набранный балл пользователя за курс
    Возвращает:
        - total_earned: float - набранные баллы
        - total_max: float - максимально возможные баллы
        - percentage: float - процент выполнения
        - with_honors: bool - с отличием (90%+ и финальный тест сдан на 90%+)
    """
    course = Course.objects.get(id=course_id)
    user = User.objects.get(id=user_id)
    
    total_earned = 0
    total_max = 0
    

    assignments = PracticalAssignment.objects.filter(
        lecture__course=course,
        is_active=True,
        grading_type='points'  
    )
    
    for assignment in assignments:
        max_score = assignment.max_score or 0
        total_max += max_score

        user_assignments = UserPracticalAssignment.objects.filter(
            user=user,
            practical_assignment=assignment
        ).order_by('-attempt_number')
        
        best_score = 0
        for ua in user_assignments:
            try:
                feedback = Feedback.objects.get(user_practical_assignment=ua)
                if feedback.score and feedback.score > best_score:
                    best_score = feedback.score
            except Feedback.DoesNotExist:
                pass
        
        total_earned += best_score
    
    tests = Test.objects.filter(
        lecture__course=course,
        is_active=True
    )
    
    final_test_passed_with_honors = False
    
    for test in tests:
        max_score = test.question_set.aggregate(total=Sum('question_score'))['total'] or 0
        total_max += max_score

        best_result = TestResult.objects.filter(
            user=user,
            test=test
        ).order_by('-final_score').first()
        
        if best_result and best_result.final_score:
            total_earned += best_result.final_score
            
            # проверка финального теста на "с отличием" (90%+)
            if test.is_final and max_score > 0:
                test_percentage = (best_result.final_score / max_score) * 100
                if test_percentage >= 90:
                    final_test_passed_with_honors = True
    
    percentage = (total_earned / total_max * 100) if total_max > 0 else 0
    
    # определение курса с завершением по условию "с отличием"
    # условия: общий процент >= 90% И (финальный тест сдан на 90%+ ИЛИ нет финального теста)
    has_final_test = tests.filter(is_final=True).exists()
    
    if has_final_test:
        with_honors = percentage >= 90 and final_test_passed_with_honors
    else:
        with_honors = percentage >= 90
    
    return {
        'total_earned': round(total_earned, 2),
        'total_max': round(total_max, 2),
        'percentage': round(percentage, 2),
        'with_honors': with_honors,
        'final_test_passed_with_honors': final_test_passed_with_honors
    }