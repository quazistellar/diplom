from django.urls import path
from . import views

app_name = 'listener_app'

urlpatterns = [
    path('', views.listener_dashboard, name='dashboard'),
    path('listener-profile/', views.listener_profile, name='listener_profile'),
    
    path('my-courses/', views.my_courses, name='my_courses'),
    # path('course/<int:course_id>/', views.listener_course_detail, name='course_detail'),
    path('course/<int:course_id>/', views.listener_course_detail, name='course_detail'),

    path('course/<int:course_id>/study/', views.course_study, name='course_study'),
    path('course/<int:course_id>/continue/', views.continue_course, name='continue_course'),
    path('course/<int:course_id>/exit/', views.exit_course, name='exit_course'),
    path('course/<int:course_id>/return/', views.return_to_course, name='return_to_course'),
    
    path('lecture/<int:lecture_id>/', views.lecture_detail, name='lecture_detail'),
    
    path('test/<int:test_id>/start/', views.test_start, name='test_start'),
    path('test/<int:test_id>/submit/', views.test_submit, name='test_submit'),
    path('course/<int:course_id>/test-results/', views.test_results_list, name='test_results_list'),
    path('test-result/<int:result_id>/', views.test_result_detail, name='test_result_detail'),
    
    path('practical/<int:assignment_id>/submit/', views.practical_submit, name='practical_submit'),
    path('course/<int:course_id>/graded-assignments/', views.graded_assignments, name='graded_assignments'),
    
    path('course/<int:course_id>/statistics/', views.student_statistics, name='statistics'),
    
    path('certificates/', views.my_certificates, name='my_certificates'),
    path('certificate/<int:certificate_id>/', views.certificate_detail, name='certificate_detail'),
    path('certificate/<int:certificate_id>/download/', views.download_certificate, name='download_certificate'),
    path('course/<int:course_id>/check-certificate/', views.check_certificate_eligibility, name='check_certificate_eligibility'),
    path('course/<int:course_id>/generate-certificate/', views.generate_certificate, name='generate_certificate'),
    path('certificate/<int:certificate_id>/regenerate/', views.regenerate_certificate, name='regenerate_certificate'),
    
    path('favorite/toggle/<int:course_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('favorite/', views.favorite_courses, name='favorite_courses'),
    path('favorite/remove/<int:favorite_id>/', views.remove_favorite, name='remove_favorite'),
    
    path('course/<int:course_id>/progress/', views.course_progress, name='course_progress'),
    
    path('course/<int:course_id>/add-review/', views.add_review, name='add_review'),
    path('course/<int:course_id>/edit-review/<int:review_id>/', views.edit_review, name='edit_review'),
    path('course/<int:course_id>/delete-review/<int:review_id>/', views.delete_review, name='delete_review'),

    path('payment/create/<int:course_id>/', views.create_payment, name='create_payment'),
    path('payment/success/<int:course_id>/<str:payment_id>/', views.payment_success, name='payment_success'),
    path('payment/cancel/<int:course_id>/', views.payment_cancel, name='payment_cancel'),
    path('payment/receipt/<int:course_id>/<str:payment_id>/', views.download_receipt, name='payment_receipt'),

    path('profile/deactivate/', views.listener_deactivate_account, name='deactivate_account'),
    path('profile/payments/', views.payment_history, name='payment_history'),

    path('api/course/<int:course_id>/posts/', views.get_course_posts, name='get_course_posts'),
    path('api/course/<int:course_id>/post/create/', views.create_course_post, name='create_course_post'),
    path('api/post/<int:post_id>/edit/', views.edit_course_post, name='edit_course_post'),
    path('api/post/<int:post_id>/delete/', views.delete_course_post, name='delete_course_post'),
    path('api/post/<int:post_id>/comment/', views.add_course_comment, name='add_course_comment'),
    path('api/comment/<int:comment_id>/delete/', views.delete_course_comment, name='delete_course_comment'),
    
    
]