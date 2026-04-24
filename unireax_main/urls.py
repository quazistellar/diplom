from django.contrib import admin
from django.urls import path, include

from . import views
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.main_page, name='main_page'),  
    path('login/', views.login_page, name='login_page'),
    path('logout/', views.logout_view, name='logout_move'),
    path('profile/', views.profile_page, name='profile_page'),
    path('courses/', views.courses_page, name='courses_page'),
    path('details-course/<int:course_id>/', views.course_detail, name='course_detail'),
    path('course/<int:course_id>/add_review/', views.add_review, name='add_review'),
    path('search/', views.search_courses, name='search_courses'), 
    path('about/', views.about_page, name='about_page'),
    path('teachers/', views.teachers_page, name='teachers_page'),
    path('feedback/', views.feedback_page, name='feedback_page'),

    path('register/listener/', views.register_listener, name='register_listener'),
    path('register/teacher-methodist/', views.register_teacher_methodist, name='register_teacher_methodist'),
    path('register/verify/', views.verify_registration, name='verify_registration'),
    path('register/resend-code/', views.resend_verification_code, name='resend_verification_code'),

    path('privacy-notice/', TemplateView.as_view(template_name='privacy_notice.html'), name='privacy_notice'),
    path('site-policy/', TemplateView.as_view(template_name='site_policy.html'), name='site_policy'),

    path('profile/unverified/', views.unverified_profile, name='unverified_profile'),

    path('password-reset/', views.password_reset_request, name='password_reset_req'),
    path('password-reset/verify/', views.password_reset_verify, name='password_reset_verif'),
    path('password-reset/resend-code/', views.password_reset_resend_code, name='password_reset_resend_code'),
    path('password-reset/confirm/', views.password_reset_confirm, name='password_reset_conf'),

]

