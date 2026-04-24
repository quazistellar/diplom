import time
import random
import re
import os
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.db import transaction, connection
from django.utils import timezone
from faker import Faker
from django.db.models import Count, Q, Value, F
from django.db.models.functions import Coalesce
from decimal import Decimal
from statistics import mean
from contextlib import contextmanager

from unireax_main.models import (
    Role, User, CourseCategory, CourseType, AssignmentStatus,
    Course, Lecture, PracticalAssignment, Test, AnswerType,
    Question, ChoiceOption, UserCourse
)

fake = Faker('ru_RU')


class Command(BaseCommand):
    help = 'Тестирование производительности БД с разными объемами данных'

    def __init__(self):
        super().__init__()
        self.results = []
        self.search_results = []
        self.last_elapsed = 0
        self.faker = Faker('ru_RU')
        
        self.role_names = ['администратор', 'методист', 'преподаватель', 'слушатель курсов']
        self.course_categories = ['физика', 'астрономия', 'математика', 'программирование', 
                                   'информационные технологии', 'литература', 'история', 'география']
        self.course_types = ['образовательная программа', 'профессиональная переподготовка', 
                             'классная комната', 'подготовка к экзаменам']
        self.status_names = ['завершено', 'на доработке', 'отклонено', 'просрочено', 'на проверке']
        self.answer_types = ['один ответ', 'несколько ответов', 'текст', 'сопоставление']
        
        self.role_objects = {}
        self.category_objects = {}
        self.type_objects = {}
        self.status_objects = {}
        self.answer_type_objects = {}
        
        self.allowed_names = [
            'Иван', 'Петр', 'Сергей', 'Алексей', 'Дмитрий', 'Александр',
            'Мария', 'Елена', 'Анна', 'Ольга', 'Татьяна', 'Наталья',
            'Владимир', 'Николай', 'Михаил', 'Евгений', 'Андрей', 'Павел',
            'Екатерина', 'Ирина', 'Светлана', 'Юлия', 'Людмила', 'Галина'
        ]
        self.allowed_lastnames = [
            'Иванов', 'Петров', 'Сидоров', 'Смирнов', 'Кузнецов',
            'Попов', 'Васильев', 'Соколов', 'Михайлов', 'Новиков',
            'Федоров', 'Морозов', 'Волков', 'Алексеев', 'Лебедев',
            'Семенов', 'Егоров', 'Павлов', 'Козлов', 'Степанов'
        ]

    @contextmanager
    def measure_time_ms(self, operation_name):
        start = time.perf_counter()
        try:
            yield
            elapsed = (time.perf_counter() - start) * 1000
        except Exception as e:
            self.stdout.write(f"    Ошибка при измерении {operation_name}: {e}")
            elapsed = 0
        finally:
            self.last_elapsed = elapsed
            self.results.append({
                'operation': operation_name,
                'time_ms': elapsed
            })

    def setup_initial_data(self):
        self.stdout.write("\n=== Подготовка справочных данных ===")
        
        for role_name in self.role_names:
            role = Role.objects.filter(role_name=role_name).first()
            if role:
                self.role_objects[role_name] = role
        
        for cat_name in self.course_categories:
            cat = CourseCategory.objects.filter(course_category_name=cat_name).first()
            if cat:
                self.category_objects[cat_name] = cat
        
        for type_name in self.course_types:
            type_obj = CourseType.objects.filter(course_type_name=type_name).first()
            if type_obj:
                self.type_objects[type_name] = type_obj
        
        for status_name in self.status_names:
            status = AssignmentStatus.objects.filter(assignment_status_name=status_name).first()
            if status:
                self.status_objects[status_name] = status
        
        for at_name in self.answer_types:
            at = AnswerType.objects.filter(answer_type_name=at_name).first()
            if at:
                self.answer_type_objects[at_name] = at
        
        if not self.role_objects:
            self.stdout.write(self.style.WARNING("  Внимание: роли не найдены в базе данных!"))
        else:
            self.stdout.write(f"  Найдено ролей: {len(self.role_objects)}")
            self.stdout.write("  Справочные данные готовы")

    def clear_test_data(self):
        self.stdout.write("  Очистка тестовых данных...")
        try:
            Course.objects.filter(course_name__startswith='Тестовый курс').delete()
            User.objects.filter(username__startswith='test_').delete()
            self.stdout.write("  Очистка завершена")
        except Exception as e:
            self.stdout.write(f"  Ошибка при очистке: {e}")

    def generate_users_fast(self, count, volume_key):
        users = []
        roles_list = list(self.role_objects.values())
        
        if not roles_list:
            self.stdout.write(self.style.ERROR("  Ошибка: нет ролей для назначения пользователям!"))
            return users
        
        existing_usernames = set(User.objects.values_list('username', flat=True))
        existing_emails = set(User.objects.values_list('email', flat=True))
        prefix = f"test_{volume_key}_"
        
        for i in range(count):
            base_username = f"{prefix}{i}_{self.faker.user_name()[:10]}"
            base_username = re.sub(r'[^\w.@-]', '', base_username)
            username = base_username
            counter = 1
            while username in existing_usernames:
                username = f"{base_username}_{counter}"
                counter += 1
            existing_usernames.add(username)
            
            email = f"{username}@test.local"
            while email in existing_emails:
                email = f"{username}_{random.randint(1, 999)}@test.local"
            existing_emails.add(email)
            
            if i % 2 == 0:
                first_name = 'Иван'
            else:
                first_name = random.choice([n for n in self.allowed_names if n != 'Иван'])
            last_name = random.choice(self.allowed_lastnames)
            role = random.choice(roles_list)
            
            position = None
            educational_institution = None
            if role.role_name in ['методист', 'преподаватель']:
                position = "Преподаватель"
                educational_institution = "Тестовое учебное заведение"
            
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                role=role,
                position=position,
                educational_institution=educational_institution,
                is_verified=random.choice([True, False]),
                is_active=True,
                is_staff=False,
                is_superuser=False
            )
            user.password = 'pbkdf2_sha256$36000$test$testhash'
            users.append(user)
        
        return users

    def generate_courses_fast(self, count, users, volume_key):
        courses = []
        categories = list(self.category_objects.values())
        types = list(self.type_objects.values())
        creators = [u for u in users if u.role and u.role.role_name in ['методист', 'преподаватель']]
        
        words_with_a = ['математика', 'программирование', 'астрономия', 'алгебра', 'анализ', 
                        'лаборатория', 'практика', 'алгоритмы', 'архитектура', 'администрирование']
        
        for i in range(count):
            word = random.choice(words_with_a)
            course_name = f"Тестовый курс {volume_key}_{i+1} {word}"
            
            price = Decimal(random.randint(1000, 50000)) / 100
            
            course = Course(
                course_name=course_name,
                course_category=random.choice(categories) if categories else None,
                course_type=random.choice(types) if types else None,
                course_hours=random.randint(10, 100),
                course_price=price,
                is_active=True,
                is_completed=random.choice([True, False]),
                created_by=random.choice(creators) if creators else None
            )
            courses.append(course)
        
        return courses

    def generate_lectures_fast(self, count, courses, volume_key):
        lectures = []
        for i in range(count):
            course = random.choice(courses) if courses else None
            lecture = Lecture(
                lecture_name=f"Лекция {volume_key}_{i+1}",
                lecture_content="Тестовое содержание лекции",
                lecture_order=i + 1,
                course=course,
                is_active=True
            )
            lectures.append(lecture)
        
        return lectures

    def generate_assignments_fast(self, count, lectures, volume_key):
        assignments = []
        for i in range(count):
            lecture = random.choice(lectures) if lectures else None
            grading_type = random.choice(['points', 'pass_fail'])
            assignment = PracticalAssignment(
                practical_assignment_name=f"Задание {volume_key}_{i+1}",
                practical_assignment_description="Тестовое описание задания",
                lecture=lecture,
                grading_type=grading_type,
                max_score=random.randint(10, 100) if grading_type == 'points' else None,
                passing_score=random.randint(5, 50) if grading_type == 'points' else None,
                is_active=True,
                is_can_pin_after_deadline=False
            )
            assignments.append(assignment)
        
        return assignments

    def generate_tests_fast(self, count, lectures, volume_key):
        tests = []
        for i in range(count):
            lecture = random.choice(lectures) if lectures else None
            grading_form = random.choice(['points', 'pass_fail'])
            test = Test(
                test_name=f"Тест {volume_key}_{i+1}",
                lecture=lecture,
                grading_form=grading_form,
                passing_score=random.randint(10, 50) if grading_form == 'points' else None,
                is_active=True
            )
            tests.append(test)
        
        return tests

    def generate_questions_fast(self, count, tests, answer_types, volume_key):
        questions = []
        for i in range(count):
            test = random.choice(tests) if tests else None
            question = Question(
                test=test,
                question_text=f"Вопрос {volume_key}_{i+1}",
                answer_type=random.choice(answer_types) if answer_types else None,
                question_score=random.randint(1, 5),
                question_order=i + 1
            )
            questions.append(question)
        
        return questions

    def generate_choice_options_fast(self, count, questions, volume_key):
        options = []
        for i in range(count):
            question = random.choice(questions) if questions else None
            option = ChoiceOption(
                question=question,
                option_text=f"Вариант ответа {volume_key}_{i+1}",
                is_correct=(i % 3 == 0)
            )
            options.append(option)
        
        return options

    def generate_user_courses_fast(self, count, users, courses, volume_key):
        user_courses = []
        existing_pairs = set()
        
        for i in range(count):
            user = random.choice(users)
            course = random.choice(courses)
            pair_key = (user.id, course.id)
            
            while pair_key in existing_pairs:
                user = random.choice(users)
                course = random.choice(courses)
                pair_key = (user.id, course.id)
            
            existing_pairs.add(pair_key)
            
            registration_date = timezone.now().date() - timedelta(days=random.randint(1, 30))
            status_course = random.choice([True, False])
            
            completion_date = None
            if status_course:
                completion_date = registration_date + timedelta(days=random.randint(1, 30))
            
            user_course = UserCourse(
                user=user,
                course=course,
                status_course=status_course,
                completion_date=completion_date,
                is_active=True,
                registration_date=registration_date
            )
            user_courses.append(user_course)
        
        return user_courses
    
    def run_search_tests(self, volume_key, current_courses=None):
        self.stdout.write(f"\n  Тесты поиска и сортировки ({volume_key} записей):")
        
        search_results = {}
        prefix = f"test_{volume_key}_"
        course_prefix = f"Тестовый курс {volume_key}_"
        
        with self.measure_time_ms(f"{volume_key}_search_by_name"):
            ivan_users = list(User.objects.filter(
                username__startswith=prefix,
                first_name='Иван'
            ))
            t = self.last_elapsed
            count = len(ivan_users)
            self.stdout.write(f"    Поиск пользователей по имени (Иван): {count} записей за {t:.2f} мс")
            search_results['search_by_name'] = {'time': t, 'count': count}
            if self.results:
                self.results[-1]['count'] = count
        
        with self.measure_time_ms(f"{volume_key}_search_courses_by_name"):
            courses_with_a = list(Course.objects.filter(
                course_name__startswith=course_prefix,
                course_name__icontains='а'
            ))
            t = self.last_elapsed
            count = len(courses_with_a)
            self.stdout.write(f"    Поиск курсов по названию (содержит \"а\"): {count} записей за {t:.2f} мс")
            search_results['search_courses_by_name'] = {'time': t, 'count': count}
            if self.results:
                self.results[-1]['count'] = count
        
        with self.measure_time_ms(f"{volume_key}_sort_courses_by_price"):
            all_courses = list(Course.objects.filter(course_name__startswith=course_prefix))
            
            if not all_courses:
                all_courses = list(Course.objects.filter(course_name__contains=f"Тестовый курс {volume_key}"))
            
            sorted_courses = sorted(all_courses, key=lambda x: x.course_price if x.course_price is not None else 0)
            count = len(sorted_courses)
            
            self.stdout.write(f"    Сортировка курсов по цене: {count} записей за {self.last_elapsed:.2f} мс")
            
            search_results['sort_courses_by_price'] = {'time': self.last_elapsed, 'count': count}
            if self.results:
                self.results[-1]['count'] = count
        
        return search_results

    def run_tests_for_volume(self, volume_key, counts):
        self.stdout.write(f"\n{'='*60}")
        self.stdout.write(f"Тестирование объема: {volume_key} записей")
        self.stdout.write(f"{'='*60}")
        
        volume_results = {}
        
        with self.measure_time_ms(f"{volume_key}_write_users"):
            users = self.generate_users_fast(counts['users'], volume_key)
            if users:
                User.objects.filter(username__startswith=f'test_{volume_key}_').delete()
                User.objects.bulk_create(users, batch_size=100)
                current_users = list(User.objects.filter(username__startswith=f'test_{volume_key}_'))
                t = self.last_elapsed
                self.stdout.write(f"    Пользователи: {len(current_users)} записей за {t:.2f} мс")
                volume_results['write_users'] = t
            else:
                self.stdout.write(f"    Пользователи: 0 записей")
                volume_results['write_users'] = 0
                current_users = []
        
        with self.measure_time_ms(f"{volume_key}_write_courses"):
            courses = self.generate_courses_fast(counts['courses'], current_users, volume_key)
            if courses:
                Course.objects.filter(course_name__startswith=f'Тестовый курс {volume_key}_').delete()
                Course.objects.bulk_create(courses, batch_size=100)
                current_courses = list(Course.objects.filter(course_name__startswith=f'Тестовый курс {volume_key}_'))
                t = self.last_elapsed
                self.stdout.write(f"    Курсы: {len(current_courses)} записей за {t:.2f} мс")
                volume_results['write_courses'] = t
            else:
                self.stdout.write(f"    Курсы: 0 записей")
                volume_results['write_courses'] = 0
                current_courses = []
        
        with self.measure_time_ms(f"{volume_key}_write_lectures"):
            lectures = self.generate_lectures_fast(counts['lectures'], current_courses, volume_key)
            if lectures:
                Lecture.objects.filter(lecture_name__startswith=f'Лекция {volume_key}_').delete()
                Lecture.objects.bulk_create(lectures, batch_size=100)
                current_lectures = list(Lecture.objects.filter(lecture_name__startswith=f'Лекция {volume_key}_'))
                t = self.last_elapsed
                self.stdout.write(f"    Лекции: {len(current_lectures)} записей за {t:.2f} мс")
                volume_results['write_lectures'] = t
            else:
                self.stdout.write(f"    Лекции: 0 записей")
                volume_results['write_lectures'] = 0
                current_lectures = []
        
        with self.measure_time_ms(f"{volume_key}_write_assignments"):
            assignments = self.generate_assignments_fast(counts['assignments'], current_lectures, volume_key)
            if assignments:
                PracticalAssignment.objects.filter(practical_assignment_name__startswith=f'Задание {volume_key}_').delete()
                PracticalAssignment.objects.bulk_create(assignments, batch_size=100)
                t = self.last_elapsed
                self.stdout.write(f"    Задания: {len(assignments)} записей за {t:.2f} мс")
                volume_results['write_assignments'] = t
            else:
                self.stdout.write(f"    Задания: 0 записей")
                volume_results['write_assignments'] = 0
        
        with self.measure_time_ms(f"{volume_key}_write_tests"):
            tests = self.generate_tests_fast(counts['tests'], current_lectures, volume_key)
            if tests:
                Test.objects.filter(test_name__startswith=f'Тест {volume_key}_').delete()
                Test.objects.bulk_create(tests, batch_size=100)
                current_tests = list(Test.objects.filter(test_name__startswith=f'Тест {volume_key}_'))
                t = self.last_elapsed
                self.stdout.write(f"    Тесты: {len(current_tests)} записей за {t:.2f} мс")
                volume_results['write_tests'] = t
            else:
                self.stdout.write(f"    Тесты: 0 записей")
                volume_results['write_tests'] = 0
                current_tests = []
        
        with self.measure_time_ms(f"{volume_key}_write_questions"):
            questions = self.generate_questions_fast(counts['questions'], current_tests, list(self.answer_type_objects.values()), volume_key)
            if questions:
                Question.objects.filter(question_text__startswith=f'Вопрос {volume_key}_').delete()
                Question.objects.bulk_create(questions, batch_size=100)
                saved_questions = list(Question.objects.filter(question_text__startswith=f'Вопрос {volume_key}_'))
                t = self.last_elapsed
                self.stdout.write(f"    Вопросы: {len(saved_questions)} записей за {t:.2f} мс")
                volume_results['write_questions'] = t
            else:
                self.stdout.write(f"    Вопросы: 0 записей")
                volume_results['write_questions'] = 0
                saved_questions = []
        
        with self.measure_time_ms(f"{volume_key}_write_options"):
            if saved_questions:
                options = self.generate_choice_options_fast(counts['options'], saved_questions, volume_key)
                if options:
                    ChoiceOption.objects.filter(option_text__startswith=f'Вариант ответа {volume_key}_').delete()
                    ChoiceOption.objects.bulk_create(options, batch_size=100)
                    t = self.last_elapsed
                    self.stdout.write(f"    Варианты ответов: {len(options)} записей за {t:.2f} мс")
                    volume_results['write_options'] = t
                else:
                    self.stdout.write(f"    Варианты ответов: 0 записей")
                    volume_results['write_options'] = 0
            else:
                self.stdout.write(f"    Варианты ответов: 0 записей (нет вопросов)")
                volume_results['write_options'] = 0
        
        with self.measure_time_ms(f"{volume_key}_write_user_courses"):
            user_courses = self.generate_user_courses_fast(counts['user_courses'], current_users, current_courses, volume_key)
            if user_courses:
                UserCourse.objects.filter(user__username__startswith=f'test_{volume_key}_').delete()
                UserCourse.objects.bulk_create(user_courses, batch_size=100)
                t = self.last_elapsed
                self.stdout.write(f"    Связи: {len(user_courses)} записей за {t:.2f} мс")
                volume_results['write_user_courses'] = t
            else:
                self.stdout.write(f"    Связи: 0 записей")
                volume_results['write_user_courses'] = 0
        
        with self.measure_time_ms(f"{volume_key}_read_users"):
            users_count = User.objects.filter(username__startswith=f'test_{volume_key}_').count()
            t = self.last_elapsed
            self.stdout.write(f"    Чтение пользователей: {users_count} записей за {t:.2f} мс")
            volume_results['read_users'] = t
        
        with self.measure_time_ms(f"{volume_key}_read_courses"):
            courses_count = Course.objects.filter(course_name__startswith=f'Тестовый курс {volume_key}_').count()
            t = self.last_elapsed
            self.stdout.write(f"    Чтение курсов: {courses_count} записей за {t:.2f} мс")
            volume_results['read_courses'] = t
        
        with self.measure_time_ms(f"{volume_key}_read_lectures"):
            lectures_count = Lecture.objects.filter(lecture_name__startswith=f'Лекция {volume_key}_').count()
            t = self.last_elapsed
            self.stdout.write(f"    Чтение лекций: {lectures_count} записей за {t:.2f} мс")
            volume_results['read_lectures'] = t
        
        with self.measure_time_ms(f"{volume_key}_read_assignments"):
            assignments_count = PracticalAssignment.objects.filter(practical_assignment_name__startswith=f'Задание {volume_key}_').count()
            t = self.last_elapsed
            self.stdout.write(f"    Чтение заданий: {assignments_count} записей за {t:.2f} мс")
            volume_results['read_assignments'] = t
        
        with self.measure_time_ms(f"{volume_key}_read_tests"):
            tests_count = Test.objects.filter(test_name__startswith=f'Тест {volume_key}_').count()
            t = self.last_elapsed
            self.stdout.write(f"    Чтение тестов: {tests_count} записей за {t:.2f} мс")
            volume_results['read_tests'] = t
        
        with self.measure_time_ms(f"{volume_key}_read_questions"):
            questions_count = Question.objects.filter(question_text__startswith=f'Вопрос {volume_key}_').count()
            t = self.last_elapsed
            self.stdout.write(f"    Чтение вопросов: {questions_count} записей за {t:.2f} мс")
            volume_results['read_questions'] = t
        
        with self.measure_time_ms(f"{volume_key}_read_options"):
            options_count = ChoiceOption.objects.filter(option_text__startswith=f'Вариант ответа {volume_key}_').count()
            t = self.last_elapsed
            self.stdout.write(f"    Чтение вариантов ответов: {options_count} записей за {t:.2f} мс")
            volume_results['read_options'] = t
        
        with self.measure_time_ms(f"{volume_key}_read_user_courses"):
            user_courses_count = UserCourse.objects.filter(user__username__startswith=f'test_{volume_key}_').count()
            t = self.last_elapsed
            self.stdout.write(f"    Чтение связей: {user_courses_count} записей за {t:.2f} мс")
            volume_results['read_user_courses'] = t
        
        search_results = self.run_search_tests(volume_key, current_courses)
        volume_results['search'] = search_results
        
        return volume_results

    def generate_html_report(self):
        volumes_data = {}
        search_data_by_volume = {}
        
        for res in self.results:
            if 'operation' in res:
                parts = res['operation'].split('_')
                if len(parts) >= 2:
                    volume = parts[0]
                    operation = '_'.join(parts[1:])
                    
                    if volume not in volumes_data:
                        volumes_data[volume] = {}
                        search_data_by_volume[volume] = {}
                    
                    if operation.startswith('write_'):
                        volumes_data[volume][operation] = res['time_ms']
                    elif operation.startswith('read_'):
                        volumes_data[volume][operation] = res['time_ms']
                    elif operation in ['search_by_name', 'search_courses_by_name', 'sort_courses_by_price']:
                        search_data_by_volume[volume][operation] = {
                            'time': res['time_ms'],
                            'count': res.get('count', 0)
                        }
        
        html_lines = []
        html_lines.append('<!DOCTYPE html>')
        html_lines.append('<html lang="ru">')
        html_lines.append('<head>')
        html_lines.append('    <meta charset="UTF-8">')
        html_lines.append('    <title>Отчет о производительности базы данных</title>')
        html_lines.append('    <style>')
        html_lines.append('        body { font-family: "Segoe UI", Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }')
        html_lines.append('        .container { max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }')
        html_lines.append('        h1 { color: #333; border-bottom: 3px solid #4CAF50; padding-bottom: 10px; }')
        html_lines.append('        h2 { color: #555; margin-top: 30px; }')
        html_lines.append('        table { border-collapse: collapse; width: 100%; margin: 15px 0; }')
        html_lines.append('        th, td { border: 1px solid #ddd; padding: 12px 8px; text-align: center; }')
        html_lines.append('        th { background-color: #4CAF50; color: white; font-weight: bold; }')
        html_lines.append('        tr:nth-child(even) { background-color: #f9f9f9; }')
        html_lines.append('        .good { color: green; font-weight: bold; }')
        html_lines.append('        .medium { color: orange; font-weight: bold; }')
        html_lines.append('        .bad { color: red; font-weight: bold; }')
        html_lines.append('        .test-list { list-style-type: none; padding-left: 20px; }')
        html_lines.append('        .test-list li { margin: 8px 0; }')
        html_lines.append('    </style>')
        html_lines.append('</head>')
        html_lines.append('<body>')
        html_lines.append('<div class="container">')
        html_lines.append('    <h1>Отчет о производительности базы данных</h1>')
        
        html_lines.append('    <h2>Скорость записи данных (мс)</h2>')
        html_lines.append('    <table>')
        html_lines.append('        <thead>')
        html_lines.append('            <tr>')
        html_lines.append('                <th>Таблица</th>')
        html_lines.append('                <th>20 записей</th>')
        html_lines.append('                <th>200 записей</th>')
        html_lines.append('                <th>500 записей</th>')
        html_lines.append('                <th>1000 записей</th>')
        html_lines.append('            </tr>')
        html_lines.append('        </thead>')
        html_lines.append('        <tbody>')
        
        tables = ['users', 'courses', 'lectures', 'assignments', 'tests', 'questions', 'options', 'user_courses']
        labels = ['User', 'Course', 'Lecture', 'PracticalAssignment', 'Test', 'Question', 'ChoiceOption', 'UserCourse']
        volume_order = ['20', '200', '500', '1000']
        
        for table, label in zip(tables, labels):
            html_lines.append('            <tr>')
            html_lines.append(f'                <td><strong>{label}</strong></td>')
            for vol in volume_order:
                if vol in volumes_data:
                    time_val = volumes_data[vol].get(f'write_{table}', 0)
                    if time_val and time_val > 0:
                        css_class = 'good' if time_val < 100 else ('medium' if time_val < 500 else 'bad')
                        html_lines.append(f'                <td class="{css_class}">{time_val:.2f}</td>')
                    else:
                        html_lines.append('                <td class="medium">-</td>')
                else:
                    html_lines.append('                <td class="medium">-</td>')
            html_lines.append('            </tr>')
        
        html_lines.append('        </tbody>')
        html_lines.append('    </table>')
        
        html_lines.append('    <h2>Скорость чтения данных (мс)</h2>')
        html_lines.append('    <table>')
        html_lines.append('        <thead>')
        html_lines.append('            <tr>')
        html_lines.append('                <th>Таблица</th>')
        html_lines.append('                <th>20 записей</th>')
        html_lines.append('                <th>200 записей</th>')
        html_lines.append('                <th>500 записей</th>')
        html_lines.append('                <th>1000 записей</th>')
        html_lines.append('            </tr>')
        html_lines.append('        </thead>')
        html_lines.append('        <tbody>')
        
        for table, label in zip(tables, labels):
            html_lines.append('            <tr>')
            html_lines.append(f'                <td><strong>{label}</strong></td>')
            for vol in volume_order:
                if vol in volumes_data:
                    time_val = volumes_data[vol].get(f'read_{table}', 0)
                    if time_val and time_val > 0:
                        css_class = 'good' if time_val < 50 else ('medium' if time_val < 200 else 'bad')
                        html_lines.append(f'                <td class="{css_class}">{time_val:.2f}</td>')
                    else:
                        html_lines.append('                <td class="medium">-</td>')
                else:
                    html_lines.append('                <td class="medium">-</td>')
            html_lines.append('            </tr>')
        
        html_lines.append('        </tbody>')
        html_lines.append('    </table>')
        
        html_lines.append('    <h2>Тесты поиска и сортировки</h2>')
        
        for vol in volume_order:
            if vol in search_data_by_volume and search_data_by_volume[vol]:
                html_lines.append(f'    <h3>Тесты поиска и сортировки ({vol} записей):</h3>')
                html_lines.append('    <ul class="test-list">')
                
                if 'search_by_name' in search_data_by_volume[vol]:
                    data = search_data_by_volume[vol]['search_by_name']
                    html_lines.append(f'        <li>Поиск пользователей по имени (Иван): {data["count"]} записей за {data["time"]:.2f} мс</li>')
                
                if 'search_courses_by_name' in search_data_by_volume[vol]:
                    data = search_data_by_volume[vol]['search_courses_by_name']
                    html_lines.append(f'        <li>Поиск курсов по названию (содержит "а"): {data["count"]} записей за {data["time"]:.2f} мс</li>')
                
                if 'sort_courses_by_price' in search_data_by_volume[vol]:
                    data = search_data_by_volume[vol]['sort_courses_by_price']
                    html_lines.append(f'        <li>Сортировка курсов по цене: {data["count"]} записей за {data["time"]:.2f} мс</li>')
                
                html_lines.append('    </ul>')
        
        all_write_times = []
        all_read_times = []
        for vol in volumes_data.values():
            for k, v in vol.items():
                if isinstance(v, (int, float)) and v > 0:
                    if k.startswith('write_'):
                        all_write_times.append(v)
                    elif k.startswith('read_'):
                        all_read_times.append(v)
        
        if all_write_times and all_read_times:
            html_lines.append('    <div style="background-color: #e8f5e9; padding: 15px; border-radius: 5px; margin: 20px 0;">')
            html_lines.append('        <h2>Общая статистика</h2>')
            html_lines.append(f'        <p><strong>Среднее время записи:</strong> {mean(all_write_times):.2f} мс</p>')
            html_lines.append(f'        <p><strong>Среднее время чтения:</strong> {mean(all_read_times):.2f} мс</p>')
            html_lines.append(f'        <p><strong>Протестировано таблиц:</strong> {len(tables)}</p>')
            html_lines.append('    </div>')
        
        html_lines.append('</div>')
        html_lines.append('</body>')
        html_lines.append('</html>')
        
        return '\n'.join(html_lines)

    def handle(self, *args, **options):
        self.stdout.write("="*80)
        self.stdout.write("ЗАПУСК ТЕСТИРОВАНИЯ ПРОИЗВОДИТЕЛЬНОСТИ БАЗЫ ДАННЫХ")
        self.stdout.write("="*80)
        
        self.results = []
        self.setup_initial_data()
        
        if not self.role_objects:
            self.stdout.write(self.style.ERROR("Ошибка: Не найдены роли в базе данных!"))
            self.stdout.write("Запустите сначала команду настройки: python manage.py setup_app")
            return
        
        self.clear_test_data()
        
        volumes = {
            '20': {
                'users': 20,
                'courses': 20,
                'lectures': 20,
                'assignments': 20,
                'tests': 20,
                'questions': 20,
                'options': 20,
                'user_courses': 20
            },
            '200': {
                'users': 200,
                'courses': 200,
                'lectures': 200,
                'assignments': 200,
                'tests': 200,
                'questions': 200,
                'options': 200,
                'user_courses': 200
            },
            '500': {
                'users': 500,
                'courses': 500,
                'lectures': 500,
                'assignments': 500,
                'tests': 500,
                'questions': 500,
                'options': 500,
                'user_courses': 500
            },
            '1000': {
                'users': 1000,
                'courses': 1000,
                'lectures': 1000,
                'assignments': 1000,
                'tests': 1000,
                'questions': 1000,
                'options': 1000,
                'user_courses': 1000
            }
        }
        
        try:
            for vol_key, vol_counts in volumes.items():
                self.run_tests_for_volume(vol_key, vol_counts)
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"\nОшибка при выполнении тестов: {e}"))
            import traceback
            traceback.print_exc()
            raise
        
        html_content = self.generate_html_report()
        
        report_path = os.path.join(os.path.dirname(__file__), '..', '..', '..', 'rez.html')
        report_path = os.path.abspath(report_path)
        
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        self.stdout.write(f"\n{'='*80}")
        self.stdout.write(self.style.SUCCESS(f"HTML отчет сохранен: {report_path}"))
        self.stdout.write(self.style.SUCCESS("ТЕСТИРОВАНИЕ ЗАВЕРШЕНО"))
        self.stdout.write("="*80)