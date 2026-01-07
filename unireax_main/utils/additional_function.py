from django.db import connection

def calculate_course_progress(user, course):
    """расчет прогресса курса с использованием существующей функции БД"""
    try:
        with connection.cursor() as cu:
            cu.execute("SELECT calculate_course_completion(%s, %s)", [user.id, course.id])
            res = cu.fetchone()
            return float(res[0]) if res and res[0] is not None else 0.0
    except Exception as e:
        print(f"ошибка подсчета прогресса: {e}")
        return 0.0
