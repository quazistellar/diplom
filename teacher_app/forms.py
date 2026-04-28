from django import forms
from unireax_main.models import (
    Course, Lecture, PracticalAssignment, Test, Question, 
    ChoiceOption, MatchingPair, AnswerType, CourseCategory, CourseType
)


class TeacherCourseForm(forms.ModelForm):
    class Meta:
        model = Course
        fields = [
            'course_name',
            'course_description',
            'course_category',
            'course_hours',
            'course_max_places',
            'code_link',
            'course_photo_path',
            'is_active',
        ]
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название курса'}),
            'course_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Опишите курс'}),
            'course_category': forms.Select(attrs={'class': 'form-control'}),
            'course_hours': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Количество часов'}),
            'course_max_places': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Максимум мест (оставьте пустым если без ограничений)'}),
            'code_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://...'}),
            'course_photo_path': forms.FileInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'course_name': 'Название курса',
            'course_description': 'Описание курса',
            'course_category': 'Категория',
            'course_hours': 'Количество часов',
            'course_max_places': 'Максимум мест',
            'code_link': 'Ссылка на видеовстречу',
            'course_photo_path': 'Изображение курса',
            'is_active': 'Курс активен',
        }
        help_texts = {
            'course_name': 'Название курса (3-200 символов)',
            'course_description': 'Краткое описание курса (до 300 символов)',
            'course_hours': 'Общая продолжительность курса в часах',
            'course_max_places': 'Оставьте пустым, если нет ограничений',
            'code_link': 'Ссылка на Яндекс.Телемост или другую платформу',
            'course_photo_path': 'Изображение курса (JPG, JPEG, PNG)',
            'is_active': 'Если убрать галочку, курс станет недоступным для слушателей',
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not kwargs.get('instance'):
            self.initial['is_active'] = True

class TeacherGradeForm(forms.Form):
    """Форма для оценивания работы слушателя"""
    
    score = forms.IntegerField(
        required=False,
        min_value=0,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Введите баллы'})
    )
    is_passed = forms.ChoiceField(
        required=False,
        choices=[('', '---'), ('true', 'Зачёт'), ('false', 'Незачёт')],
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    comment_feedback = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 5, 'placeholder': 'Оставьте комментарий к работе...'})
    )
    
    def clean(self):
        cleaned_data = super().clean()
        score = cleaned_data.get('score')
        is_passed = cleaned_data.get('is_passed')
        
        if score is None and not is_passed:
            raise forms.ValidationError('Укажите баллы или зачёт/незачёт')
        
        return cleaned_data