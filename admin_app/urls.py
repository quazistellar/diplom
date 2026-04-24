from django.urls import path
from . import views

app_name = 'admin_app'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('logs/', views.logs_page, name='logs_page'),
    path('backup/', views.BackupDatabaseView.as_view(), name='backup_database'),
    path('admin-dashboard/', views.dashboard, name='dashboard'),  
    path('profile/', views.admin_profile_view, name='admin_profile'),
    
    # категории
    path('categories/', views.category_list, name='category_list'),
    path('categories/create/', views.category_create, name='category_create'),
    path('categories/<int:pk>/', views.category_detail, name='category_detail'),
    path('categories/<int:pk>/edit/', views.category_edit, name='category_edit'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
    
    # пользователи
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('users/<int:pk>/', views.user_detail, name='user_detail'),
    path('users/<int:pk>/edit/', views.user_edit, name='user_edit'),
    path('users/<int:pk>/delete/', views.user_delete, name='user_delete'),
    path('user-verification/', views.admin_user_verification_list, name='admin_user_verification_list'),
    path('user-verification/<int:user_id>/', views.admin_user_verification_detail, name='admin_user_verification_detail'),
    
    # курсы
    path('courses/', views.course_list, name='course_list'),
    path('courses/create/', views.course_create, name='course_create'),
    path('courses/<int:pk>/', views.course_detail, name='course_detail'),
    path('courses/<int:pk>/edit/', views.course_edit, name='course_edit'),
    path('courses/<int:pk>/delete/', views.course_delete, name='course_delete'),
    
    # слушатели и курсы
    path('user-courses/', views.user_course_list, name='user_course_list'),
    path('user-courses/create/', views.user_course_create, name='user_course_create'),
    path('user-courses/<int:pk>/', views.user_course_detail, name='user_course_detail'),
    path('user-courses/<int:pk>/edit/', views.user_course_edit, name='user_course_edit'),
    path('user-courses/<int:pk>/delete/', views.user_course_delete, name='user_course_delete'),
    
    # персонал и курсы
    path('course-teachers/', views.course_teacher_list, name='course_teacher_list'),
    path('course-teachers/create/', views.course_teacher_create, name='course_teacher_create'),
    path('course-teachers/<int:pk>/', views.course_teacher_detail, name='course_teacher_detail'),
    path('course-teachers/<int:pk>/edit/', views.course_teacher_edit, name='course_teacher_edit'),
    path('course-teachers/<int:pk>/delete/', views.course_teacher_delete, name='course_teacher_delete'),
]