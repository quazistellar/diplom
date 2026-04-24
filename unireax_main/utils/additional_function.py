from django.db.models import Avg, Sum, Count, Q, F, Case, When, IntegerField, FloatField, Max
from django.utils import timezone
from django.db import transaction

def calculate_course_rating(course_id):
    """
    Рассчитывает средний рейтинг курса на основе одобренных отзывов
    """
    from ..models import Review
    
    try:
        avg_rating = Review.objects.filter(
            course_id=course_id,
            is_approved=True
        ).aggregate(
            average_rating=Avg('rating')
        )['average_rating']
        
        return float(avg_rating) if avg_rating is not None else 0.0
    except Exception as e:
        print(f"Ошибка при расчёте рейтинга курса {course_id}: {e}")
        return 0.0


def calculate_course_completion(user_id, course_id):
    """
    Рассчитывает процент завершения курса для пользователя
    Только практические задания и тесты (лекции не влияют на прогресс)
    Возвращает целое число от 0 до 100
    """
    from ..models import (
        UserCourse, PracticalAssignment, Test,
        UserPracticalAssignment, TestResult, Feedback,
        AssignmentStatus
    )
    
    try:
        if not UserCourse.objects.filter(
            user_id=user_id, 
            course_id=course_id,
            is_active=True
        ).exists():
            return 0
        
        total_items = 0
        completed_items = 0
        
        assignments = PracticalAssignment.objects.filter(
            lecture__course_id=course_id,
            is_active=True
        )
        
        for assignment in assignments:
            total_items += 1
            
            user_assignments = UserPracticalAssignment.objects.filter(
                user_id=user_id,
                practical_assignment=assignment
            ).order_by('-attempt_number')
            
            is_completed = False
            for user_assignment in user_assignments:
                status_name = user_assignment.submission_status.assignment_status_name
                
                if status_name == 'завершено':
                    try:
                        feedback = Feedback.objects.get(user_practical_assignment=user_assignment)
                        
                        if assignment.grading_type == 'points':
                            if feedback.score is not None:
                                max_score = assignment.max_score or 100
                                if feedback.score >= (max_score * 0.5):
                                    is_completed = True
                                    break
                        elif assignment.grading_type == 'pass_fail':
                            if feedback.is_passed:
                                is_completed = True
                                break
                    except Feedback.DoesNotExist:
                        is_completed = True
                        break
            
            if is_completed:
                completed_items += 1
        
        tests = Test.objects.filter(
            lecture__course_id=course_id,
            is_active=True
        )
        
        for test in tests:
            total_items += 1
            
            test_results = TestResult.objects.filter(
                user_id=user_id,
                test=test
            ).order_by('-attempt_number')
            
            is_completed = False
            for result in test_results:
                if test.grading_form == 'points':
                    if result.final_score is not None and test.passing_score is not None:
                        if result.final_score >= test.passing_score:
                            is_completed = True
                            break
                    elif result.final_score is not None:
                        if result.final_score > 0:
                            is_completed = True
                            break
                elif test.grading_form == 'pass_fail':
                    if result.is_passed:
                        is_completed = True
                        break
            
            if is_completed:
                completed_items += 1
        
        if total_items == 0:
            return 0
        
        completion_percentage = (completed_items / total_items) * 100
        return int(round(completion_percentage))
        
    except Exception as e:
        print(f"Ошибка при расчёте завершения курса для пользователя {user_id}, курс {course_id}: {e}")
        return 0


def calculate_total_course_points(course_id):
    """
    Рассчитывает общее количество возможных баллов в курсе
    """
    from ..models import PracticalAssignment, Question
    
    try:
        total_points = 0
        
        assignments_points = PracticalAssignment.objects.filter(
            lecture__course_id=course_id,
            is_active=True,
            grading_type='points'
        ).aggregate(
            total=Sum('max_score')
        )['total'] or 0
        
        total_points += assignments_points
        
        questions_points = Question.objects.filter(
            test__lecture__course_id=course_id,
            test__is_active=True
        ).aggregate(
            total=Sum('question_score')
        )['total'] or 0
        
        total_points += questions_points
        
        return float(total_points)
        
    except Exception as e:
        print(f"Ошибка при расчёте общего количества баллов для курса {course_id}: {e}")
        return 0.0


def calculate_user_course_points(user_id, course_id):
    """
    Рассчитывает количество баллов, набранных пользователем в курсе
    """
    from ..models import PracticalAssignment, UserPracticalAssignment, Feedback, Test, TestResult, Question
    
    try:
        total_points = 0
        
        assignments = PracticalAssignment.objects.filter(
            lecture__course_id=course_id,
            is_active=True
        )
        
        for assignment in assignments:
            user_assignment = UserPracticalAssignment.objects.filter(
                user_id=user_id,
                practical_assignment=assignment
            ).first()
            
            if user_assignment:
                try:
                    feedback = Feedback.objects.get(user_practical_assignment=user_assignment)
                    if feedback and feedback.score:
                        total_points += feedback.score
                except Feedback.DoesNotExist:
                    pass
        
        tests = Test.objects.filter(
            lecture__course_id=course_id,
            is_active=True
        )
        
        for test in tests:
            best_result = TestResult.objects.filter(
                user_id=user_id,
                test=test
            ).aggregate(
                best_score=Max('final_score')
            )['best_score']
            
            if best_result:
                total_points += best_result
        
        return float(total_points)
        
    except Exception as e:
        print(f"Ошибка при расчёте баллов пользователя {user_id} в курсе {course_id}: {e}")
        return 0.0


def get_course_statistics(course_id):
    """
    Возвращает полную статистику по курсу
    """
    from ..models import Course, Review, UserCourse, Lecture, PracticalAssignment, Test
    
    try:
        course = Course.objects.get(id=course_id)
        
        reviews = Review.objects.filter(course_id=course_id, is_approved=True)
        
        rating_stats = reviews.aggregate(
            avg_rating=Avg('rating'),
            total_reviews=Count('id'),
            five_star=Count('id', filter=Q(rating=5)),
            four_star=Count('id', filter=Q(rating=4)),
            three_star=Count('id', filter=Q(rating=3)),
            two_star=Count('id', filter=Q(rating=2)),
            one_star=Count('id', filter=Q(rating=1))
        )
        
        enrollments = UserCourse.objects.filter(course_id=course_id)
        enrollment_stats = enrollments.aggregate(
            total_enrollments=Count('id'),
            active_enrollments=Count('id', filter=Q(is_active=True)),
            completed_enrollments=Count('id', filter=Q(status_course=True))
        )
        
        teachers_count = course.courseteacher_set.filter(is_active=True).count()
        materials_stats = {
            'lectures': Lecture.objects.filter(course_id=course_id, is_active=True).count(),
            'assignments': PracticalAssignment.objects.filter(lecture__course_id=course_id, is_active=True).count(),
            'tests': Test.objects.filter(lecture__course_id=course_id, is_active=True).count(),
        }
        
        avg_progress = 0.0
        active_enrollments = enrollments.filter(is_active=True)
        if active_enrollments.exists():
            total_progress = 0
            for enrollment in active_enrollments:
                progress = calculate_course_completion(enrollment.user_id, course_id)
                total_progress += progress
            avg_progress = total_progress / active_enrollments.count()
        
        return {
            'course': {
                'id': course.id,
                'name': course.course_name,
                'hours': course.course_hours,
                'price': float(course.course_price) if course.course_price else None,
                'has_certificate': course.has_certificate,
                'is_completed': course.is_completed,
                'is_active': course.is_active,
            },
            'rating': {
                'average': float(rating_stats['avg_rating']) if rating_stats['avg_rating'] else 0.0,
                'total': rating_stats['total_reviews'],
                'distribution': {
                    5: rating_stats['five_star'],
                    4: rating_stats['four_star'],
                    3: rating_stats['three_star'],
                    2: rating_stats['two_star'],
                    1: rating_stats['one_star']
                }
            },
            'enrollments': enrollment_stats,
            'teachers_count': teachers_count,
            'materials': materials_stats,
            'progress': {
                'average': round(avg_progress, 2),
                'total_points': calculate_total_course_points(course_id)
            }
        }
        
    except Course.DoesNotExist:
        return None
    except Exception as e:
        print(f"Ошибка при получении статистики курса {course_id}: {e}")
        return None


def get_user_course_progress(user_id, course_id):
    """
    Получает детальный прогресс пользователя по курсу
    """
    from ..models import UserCourse, Course, Lecture, PracticalAssignment, UserPracticalAssignment, Feedback, Test, TestResult, Question
    
    try:
        user_course = UserCourse.objects.filter(
            user_id=user_id,
            course_id=course_id,
            is_active=True
        ).first()
        
        if not user_course:
            return None
        
        course = Course.objects.get(id=course_id)
        completion = calculate_course_completion(user_id, course_id)
        total_points = calculate_total_course_points(course_id)
        earned_points = calculate_user_course_points(user_id, course_id)
        assignments_progress = []
        tests_progress = []
        
        assignments = PracticalAssignment.objects.filter(
            lecture__course_id=course_id,
            is_active=True
        ).select_related('lecture')
        
        for assignment in assignments:
            user_assignment = UserPracticalAssignment.objects.filter(
                user_id=user_id,
                practical_assignment=assignment
            ).first()
            
            status = "Не начато"
            is_completed = False
            score = 0
            max_score = assignment.max_score if assignment.grading_type == 'points' else None
            
            if user_assignment:
                status = user_assignment.submission_status.assignment_status_name if user_assignment.submission_status else "Сдано"
                
                if user_assignment.submission_status_id >= 2:
                    is_completed = True
                
                try:
                    feedback = Feedback.objects.get(user_practical_assignment=user_assignment)
                    if feedback:
                        score = feedback.score if feedback.score else 0
                        is_completed = True
                except Feedback.DoesNotExist:
                    pass
            
            assignments_progress.append({
                'id': assignment.id,
                'name': assignment.practical_assignment_name,
                'lecture': assignment.lecture.lecture_name,
                'lecture_order': assignment.lecture.lecture_order,
                'status': status,
                'is_completed': is_completed,
                'score': score,
                'max_score': max_score,
                'deadline': assignment.assignment_deadline,
                'submission_date': user_assignment.submission_date if user_assignment else None
            })
        
        tests = Test.objects.filter(
            lecture__course_id=course_id,
            is_active=True
        ).select_related('lecture')
        
        for test in tests:
            best_result = TestResult.objects.filter(
                user_id=user_id,
                test=test
            ).order_by('-final_score').first()
            
            is_completed = best_result is not None
            is_passed = False
            score = 0
            
            if best_result:
                score = best_result.final_score or 0
                if test.grading_form == 'pass_fail':
                    is_passed = best_result.is_passed or False
                else:
                    is_passed = test.passing_score and score >= test.passing_score
            
            max_test_score = Question.objects.filter(
                test=test
            ).aggregate(total=Sum('question_score'))['total'] or 0
            
            tests_progress.append({
                'id': test.id,
                'name': test.test_name,
                'lecture': test.lecture.lecture_name,
                'lecture_order': test.lecture.lecture_order,
                'is_completed': is_completed,
                'is_passed': is_passed,
                'score': score,
                'max_score': max_test_score,
                'passing_score': test.passing_score,
                'attempts': TestResult.objects.filter(user_id=user_id, test=test).count(),
                'best_result_date': best_result.completion_date if best_result else None
            })
        
        lectures = Lecture.objects.filter(
            course_id=course_id,
            is_active=True
        ).order_by('lecture_order')
        
        lectures_progress = []
        for lecture in lectures:
            lecture_assignments = [a for a in assignments_progress if a['lecture'] == lecture.lecture_name]
            lecture_tests = [t for t in tests_progress if t['lecture'] == lecture.lecture_name]
            
            lecture_items = len(lecture_assignments) + len(lecture_tests)
            completed_items = len([a for a in lecture_assignments if a['is_completed']]) + \
                            len([t for t in lecture_tests if t['is_passed']])
            
            lecture_progress = (completed_items / lecture_items * 100) if lecture_items > 0 else 0
            
            lectures_progress.append({
                'id': lecture.id,
                'name': lecture.lecture_name,
                'order': lecture.lecture_order,
                'progress': round(lecture_progress, 2),
                'assignments_count': len(lecture_assignments),
                'tests_count': len(lecture_tests),
                'completed_count': completed_items,
                'total_count': lecture_items
            })
        
        certificate_eligible = (
            user_course.status_course and 
            completion >= 100 and 
            course.has_certificate and 
            course.is_completed
        )
        
        return {
            'user_id': user_id,
            'course_id': course_id,
            'course_name': course.course_name,
            'enrollment_date': user_course.registration_date,
            'is_active': user_course.is_active,
            'course_completed': user_course.status_course,
            'completion_date': user_course.completion_date,
            'overall_progress': {
                'percentage': completion,
                'assignments_completed': len([a for a in assignments_progress if a['is_completed']]),
                'assignments_total': len(assignments_progress),
                'tests_passed': len([t for t in tests_progress if t['is_passed']]),
                'tests_total': len(tests_progress)
            },
            'points': {
                'total': total_points,
                'earned': earned_points,
                'remaining': max(0, total_points - earned_points),
                'percentage': round((earned_points / total_points * 100), 2) if total_points > 0 else 0
            },
            'certificate': {
                'eligible': certificate_eligible,
                'requirements': {
                    'course_completed': user_course.status_course,
                    'progress_100': completion >= 100,
                    'course_has_certificate': course.has_certificate,
                    'materials_completed': course.is_completed
                },
                'course_has_certificate': course.has_certificate
            },
            'lectures_progress': lectures_progress,
            'assignments_progress': assignments_progress,
            'tests_progress': tests_progress
        }
        
    except Course.DoesNotExist:
        print(f"Курс {course_id} не найден")
        return None
    except Exception as e:
        print(f"Ошибка при получении прогресса пользователя {user_id} по курсу {course_id}: {e}")
        return None


def calculate_certificate_eligibility(user_id, course_id):
    """
    Проверяет, имеет ли пользователь право на получение сертификата
    Учитывает прохождение финальных тестов и условия оценивания
    """
    from ..models import UserCourse, Course, Test, TestResult, Question
    from django.db.models import Q, Sum
    
    try:
        user_course = UserCourse.objects.get(
            user_id=user_id,
            course_id=course_id
        )
        
        course = Course.objects.get(id=course_id)
        completion = calculate_course_completion(user_id, course_id)
        
        if not user_course.status_course:
            return {
                'is_eligible': False,
                'requirements': {
                    'course_completed': False,
                    'message': 'Курс не завершен'
                },
                'progress': completion,
                'course': {
                    'id': course.id,
                    'name': course.course_name,
                    'has_certificate': course.has_certificate,
                    'is_completed': course.is_completed
                },
                'user_course': {
                    'is_completed': user_course.status_course,
                    'completion_date': user_course.completion_date
                }
            }
        
        if not course.has_certificate:
            return {
                'is_eligible': False,
                'requirements': {
                    'course_has_certificate': False,
                    'message': 'Курс не предусматривает выдачу сертификатов'
                },
                'progress': completion,
                'course': {
                    'id': course.id,
                    'name': course.course_name,
                    'has_certificate': course.has_certificate,
                    'is_completed': course.is_completed
                },
                'user_course': {
                    'is_completed': user_course.status_course,
                    'completion_date': user_course.completion_date
                }
            }
        
        if not course.is_completed:
            return {
                'is_eligible': False,
                'requirements': {
                    'course_materials_completed': False,
                    'message': 'Курс ещё пополняется материалами'
                },
                'progress': completion,
                'course': {
                    'id': course.id,
                    'name': course.course_name,
                    'has_certificate': course.has_certificate,
                    'is_completed': course.is_completed
                },
                'user_course': {
                    'is_completed': user_course.status_course,
                    'completion_date': user_course.completion_date
                }
            }
        
        if completion < 100:
            return {
                'is_eligible': False,
                'requirements': {
                    'user_progress_100': False,
                    'message': f'Прогресс курса {completion}% (требуется 100%)'
                },
                'progress': completion,
                'course': {
                    'id': course.id,
                    'name': course.course_name,
                    'has_certificate': course.has_certificate,
                    'is_completed': course.is_completed
                },
                'user_course': {
                    'is_completed': user_course.status_course,
                    'completion_date': user_course.completion_date
                }
            }
        
        final_tests = Test.objects.filter(
            lecture__course=course,
            is_final=True,
            is_active=True
        )
        
        test_results = {}
        all_tests_passed = True
        failed_tests = []
        
        for test in final_tests:
            if test.grading_form == 'points':
                best_result = TestResult.objects.filter(
                    user_id=user_id,
                    test=test
                ).order_by('-final_score').first()
            else:
                best_result = TestResult.objects.filter(
                    user_id=user_id,
                    test=test
                ).order_by(
                    '-is_passed',
                    '-completion_date'
                ).first()
            
            if not best_result:
                all_tests_passed = False
                failed_tests.append({
                    'test_id': test.id,
                    'test_name': test.test_name,
                    'reason': 'Тест не пройден'
                })
                continue
            
            test_passed = False
            score_info = {}
            
            if test.grading_form == 'points':
                max_score = Question.objects.filter(test=test).aggregate(
                    total=Sum('question_score')
                )['total'] or 100
                
                user_score = best_result.final_score or 0
                
                if test.passing_score:
                    if 1 < test.passing_score <= 100:
                        required_percentage = test.passing_score
                        user_percentage = (user_score / max_score * 100) if max_score > 0 else 0
                        test_passed = user_percentage >= required_percentage
                        
                        score_info = {
                            'user_score': user_score,
                            'max_score': max_score,
                            'user_percentage': round(user_percentage, 1),
                            'required_percentage': required_percentage,
                            'passing_type': 'percentage'
                        }
                    else:
                        test_passed = user_score >= test.passing_score
                        
                        score_info = {
                            'user_score': user_score,
                            'max_score': max_score,
                            'required_score': test.passing_score,
                            'passing_type': 'absolute'
                        }
                else:
                    user_percentage = (user_score / max_score * 100) if max_score > 0 else 0
                    test_passed = user_percentage >= 50
                    
                    score_info = {
                        'user_score': user_score,
                        'max_score': max_score,
                        'user_percentage': round(user_percentage, 1),
                        'required_percentage': 50,
                        'passing_type': 'percentage_default'
                    }
            
            else: 
                test_passed = best_result.is_passed or False
                score_info = {
                    'is_passed': test_passed
                }
            
            if not test_passed:
                all_tests_passed = False
                reason = 'Недостаточно баллов' if test.grading_form == 'points' else 'Не зачтено'
                failed_tests.append({
                    'test_id': test.id,
                    'test_name': test.test_name,
                    'reason': reason,
                    'details': score_info
                })
            
            test_results[test.test_name] = {
                'attempt_number': best_result.attempt_number,
                'completion_date': best_result.completion_date,
                'is_passed': test_passed,
                'score_info': score_info,
                'grading_form': test.grading_form
            }
        
        requirements = {
            'course_completed': user_course.status_course,
            'course_has_certificate': course.has_certificate,
            'course_materials_completed': course.is_completed,
            'user_progress_100': completion >= 100,
            'final_tests_passed': all_tests_passed
        }
        
        is_eligible = all(requirements.values())
        
        return {
            'is_eligible': is_eligible,
            'requirements': requirements,
            'progress': completion,
            'final_tests': {
                'count': final_tests.count(),
                'passed_count': len(final_tests) - len(failed_tests),
                'failed_tests': failed_tests if not is_eligible else [],
                'results': test_results
            },
            'course': {
                'id': course.id,
                'name': course.course_name,
                'has_certificate': course.has_certificate,
                'is_completed': course.is_completed
            },
            'user_course': {
                'is_completed': user_course.status_course,
                'completion_date': user_course.completion_date,
                'registration_date': user_course.registration_date
            },
            'message': 'Сертификат доступен' if is_eligible else 'Условия для получения сертификата не выполнены'
        }
        
    except UserCourse.DoesNotExist:
        return {
            'is_eligible': False,
            'requirements': {'enrolled': False},
            'progress': 0,
            'final_tests': None,
            'course': None,
            'user_course': None,
            'message': 'Пользователь не записан на курс'
        }
    except Course.DoesNotExist:
        return {
            'is_eligible': False,
            'requirements': {'course_exists': False},
            'progress': 0,
            'final_tests': None,
            'course': None,
            'user_course': None,
            'message': 'Курс не найден'
        }
    except Exception as e:
        print(f"Ошибка при проверке права на сертификат: {e}")
        import traceback
        print(traceback.format_exc())
        return {
            'is_eligible': False,
            'requirements': {'error': str(e)},
            'progress': 0,
            'final_tests': None,
            'course': None,
            'user_course': None,
            'message': f'Ошибка проверки: {str(e)}'
        }

def get_courses_with_ratings():
    """
    Получает все курсы с аннотированными рейтингами
    """
    from ..models import Course, Review
    
    return Course.objects.annotate(
        calculated_rating=Avg(
            'review__rating',
            filter=Q(review__is_approved=True)
        ),
        review_count=Count(
            'review',
            filter=Q(review__is_approved=True)
        )
    ).filter(
        is_active=True
    )


def get_popular_courses(limit=10):
    """
    Возвращает популярные курсы (по количеству зачислений и рейтингу)
    """
    from ..models import Course, Review, UserCourse
    
    courses = Course.objects.annotate(
        calculated_rating=Avg(
            'review__rating',
            filter=Q(review__is_approved=True)
        ),
        total_enrollments=Count('usercourse'),
        active_enrollments=Count('usercourse', filter=Q(usercourse__is_active=True))
    ).filter(
        is_active=True
    ).order_by('-active_enrollments', '-calculated_rating')[:limit]
    
    return courses


def get_user_active_courses(user_id):
    """
    Возвращает активные курсы пользователя с прогрессом
    """
    from ..models import UserCourse, Course, Lecture
    
    user_courses = UserCourse.objects.filter(
        user_id=user_id,
        is_active=True
    ).select_related('course')
    
    result = []
    for user_course in user_courses:
        course = user_course.course
        progress = calculate_course_completion(user_id, course.id)
        
        result.append({
            'course_id': course.id,
            'course_name': course.course_name,
            'course_description': course.course_description,
            'enrollment_date': user_course.registration_date,
            'progress': progress,
            'is_course_completed': user_course.status_course,
            'course_photo': course.course_photo_path.url if course.course_photo_path else None,
            'hours': course.course_hours,
            'price': float(course.course_price) if course.course_price else None,
            'has_certificate': course.has_certificate,
            'next_deadline': None  
        })
    
    return result



def get_best_test_result(user_id, test_id):
    """
    Возвращает лучший результат пользователя по конкретному тесту
    Для балльной системы - с максимальным баллом
    Для зачет/незачет - сначала зачтенные, потом последние по дате
    
    Args:
        user_id: ID пользователя
        test_id: ID теста
    
    Returns:
        TestResult object or None
    """
    from unireax_main.models import Test, TestResult
    
    try:
        test = Test.objects.get(id=test_id)
        
        if test.grading_form == 'points':
            return TestResult.objects.filter(
                user_id=user_id,
                test_id=test_id
            ).order_by('-final_score').first()
        else:
            return TestResult.objects.filter(
                user_id=user_id,
                test_id=test_id
            ).order_by(
                '-is_passed',
                '-completion_date' 
            ).first()
    except Test.DoesNotExist:
        return None
    except Exception as e:
        print(f"Ошибка в get_best_test_result: {e}")
        return None