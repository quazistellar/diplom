from django import forms
from unireax_main.models import (
    Course, Lecture, PracticalAssignment, Test, Question, 
    ChoiceOption, MatchingPair, AnswerType, CourseCategory, CourseType
)


class TeacherCourseForm(forms.ModelForm):
    """Форма для создания/редактирования курса преподавателем (только тип 'Классная комната')"""
    
    class Meta:
        model = Course
        fields = [
            'course_name', 'course_description', 'course_price', 
            'course_category', 'course_photo_path',
            'has_certificate', 'course_max_places', 'course_hours',
            'code_link', 'is_active'
        ]
        widgets = {
            'course_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Введите название курса'}),
            'course_description': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'Описание курса'}),
            'course_price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '0.00'}),
            'course_category': forms.Select(attrs={'class': 'form-control'}),
            'course_photo_path': forms.FileInput(attrs={'class': 'form-control'}),
            'has_certificate': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'course_max_places': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Не ограничено'}),
            'course_hours': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Количество часов'}),
            'code_link': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['course_price'].required = False
        self.fields['course_max_places'].required = False
        self.fields['course_photo_path'].required = False
        self.fields['code_link'].required = False
        self.fields['course_description'].required = False
        self.fields['course_category'].queryset = CourseCategory.objects.all()
        self.fields['course_category'].empty_label = "Выберите категорию"


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