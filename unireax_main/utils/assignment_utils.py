from ..models import AssignmentStatus, UserPracticalAssignment

def update_assignment_status(user_assignment, feedback):
    """
    Обновляет статус задания на основе обратной связи
    Возвращает новый статус
    """
    try:
        assignment = user_assignment.practical_assignment
        score = feedback.score
        is_passed = feedback.is_passed
        
        print(f"=== ОБНОВЛЕНИЕ СТАТУСА ===")
        print(f"Задание: {assignment.id}, баллы: {score}, зачтено: {is_passed}")
        print(f"Тип оценивания: {assignment.grading_type}")
        print(f"Макс. балл: {assignment.max_score}")
        print(f"Проходной балл: {assignment.passing_score}")
        
        pending_status = AssignmentStatus.objects.get(assignment_status_name='на проверке')
        overdue_status = AssignmentStatus.objects.get(assignment_status_name='просрочено')
        rejected_status = AssignmentStatus.objects.get(assignment_status_name='отклонено')
        revision_status = AssignmentStatus.objects.get(assignment_status_name='на доработке')
        completed_status = AssignmentStatus.objects.get(assignment_status_name='завершено')
        
        if assignment.grading_type == 'points':
            max_score = assignment.max_score
            
            if assignment.passing_score is not None:
                passing_score = assignment.passing_score
                if score is not None and score >= passing_score:
                    new_status = completed_status
                    print(f"Набрано {score}/{passing_score} баллов. Статус: завершено")
                else:
                    new_status = revision_status
                    print(f"Набрано {score}/{passing_score} баллов. Статус: на доработке")
            else:
                passing_percentage = max_score * 0.5
                if score is not None and score >= passing_percentage:
                    new_status = completed_status
                    print(f"Набрано {score}/{passing_percentage:.2f} баллов. Статус: завершено")
                else:
                    new_status = revision_status
                    print(f"Набрано {score}/{passing_percentage:.2f} баллов. Статус: на доработке")
        
        elif assignment.grading_type == 'pass_fail':
            if is_passed:
                new_status = completed_status
                print(f"Зачтено! Статус: завершено")
            else:
                if score is not None and assignment.max_score:
                    percentage = (score / assignment.max_score) * 100
                    if percentage >= 50:
                        new_status = completed_status
                        print(f"Набрано {percentage}% (требуется 50%). Статус: завершено")
                    else:
                        new_status = revision_status
                        print(f"Набрано {percentage}% (требуется 50%). Статус: на доработке")
                else:
                    new_status = revision_status
                    print(f"Не зачтено! Статус: на доработке")
        
        else:
            new_status = revision_status
            print(f"Неизвестная система оценивания! Статус: на доработке")
        
        current_status_name = user_assignment.submission_status.assignment_status_name
        
        if current_status_name == 'на доработке' and new_status == revision_status:
            attempts_count = UserPracticalAssignment.objects.filter(
                user=user_assignment.user,
                practical_assignment=assignment
            ).count()
            
            if attempts_count >= 3:
                new_status = rejected_status
                print(f"Превышено 3 попытки! Статус: отклонено")
        
        user_assignment.submission_status = new_status
        user_assignment.save()
        
        print(f"Статус обновлен на: {new_status.assignment_status_name}")
        print(f"=== КОНЕЦ ОБНОВЛЕНИЯ ===")
        
        return new_status
        
    except Exception as e:
        print(f"Ошибка обновления статуса задания: {e}")
        import traceback
        print(traceback.format_exc())
        raise