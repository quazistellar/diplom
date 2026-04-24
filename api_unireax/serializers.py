from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from unireax_main.models import *
from django.contrib.auth import get_user_model
User = get_user_model()

# 1. роли пользователей
class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ['id', 'role_name', 'role_name']

# 2. пользователи
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    role_details = RoleSerializer(source='role', read_only=True)
    full_name = serializers.ReadOnlyField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name', 'patronymic',
            'password', 'role', 'role_details', 'position', 
            'educational_institution', 'certificate_file', 'is_verified',
            'is_light_theme', 'full_name', 'date_joined', 'last_login',
            'is_active', 'is_staff', 'is_superuser'
        ]
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True},
            'username': {'required': True}
        }

    def validate_email(self, value):
        value = value.lower()

        instance = getattr(self, 'instance', None)
        
        query = User.objects.filter(email=value)
        
        if instance:
            query = query.exclude(id=instance.id)
        
        if query.exists():
            raise serializers.ValidationError("Пользователь с такой почтой уже существует")
        
        return value

    def validate_username(self, value):
        instance = getattr(self, 'instance', None)
        
        query = User.objects.filter(username=value)
        
        if instance:
            query = query.exclude(id=instance.id)
        
        if query.exists():
            raise serializers.ValidationError("Пользователь с таким именем уже существует")
        
        return value

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = User(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance

# 3. категории курсов
class CourseCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseCategory
        fields = ['id', 'course_category_name']

# 4. типы курсов
class CourseTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CourseType
        fields = ['id', 'course_type_name', 'course_type_description']

# 5. статусы заданий
class AssignmentStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssignmentStatus
        fields = ['id', 'assignment_status_name']

# 6. курсы
class CourseSerializer(serializers.ModelSerializer):
    category_details = CourseCategorySerializer(source='course_category', read_only=True)
    type_details = CourseTypeSerializer(source='course_type', read_only=True)
    created_by_details = UserSerializer(source='created_by', read_only=True)
    rating = serializers.ReadOnlyField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'course_name', 'course_description', 'course_price',
            'course_category', 'category_details', 'course_photo_path',
            'has_certificate', 'course_max_places', 'course_hours',
            'is_completed', 'code_link', 'course_type', 'type_details',
            'created_by', 'created_by_details', 'is_active', 'created_at',
            'rating'
        ]

# 7. преподаватели_курсы
class CourseTeacherSerializer(serializers.ModelSerializer):
    teacher_details = UserSerializer(source='teacher', read_only=True)
    course_details = CourseSerializer(source='course', read_only=True)

    class Meta:
        model = CourseTeacher
        fields = [
            'id', 'course', 'course_details', 'teacher', 'teacher_details',
            'start_date', 'is_active'
        ]

# 8. лекции
class LectureSerializer(serializers.ModelSerializer):
    course_details = CourseSerializer(source='course', read_only=True)

    class Meta:
        model = Lecture
        fields = [
            'id', 'lecture_name', 'lecture_content', 'lecture_document_path',
            'lecture_order', 'course', 'course_details', 'is_active',
            'created_at', 'updated_at'
        ]

# 9. практические задания
class PracticalAssignmentSerializer(serializers.ModelSerializer):
    is_overdue = serializers.BooleanField(read_only=True)
    can_submit = serializers.BooleanField(read_only=True)
    
    class Meta:
        model = PracticalAssignment
        fields = [
            'id',
            'practical_assignment_name',
            'practical_assignment_description',
            'assignment_document_path',
            'assignment_criteria',
            'lecture',
            'assignment_deadline',
            'grading_type',
            'max_score',
            'passing_score',  
            'is_active',
            'created_at',
            'updated_at',
            'is_can_pin_after_deadline',
            'is_overdue',
            'can_submit',
        ]
        read_only_fields = ['created_at', 'updated_at', 'is_overdue', 'can_submit']


# 10. сдачи практических заданий
class UserPracticalAssignmentSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    assignment_details = PracticalAssignmentSerializer(source='practical_assignment', read_only=True)
    status_details = AssignmentStatusSerializer(source='submission_status', read_only=True)

    class Meta:
        model = UserPracticalAssignment
        fields = [
            'id', 'user', 'user_details', 'practical_assignment',
            'assignment_details', 'submission_date', 'submission_status',
            'status_details', 'attempt_number', 'comment', 'submitted_at'
        ]


# 11. пользователи_курсы
class UserCourseSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    course_details = CourseSerializer(source='course', read_only=True)

    class Meta:
        model = UserCourse
        fields = [
            'id', 'user', 'user_details', 'course', 'course_details',
            'registration_date', 'status_course', 'payment_date',
            'completion_date', 'course_price', 'is_active', 'enrolled_at'
        ]

# 12. обратная связь
class FeedbackSerializer(serializers.ModelSerializer):
    user_assignment_details = UserPracticalAssignmentSerializer(source='user_practical_assignment', read_only=True)
    given_by_details = UserSerializer(source='given_by', read_only=True)

    class Meta:
        model = Feedback
        fields = [
            'id', 'user_practical_assignment', 'user_assignment_details',
            'score', 'is_passed', 'comment_feedback', 'given_at',
            'given_by', 'given_by_details'
        ]

# 13. отзывы
class ReviewSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    course_details = CourseSerializer(source='course', read_only=True)

    class Meta:
        model = Review
        fields = [
            'id', 'course', 'course_details', 'user', 'user_details',
            'rating', 'publish_date', 'comment_review', 'is_approved'
        ]

# 14. типы ответов
class AnswerTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = AnswerType
        fields = ['id', 'answer_type_name', 'answer_type_description']

# 15. тесты
class TestSerializer(serializers.ModelSerializer):
    lecture_details = LectureSerializer(source='lecture', read_only=True)

    class Meta:
        model = Test
        fields = [
            'id', 'test_name', 'test_description', 'is_final',
            'lecture', 'lecture_details', 'max_attempts',
            'grading_form', 'passing_score', 'is_active',
            'created_at', 'updated_at'
        ]

# 16. вопросы
class QuestionSerializer(serializers.ModelSerializer):
    test_details = TestSerializer(source='test', read_only=True)
    answer_type_details = AnswerTypeSerializer(source='answer_type', read_only=True)

    class Meta:
        model = Question
        fields = [
            'id', 'test', 'test_details', 'question_text',
            'answer_type', 'answer_type_details', 'question_score',
            'correct_text', 'question_order'
        ]


# 17. варианты ответов
class ChoiceOptionSerializer(serializers.ModelSerializer):
    question_details = QuestionSerializer(source='question', read_only=True)

    class Meta:
        model = ChoiceOption
        fields = ['id', 'question', 'question_details', 'option_text', 'is_correct']


# 18. пары соответствия
class MatchingPairSerializer(serializers.ModelSerializer):
    question_details = QuestionSerializer(source='question', read_only=True)

    class Meta:
        model = MatchingPair
        fields = ['id', 'question', 'question_details', 'left_text', 'right_text']


# 19. ответы пользователей
class UserAnswerSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    question_details = QuestionSerializer(source='question', read_only=True)

    class Meta:
        model = UserAnswer
        fields = [
            'id', 'user', 'user_details', 'question', 'question_details',
            'answer_text', 'answer_date', 'attempt_number', 'score'
        ]


# 20. выбранные варианты
class UserSelectedChoiceSerializer(serializers.ModelSerializer):
    user_answer_details = UserAnswerSerializer(source='user_answer', read_only=True)
    choice_details = ChoiceOptionSerializer(source='choice_option', read_only=True)

    class Meta:
        model = UserSelectedChoice
        fields = [
            'id', 'user_answer', 'user_answer_details',
            'choice_option', 'choice_details', 'selected_at'
        ]


# 21. ответы на сопоставления
class UserMatchingAnswerSerializer(serializers.ModelSerializer):
    user_answer_details = UserAnswerSerializer(source='user_answer', read_only=True)
    matching_pair_details = MatchingPairSerializer(source='matching_pair', read_only=True)

    class Meta:
        model = UserMatchingAnswer
        fields = [
            'id', 'user_answer', 'user_answer_details',
            'matching_pair', 'matching_pair_details',
            'user_selected_right_text', 'selected_at'
        ]


# 22. результаты тестов
class TestResultSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    test_details = TestSerializer(source='test', read_only=True)

    class Meta:
        model = TestResult
        fields = [
            'id', 'user', 'user_details', 'test', 'test_details',
            'completion_date', 'final_score', 'is_passed',
            'attempt_number', 'time_spent'
        ]


# 23. сертификаты
class CertificateSerializer(serializers.ModelSerializer):
    user_course_details = UserCourseSerializer(source='user_course', read_only=True)
    score_data = serializers.SerializerMethodField(read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'user_course', 'user_course_details',
            'certificate_number', 'issue_date', 'certificate_file_path',
            'score_data'
        ]
    
    def get_score_data(self, obj):
        from unireax_main.utils.certificate_generator import calculate_total_course_score
        user = obj.user_course.user
        course = obj.user_course.course
        return calculate_total_course_score(user.id, course.id)


# 24. файлы сдачи заданий
class AssignmentSubmissionFileSerializer(serializers.ModelSerializer):
    user_assignment_details = UserPracticalAssignmentSerializer(source='user_assignment', read_only=True)

    class Meta:
        model = AssignmentSubmissionFile
        fields = [
            'id', 'user_assignment', 'user_assignment_details',
            'file', 'uploaded_at', 'file_name', 'file_size', 'description'
        ]


# 25. файлы преподавателей
class TeacherAssignmentFileSerializer(serializers.ModelSerializer):
    assignment_details = PracticalAssignmentSerializer(source='practical_assignment', read_only=True)
    uploaded_by_details = UserSerializer(source='uploaded_by', read_only=True)
    file_size_mb = serializers.ReadOnlyField()

    class Meta:
        model = TeacherAssignmentFile
        fields = [
            'id', 'practical_assignment', 'assignment_details',
            'file_path', 'original_filename', 'file_type',
            'uploaded_by', 'uploaded_by_details', 'uploaded_at',
            'file_size', 'file_size_mb', 'is_active'
        ]


# 26. коды восстановления
class PasswordResetCodeSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    is_valid = serializers.ReadOnlyField()

    class Meta:
        model = PasswordResetCode
        fields = [
            'id', 'user', 'user_details', 'code',
            'created_at', 'is_used', 'is_valid'
        ]

# аутентификация
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        username = data.get('username')
        password = data.get('password')

        if username and password:
            user = authenticate(username=username, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError("Аккаунт пользователя деактивирован")
                data['user'] = user
                return data
            raise serializers.ValidationError("Неверное имя пользователя или пароль")
        raise serializers.ValidationError("Требуется имя пользователя и пароль")


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=6)
    confirm_password = serializers.CharField(write_only=True, min_length=6)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'confirm_password', 
                  'first_name', 'last_name']

    def validate(self, data):
        if data['password'] != data['confirm_password']:
            raise serializers.ValidationError({"password": "Пароли не совпадают"})
        return data

    def create(self, validated_data):
        validated_data.pop('confirm_password')
        user = User.objects.create_user(**validated_data)
        return user


class ListenerCourseSerializer(serializers.ModelSerializer):
    """Сериализатор курсов для слушателей"""
    calculated_rating = serializers.FloatField(read_only=True)
    review_count = serializers.IntegerField(read_only=True)
    enrolled_count = serializers.IntegerField(read_only=True)
    is_enrolled = serializers.SerializerMethodField()
    can_enroll = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'course_name', 'course_description', 'course_price',
            'course_category', 'course_type', 'has_certificate',
            'course_max_places', 'course_hours', 'is_completed',
            'course_photo_path', 'calculated_rating', 'review_count',
            'enrolled_count', 'is_enrolled', 'can_enroll', 'created_at'
        ]
    
    def get_is_enrolled(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return UserCourse.objects.filter(
                user=request.user,
                course=obj,
                is_active=True
            ).exists()
        return False
    
    def get_can_enroll(self, obj):
        can_enroll, message = obj.can_enroll()
        return can_enroll

class ListenerTestResultSerializer(serializers.ModelSerializer):
    """Сериализатор результатов тестов для слушателей"""
    test_name = serializers.CharField(source='test.test_name', read_only=True)
    course_name = serializers.CharField(source='test.lecture.course.course_name', read_only=True)
    
    class Meta:
        model = TestResult
        fields = [
            'id', 'test', 'test_name', 'course_name',
            'completion_date', 'final_score', 'is_passed',
            'attempt_number', 'time_spent'
        ]

class ListenerAssignmentWithFeedbackSerializer(serializers.ModelSerializer):
    """Сериализатор заданий с обратной связью для слушателей"""
    assignment_name = serializers.CharField(source='practical_assignment.practical_assignment_name', read_only=True)
    course_name = serializers.CharField(source='practical_assignment.lecture.course.course_name', read_only=True)
    feedback = serializers.SerializerMethodField()
    
    class Meta:
        model = UserPracticalAssignment
        fields = [
            'id', 'practical_assignment', 'assignment_name', 'course_name',
            'submission_date', 'submission_status', 'attempt_number',
            'comment', 'submitted_at', 'feedback'
        ]
    
    def get_feedback(self, obj):
        feedback = Feedback.objects.filter(user_practical_assignment=obj).first()
        if feedback:
            return FeedbackSerializer(feedback).data
        return None
    

class TestQuestionSerializer(serializers.ModelSerializer):
    """Сериализатор вопросов теста для мобильного приложения"""
    answer_type = serializers.SerializerMethodField()
    choiceoption_set = serializers.SerializerMethodField()
    matchingpair_set = serializers.SerializerMethodField()
    
    class Meta:
        model = Question
        fields = [
            'id', 'question_text', 'question_score', 
            'question_order', 'correct_text',
            'answer_type', 'choiceoption_set', 'matchingpair_set'
        ]
    
    def get_answer_type(self, obj):
        """Возвращение название типа ответа как строку"""
        return obj.answer_type.answer_type_name
    
    def get_choiceoption_set(self, obj):
        """Получение вариантов ответов"""
        
        if obj.answer_type.answer_type_name in ['Выбор одного', 'Выбор нескольких']:
            from .models import ChoiceOption
            
            try:
                choices = ChoiceOption.objects.filter(question=obj)
                
                if hasattr(obj, 'choice_options'):
                    choices = obj.choice_options.all()
                
                choices = obj.choiceoption_set.all()
                
                if not choices.exists():
                    return [
                        {'id': 1, 'option_text': 'Тестовый вариант 1'},
                        {'id': 2, 'option_text': 'Тестовый вариант 2'},
                        {'id': 3, 'option_text': 'Тестовый вариант 3'},
                    ]
                
                return [
                    {
                        'id': choice.id,
                        'option_text': choice.option_text,
                    }
                    for choice in choices
                ]
                
            except Exception as e:
                return [
                    {'id': 1, 'option_text': 'Вариант А (ошибка загрузки)'},
                    {'id': 2, 'option_text': 'Вариант Б'},
                ]
        
        return []
    
    def get_matchingpair_set(self, obj):
        """Получаем пары соответствия"""
        if obj.answer_type.answer_type_name == 'Сопоставление':
            pairs = obj.matchingpair_set.all()
            return [
                {
                    'id': pair.id,
                    'left_text': pair.left_text,
                }
                for pair in pairs
            ]
        return []
    

class ChoiceOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ChoiceOption
        fields = ['id', 'option_text', 'is_correct']

class MatchingPairSerializer(serializers.ModelSerializer):
    class Meta:
        model = MatchingPair
        fields = ['id', 'left_text', 'right_text']

class QuestionDetailSerializer(serializers.ModelSerializer):
    answer_type = serializers.CharField(source='answer_type.answer_type_name')
    choices = ChoiceOptionSerializer(many=True, read_only=True)
    matching_pairs = MatchingPairSerializer(many=True, read_only=True)
    
    class Meta:
        model = Question
        fields = ['id', 'question_text', 'question_score', 'question_order', 
                  'answer_type', 'choices', 'matching_pairs', 'correct_text']
        

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)


class PasswordResetVerifySerializer(serializers.Serializer):
    """Сериализатор для верификации кода"""
    code = serializers.CharField(max_length=6, min_length=6, required=True)
    email = serializers.EmailField(required=True)
    
    def validate(self, data):
        email = data['email']
        code = data['code']
        
        try:
            user = User.objects.get(email=email)
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).order_by('-created_at').first()
            
            if not reset_code:
                raise serializers.ValidationError({"code": "Неверный код подтверждения"})
            
            if not reset_code.is_valid():
                raise serializers.ValidationError({"code": "Срок действия кода истек"})
            
            data['user'] = user
            data['reset_code'] = reset_code
            
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "Пользователь с таким email не найден"})
        
        return data


class PasswordResetConfirmSerializer(serializers.Serializer):
    """Сериализатор для подтверждения сброса пароля"""
    code = serializers.CharField(required=True, min_length=6, max_length=6)
    email = serializers.EmailField(required=True)
    new_password = serializers.CharField(required=True, min_length=8, write_only=True)
    confirm_password = serializers.CharField(required=True, min_length=8, write_only=True)
    
    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"confirm_password": "Пароли не совпадают"})

        email = data['email']
        code = data['code']
        
        try:
            user = User.objects.get(email=email)
            reset_code = PasswordResetCode.objects.filter(
                user=user,
                code=code,
                is_used=False
            ).order_by('-created_at').first()
            
            if not reset_code:
                raise serializers.ValidationError({"code": "Неверный или уже использованный код"})
            
            if not reset_code.is_valid():
                raise serializers.ValidationError({"code": "Срок действия кода истек"})
            
            data['user'] = user
            data['reset_code'] = reset_code
            
        except User.DoesNotExist:
            raise serializers.ValidationError({"email": "Пользователь с таким email не найден"})
        
        return data
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, min_length=8)
    confirm_password = serializers.CharField(required=True, min_length=8)

    def validate(self, data):
        if data['new_password'] != data['confirm_password']:
            raise serializers.ValidationError({"new_password": "Пароли не совпадают"})
        return data
    
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})
    remember_me = serializers.BooleanField(default=False, required=False)

class LoginResponseSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()
    user_id = serializers.IntegerField()
    username = serializers.CharField()
    email = serializers.EmailField()
    first_name = serializers.CharField()
    last_name = serializers.CharField()

class ErrorResponseSerializer(serializers.Serializer):
    error = serializers.BooleanField()
    blocked = serializers.BooleanField(default=False)
    message = serializers.CharField()
    remaining_attempts = serializers.IntegerField(required=False)
    minutes_left = serializers.IntegerField(required=False)

class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()

class PasswordResetConfirmSerializer(serializers.Serializer):
    email = serializers.EmailField()
    code = serializers.CharField(max_length=6)
    new_password = serializers.CharField(min_length=6, write_only=True)

class TokenRefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# 27. избранные курсы
class FavoriteCourseSerializer(serializers.ModelSerializer):
    course_details = CourseSerializer(source='course', read_only=True)
    user_details = UserSerializer(source='user', read_only=True)
    
    class Meta:
        model = FavoriteCourse
        fields = [
            'id', 'user', 'user_details', 'course', 'course_details', 'added_at'
        ]
        read_only_fields = ['added_at']


# 28. сериализаторы для избранного
class FavoriteCourseListSerializer(serializers.ModelSerializer):
    """Сериализатор для списка избранных курсов с дополнительной информацией"""
    id = serializers.IntegerField(source='course.id')
    course_name = serializers.CharField(source='course.course_name')
    course_description = serializers.CharField(source='course.course_description')
    course_price = serializers.DecimalField(source='course.course_price', max_digits=10, decimal_places=2)
    course_photo_path = serializers.CharField(source='course.course_photo_path')
    course_hours = serializers.IntegerField(source='course.course_hours')
    has_certificate = serializers.BooleanField(source='course.has_certificate')
    avg_rating = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()
    category_name = serializers.CharField(source='course.course_category.course_category_name', read_only=True)
    added_at = serializers.DateTimeField()
    
    class Meta:
        model = FavoriteCourse
        fields = [
            'id', 'course_name', 'course_description', 'course_price',
            'course_photo_path', 'course_hours', 'has_certificate',
            'avg_rating', 'student_count', 'category_name', 'added_at'
        ]
    
    def get_avg_rating(self, obj):
        from django.db.models import Avg, Q
        rating = obj.course.review_set.filter(is_approved=True).aggregate(
            avg=Avg('rating')
        )['avg']
        return float(rating) if rating else 0.0
    
    def get_student_count(self, obj):
        return obj.course.usercourse_set.filter(is_active=True).count()


class ToggleFavoriteSerializer(serializers.Serializer):
    """Сериализатор для переключения избранного"""
    course_id = serializers.IntegerField()
    is_favorited = serializers.BooleanField(read_only=True)


class DeactivateAccountSerializer(serializers.Serializer):
    """Сериализатор для деактивации аккаунта"""
    password = serializers.CharField(write_only=True, required=True)
    confirm = serializers.BooleanField(required=True)
    
    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Неверный пароль")
        return value
    
    def validate_confirm(self, value):
        if not value:
            raise serializers.ValidationError("Подтвердите деактивацию аккаунта")
        return value
    

# 29. сериализаторы для постов и комментариев
class CreatePostSerializer(serializers.ModelSerializer):
    """Сериализатор для создания поста"""
    
    class Meta:
        model = CoursePost
        fields = ['title', 'content', 'post_type', 'is_pinned']


class CreateCommentSerializer(serializers.ModelSerializer):
    """Сериализатор для создания комментария"""
    parent_id = serializers.IntegerField(
        required=False,
        allow_null=True,
        write_only=True
    )
    
    class Meta:
        model = CoursePostComment
        fields = ['content', 'parent_id']

class CoursePostCommentSerializer(serializers.ModelSerializer):
    """Сериализатор для комментариев к постам"""
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    replies = serializers.SerializerMethodField()
    
    class Meta:
        model = CoursePostComment
        fields = ['id', 'content', 'created_at', 'author', 'author_name', 'author_role', 'parent', 'can_delete', 'replies']
    
    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username
    
    def get_author_role(self, obj):
        return obj.author.role.role_name if obj.author.role else ''
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return request.user.is_admin or obj.author == request.user
        return False
    
    def get_replies(self, obj):
        request = self.context.get('request')
        replies = obj.replies.all()
        return CoursePostCommentSerializer(replies, many=True, context={'request': request}).data


class CoursePostSerializer(serializers.ModelSerializer):
    """Сериализатор для постов"""
    author_name = serializers.SerializerMethodField()
    author_role = serializers.SerializerMethodField()
    post_type_display = serializers.SerializerMethodField()
    comments_count = serializers.SerializerMethodField()
    can_edit = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    comments = serializers.SerializerMethodField()
    
    class Meta:
        model = CoursePost
        fields = [
            'id', 'title', 'content', 'post_type', 'post_type_display',
            'is_pinned', 'is_active', 'created_at', 'updated_at',
            'author', 'author_name', 'author_role', 'course', 
            'comments_count', 'can_edit', 'can_delete', 'comments'
        ]
    
    def get_author_name(self, obj):
        return obj.author.get_full_name() or obj.author.username
    
    def get_author_role(self, obj):
        return obj.author.role.role_name if obj.author.role else ''
    
    def get_post_type_display(self, obj):
        return dict(CoursePost.POST_TYPES).get(obj.post_type, 'Объявление')
    
    def get_comments_count(self, obj):
        return obj.comments.count()
    
    def get_can_edit(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return request.user.is_admin or obj.author == request.user
        return False
    
    def get_can_delete(self, obj):
        request = self.context.get('request')
        if request and request.user:
            return request.user.is_admin or obj.author == request.user
        return False
    
    def get_comments(self, obj):
        request = self.context.get('request')
        comments = obj.comments.filter(parent__isnull=True)
        return CoursePostCommentSerializer(comments, many=True, context={'request': request}).data