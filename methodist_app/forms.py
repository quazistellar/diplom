from django import forms
from unireax_main.models import (
    Course, Lecture, PracticalAssignment, Test, Question, 
    ChoiceOption, MatchingPair, AnswerType
)

class CourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'course_name', 'course_description', 'course_price', 
            'course_category', 'course_type', 'course_photo_path',
            'has_certificate', 'course_max_places', 'course_hours',
            'is_completed', 'code_link', 'is_active', 'is_find_teacher' 
        ]
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название курса'}),
            'course_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Описание курса'}),
            'course_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'course_category': forms.Select(attrs={'class': 'form-control'}),
            'course_type': forms.Select(attrs={'class': 'form-control'}),
            'course_photo_path': forms.FileInput(attrs={'class': 'form-control'}),
            'has_certificate': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'course_max_places': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Не ограничено'}),
            'course_hours': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Количество часов'}),
            'is_completed': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'code_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_find_teacher': forms.CheckboxInput(attrs={'class': 'form-check-input'}),  
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course_price'].required = False
        self.fields['course_max_places'].required = False
        self.fields['course_photo_path'].required = False
        self.fields['code_link'].required = False
        self.fields['course_description'].required = False
        self.fields['is_find_teacher'].required = False  

class LectureForm(forms.ModelForm):
    class Meta:
        model = Lecture
        fields = ['lecture_name', 'lecture_content', 'lecture_document_path', 'lecture_order', 'is_active']
        widgets = {
            'lecture_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название лекции'}),
            'lecture_content': forms.Textarea(attrs={'class': 'form-control', 'rows': 10, 'placeholder': 'Содержание лекции'}),
            'lecture_document_path': forms.FileInput(attrs={'class': 'form-control'}),
            'lecture_order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Порядковый номер'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.course_id = kwargs.pop('course_id', None)  
        super().__init__(*args, **kwargs)
        self.fields['lecture_document_path'].required = False
    
    def clean_lecture_order(self):
        lecture_order = self.cleaned_data.get('lecture_order')
        
        if lecture_order is None:
            raise forms.ValidationError('Порядковый номер лекции обязателен')
        
        if lecture_order <= 0:
            raise forms.ValidationError('Порядковый номер должен быть положительным числом')
        
        if self.instance.pk:
            if Lecture.objects.filter(
                course_id=self.instance.course_id, 
                lecture_order=lecture_order, 
                is_active=True
            ).exclude(id=self.instance.pk).exists():
                raise forms.ValidationError(f'Лекция с порядковым номером {lecture_order} уже существует в этом курсе')
        else:
            if self.course_id and Lecture.objects.filter(
                course_id=self.course_id, 
                lecture_order=lecture_order, 
                is_active=True
            ).exists():
                raise forms.ValidationError(f'Лекция с порядковым номером {lecture_order} уже существует в этом курсе')
        
        return lecture_order

class PracticalAssignmentForm(forms.ModelForm):
    class Meta:
        model = PracticalAssignment
        fields = [
            'practical_assignment_name',
            'practical_assignment_description',
            'lecture',
            'grading_type',
            'max_score',
            'passing_score',
            'assignment_criteria',
            'assignment_deadline',
            'assignment_document_path',
            'is_active',
            'is_can_pin_after_deadline',
        ]
        widgets = {
            'practical_assignment_description': forms.Textarea(attrs={'rows': 5}),
            'assignment_criteria': forms.Textarea(attrs={'rows': 4}),
            'assignment_deadline': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
        }
    
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id', None)
        super().__init__(*args, **kwargs)
        
        if course_id:
            self.fields['lecture'].queryset = Lecture.objects.filter(
                course_id=course_id,
                is_active=True
            ).order_by('lecture_order')
        
        for field in self.fields:
            self.fields[field].widget.attrs.update({'class': 'form-control'})

class TestForm(forms.ModelForm):
    class Meta:
        model = Test
        fields = [
            'test_name', 'test_description', 'is_final', 'lecture',
            'max_attempts', 'grading_form', 'passing_score', 'is_active'
        ]
        widgets = {
            'test_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Название теста'}),
            'test_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Описание теста'}),
            'is_final': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'lecture': forms.Select(attrs={'class': 'form-control'}),
            'max_attempts': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Не ограничено'}),
            'grading_form': forms.Select(attrs={'class': 'form-control'}),
            'passing_score': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Проходной балл'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        course_id = kwargs.pop('course_id', None)
        super().__init__(*args, **kwargs)
        
        self.fields['test_description'].required = False
        self.fields['max_attempts'].required = False
        self.fields['passing_score'].required = False
        
        if course_id:
            self.fields['lecture'].queryset = Lecture.objects.filter(
                course_id=course_id, 
                is_active=True
            ).order_by('lecture_order')
        
        elif self.instance and self.instance.pk and self.instance.lecture:
            self.fields['lecture'].queryset = Lecture.objects.filter(
                course=self.instance.lecture.course,
                is_active=True
            ).order_by('lecture_order')
    
    def clean(self):
        cleaned_data = super().clean()
        grading_form = cleaned_data.get('grading_form')
        passing_score = cleaned_data.get('passing_score')
        lecture = cleaned_data.get('lecture')
        
        if self.instance and self.instance.pk and lecture:
            if lecture.course != self.instance.lecture.course:
                self.add_error('lecture', 'Выбранная лекция не принадлежит курсу этого теста')
        
        if grading_form == 'points' and not passing_score:
            self.add_error('passing_score', 'Для формы оценки "По баллам" необходимо указать проходной балл')
        
        return cleaned_data
    
class QuestionForm(forms.ModelForm):
    """Форма для создания/редактирования вопроса"""
    
    class Meta:
        model = Question
        fields = ['question_text', 'answer_type', 'question_score', 'question_order', 'correct_text']
        widgets = {
            'question_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Введите текст вопроса'}),
            'answer_type': forms.Select(attrs={'class': 'form-control', 'id': 'answer-type-select'}),
            'question_score': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Балл за вопрос', 'min': 1, 'max': 100}),
            'question_order': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Порядковый номер вопроса', 'min': 1}),
            'correct_text': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Введите правильный ответ'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.test_id = kwargs.pop('test_id', None)
        super().__init__(*args, **kwargs)
        self.fields['correct_text'].required = False
        self.fields['question_score'].initial = 1
        self.fields['question_order'].required = False  
    
    def clean_question_order(self):
        question_order = self.cleaned_data.get('question_order')
        
        if question_order is None or question_order == '':
            return None
        
        try:
            question_order = int(question_order)
        except (TypeError, ValueError):
            raise forms.ValidationError('Порядковый номер должен быть числом')
        
        if question_order <= 0:
            raise forms.ValidationError('Порядковый номер должен быть положительным числом')

        if self.instance.pk:
            if Question.objects.filter(
                test=self.instance.test, 
                question_order=question_order
            ).exclude(pk=self.instance.pk).exists():
                raise forms.ValidationError(f'Вопрос с порядковым номером {question_order} уже существует в этом тесте')
        else:
            if self.test_id and Question.objects.filter(
                test_id=self.test_id, 
                question_order=question_order
            ).exists():
                raise forms.ValidationError(f'Вопрос с порядковым номером {question_order} уже существует в этом тесте')
        
        return question_order


class ChoiceOptionForm(forms.ModelForm):
    class Meta:
        model = ChoiceOption
        fields = ['option_text', 'is_correct']
        widgets = {
            'option_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Текст варианта ответа'}),
            'is_correct': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }


class MatchingPairForm(forms.ModelForm):
    class Meta:
        model = MatchingPair
        fields = ['left_text', 'right_text']
        widgets = {
            'left_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Левый элемент'}),
            'right_text': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Правый элемент'}),
        }