from django.urls import path
from . import views

app_name = 'teacher_app'

urlpatterns = [
    path('profile/', views.teacher_profile, name='profile'),
    path('', views.teacher_dashboard, name='dashboard'),
    path('statistics/', views.teacher_statistics, name='statistics'),
    
    path('course/create/', views.teacher_course_create, name='course_create'),
    path('course/<int:course_id>/edit/', views.teacher_course_edit, name='course_edit'),
    path('course/<int:course_id>/delete/', views.teacher_course_delete, name='course_delete'),
    path('course/<int:course_id>/', views.teacher_course_detail, name='course_detail'),
    
    path('course/<int:course_id>/lecture/create/', views.teacher_lecture_create, name='lecture_create'),
    path('lecture/<int:lecture_id>/edit/', views.teacher_lecture_edit, name='lecture_edit'),
    path('lecture/<int:lecture_id>/delete/', views.teacher_lecture_delete, name='lecture_delete'),
    
    path('course/<int:course_id>/assignment/create/', views.teacher_assignment_create, name='assignment_create'),
    path('assignment/<int:assignment_id>/edit/', views.teacher_assignment_edit, name='assignment_edit'),
    path('assignment/<int:assignment_id>/delete/', views.teacher_assignment_delete, name='assignment_delete'),
    
    path('course/<int:course_id>/test/create/', views.teacher_test_create, name='test_create'),
    path('test/<int:test_id>/edit/', views.teacher_test_edit, name='test_edit'),
    path('test/<int:test_id>/delete/', views.teacher_test_delete, name='test_delete'),
    path('test/<int:test_id>/builder/', views.teacher_test_builder, name='test_builder'),
    
    path('question/<int:question_id>/edit/', views.teacher_question_edit, name='question_edit'),
    path('question/<int:question_id>/delete/', views.teacher_question_delete, name='question_delete'),
    path('choice-option/<int:option_id>/delete/', views.teacher_choice_option_delete, name='choice_option_delete'),
    path('matching-pair/<int:pair_id>/delete/', views.teacher_matching_pair_delete, name='matching_pair_delete'),
    
    path('course/<int:course_id>/listeners/', views.teacher_listeners_list, name='listeners_list'),
    path('course/<int:course_id>/upload-csv/', views.teacher_upload_listeners_csv, name='upload_listeners_csv'),
    path('course/<int:course_id>/generate-csv/', views.teacher_generate_listeners_csv, name='generate_listeners_csv'),
    path('course/<int:course_id>/listener/<int:student_id>/progress/', views.teacher_listener_progress, name='listener_progress'), 
    path('teacher/course/<int:course_id>/remove-listener/<int:user_id>/', views.teacher_remove_listener_from_course, name='remove_listener_from_course'),
    path('teacher/course/<int:course_id>/restore-listener/<int:user_course_id>/', views.teacher_restore_listener_to_course, name='restore_listener_to_course'),
    
    path('submission/<int:submission_id>/grade/', views.teacher_grade_assignment, name='grade_assignment'),
    
    path('export/<str:export_type>/<str:format_type>/', views.teacher_export_statistics, name='export_statistics'),

    path('pending/', views.teacher_pending_submissions, name='pending_submissions'),
    path('course/<int:course_id>/apply-for-teaching/', views.apply_for_teaching, name='apply_for_teaching'),

    path('profile/deactivate/', views.teacher_deactivate_account, name='deactivate_account'),
    
    path('course/<int:course_id>/posts/', views.teacher_course_posts_manage, name='course_posts_manage'),
    path('course/<int:course_id>/post/create/', views.teacher_course_post_create, name='course_post_create'),
    path('post/<int:post_id>/edit/', views.teacher_course_post_edit, name='course_post_edit'),
    path('post/<int:post_id>/delete/', views.teacher_course_post_delete, name='course_post_delete'),

    path('post/<int:post_id>/comment/add/', views.teacher_add_comment_to_post, name='teacher_add_comment_to_post'),
    path('comment/<int:comment_id>/delete/', views.teacher_delete_comment, name='teacher_delete_comment'),

]