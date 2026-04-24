from django.urls import path
from . import views

app_name = 'methodist_app'

urlpatterns = [
    
    # профиль
    path('profile/', views.methodist_profile, name='profile'),
    
    # дашборд
    path('', views.methodist_dashboard, name='dashboard'),
    
    # статистика
    path('statistics/', views.methodist_statistics, name='statistics'),
    
    # курсы
    path('course/create/', views.methodist_course_builder, name='course_builder'),
    path('course/<int:course_id>/', views.methodist_course_builder, name='course_builder'),
    path('course/<int:course_id>/detail/', views.methodist_course_detail, name='course_detail'),
    path('course/<int:course_id>/delete/', views.methodist_course_delete, name='course_delete'),
    
    # лекции
    path('course/<int:course_id>/lecture/create/', views.methodist_lecture_create, name='lecture_create'),
    path('lecture/<int:lecture_id>/edit/', views.methodist_lecture_edit, name='lecture_edit'),
    path('lecture/<int:lecture_id>/delete/', views.methodist_lecture_delete, name='lecture_delete'),
    
    # практические задания
    path('course/<int:course_id>/assignment/create/', views.methodist_assignment_create, name='assignment_create'),
    path('assignment/<int:assignment_id>/edit/', views.methodist_assignment_edit, name='assignment_edit'),
    path('assignment/<int:assignment_id>/delete/', views.methodist_assignment_delete, name='assignment_delete'),
    
    # тесты
    path('course/<int:course_id>/test/create/', views.methodist_test_create, name='test_create'),
    path('test/<int:test_id>/edit/', views.methodist_test_edit, name='test_edit'),
    path('test/<int:test_id>/delete/', views.methodist_test_delete, name='test_delete'),
    path('test/<int:test_id>/builder/', views.methodist_test_builder, name='test_builder'),
    
    # вопросы
    path('question/<int:question_id>/edit/', views.methodist_question_edit, name='question_edit'),
    path('question/<int:question_id>/delete/', views.methodist_question_delete, name='question_delete'),
    path('choice-option/<int:option_id>/delete/', views.methodist_choice_option_delete, name='choice_option_delete'),
    path('matching-pair/<int:pair_id>/delete/', views.methodist_matching_pair_delete, name='matching_pair_delete'),
    path('export/<str:export_type>/<str:format_type>/', views.export_statistics, name='export_statistics'),
    path('teacher-applications/', views.methodist_teacher_applications, name='teacher_applications'),
    path('teacher-applications/<int:application_id>/', views.methodist_application_detail, name='application_detail'),
    path('profile/deactivate/', views.methodist_deactivate_account, name='deactivate_account'),
    
]