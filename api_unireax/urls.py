from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views

router = DefaultRouter()
router.register('roles', views.RoleViewSet, basename='roles')
router.register('users', views.UserViewSet, basename='users')
router.register('course-categories', views.CourseCategoryViewSet, basename='course-categories')
router.register('course-types', views.CourseTypeViewSet, basename='course-types')
router.register('assignment-statuses', views.AssignmentStatusViewSet, basename='assignment-statuses')
router.register('courses', views.CourseViewSet, basename='courses')
router.register('course-teachers', views.CourseTeacherViewSet, basename='course-teachers')
router.register('lectures', views.LectureViewSet, basename='lectures')
router.register('practical-assignments', views.PracticalAssignmentViewSet, basename='practical-assignments')
router.register('user-practical-assignments', views.UserPracticalAssignmentViewSet, basename='user-practical-assignments')
router.register('user-courses', views.UserCourseViewSet, basename='user-courses')
router.register('feedback', views.FeedbackViewSet, basename='feedback')
router.register('reviews', views.ReviewViewSet, basename='reviews')
router.register('answer-types', views.AnswerTypeViewSet, basename='answer-types')
router.register('tests', views.TestViewSet, basename='tests')
router.register('questions', views.QuestionViewSet, basename='questions')
router.register('choice-options', views.ChoiceOptionViewSet, basename='choice-options')
router.register('matching-pairs', views.MatchingPairViewSet, basename='matching-pairs')
router.register('user-answers', views.UserAnswerViewSet, basename='user-answers')
router.register('user-selected-choices', views.UserSelectedChoiceViewSet, basename='user-selected-choices')
router.register('user-matching-answers', views.UserMatchingAnswerViewSet, basename='user-matching-answers')
router.register('test-results', views.TestResultViewSet, basename='test-results')
router.register('certificates', views.CertificateViewSet, basename='certificates')
router.register('assignment-submission-files', views.AssignmentSubmissionFileViewSet, basename='assignment-submission-files')
router.register('teacher-assignment-files', views.TeacherAssignmentFileViewSet, basename='teacher-assignment-files')
router.register('password-reset-codes', views.PasswordResetCodeViewSet, basename='password-reset-codes')
router.register('payments', views.PaymentViewSet, basename='payments')
router.register('favorites', views.FavoriteCourseViewSet, basename='favorites')

listener_router = DefaultRouter()
listener_router.register('courses', views.ListenerCourseViewSet, basename='listener-courses')
listener_router.register('assignments', views.ListenerAssignmentViewSet, basename='listener-assignments')
listener_router.register('reviews', views.ListenerReviewViewSet, basename='listener-reviews')
listener_router.register('certificates', views.ListenerCertificateViewSet, basename='listener-certificates')


urlpatterns = [
    path('listener/progress/', views.ListenerProgressViewSet.as_view({'get': 'list'}), name='listener-progress'),
    path('listener/progress/<int:course_id>/materials/', views.ListenerProgressViewSet.as_view({'get': 'course_materials'}), name='listener-progress-materials'),
    path('listener/progress/<int:course_id>/materials/<int:lecture_id>/', views.ListenerProgressViewSet.as_view({'get': 'lecture_detail'}), name='listener-lecture-detail'),
    path('listener/progress/<int:course_id>/assignments/<int:assignment_id>/', views.ListenerProgressViewSet.as_view({'get': 'assignment_detail'}), name='listener-assignment-detail'),
    path('listener/progress/<int:course_id>/assignments/<int:assignment_id>/submit/', views.ListenerProgressViewSet.as_view({'post': 'submit_assignment'}), name='listener-submit-assignment'),
    path('listener/results/', views.ListenerResultsView.as_view(), name='listener-results'),
    path('listener/courses/<int:course_id>/tests/<int:test_id>/', views.ListenerTestAPIView.as_view(), name='listener-test-detail'),
    path('listener/progress/<int:course_id>/assignments/<int:assignment_id>/submit', views.ListenerProgressViewSet.as_view({'post': 'submit_assignment'}), name='listener-submit-assignment-no-slash'),
    path('listener/', include(listener_router.urls)),
    path('listener/courses/<int:course_id>/tests/<int:test_id>/', views.ListenerTestAPIView.as_view(), name='listener-test'),
    path('', include(router.urls)),

    # аутентификация
    path('auth/register/', views.RegisterView.as_view(), name='register'),
    path('auth/login/', views.LoginView.as_view(), name='login'),
    path('auth/logout/', views.LogoutView.as_view(), name='logout'),
    path('auth/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # восстановление пароля
    path('auth/password-reset/request/', views.PasswordResetRequestView.as_view(), name='password_reset_request'),
    path('auth/password-reset/verify/', views.PasswordResetVerifyView.as_view(), name='password_reset_verify'),
    path('auth/password-reset/confirm/', views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),

     # статистика
    path('statistics/', views.StatisticsView.as_view(), name='statistics'),

    path('payments/create/<int:course_id>/', views.PaymentViewSet.as_view({'post': 'create_payment'}), name='create-payment'),
    path('payments/status/<str:pk>/', views.PaymentViewSet.as_view({'get': 'payment_status'}), name='payment-status'),
    path('payments/confirm/<str:pk>/', views.PaymentViewSet.as_view({'post': 'confirm_payment'}), name='confirm-payment'),
    path('payments/receipt/<str:pk>/', views.PaymentViewSet.as_view({'get': 'get_receipt'}), name='get-receipt'),

     # завершение курса
    path('courses/<int:pk>/completion/', views.CourseViewSet.as_view({'get': 'completion'}), name='course-completion'),
    path('listener/courses/<int:course_id>/tests/<int:test_id>/', 
         views.ListenerTestAPIView.as_view(), name='listener-test'),
    path('listener/test-results/<int:test_result_id>/', 
         views.TestResultDetailView.as_view(), name='test-result-detail'),
    path('listener/courses/<int:course_id>/tests/<int:test_id>/attempts/', 
         views.UserTestAttemptsView.as_view(), name='user-test-attempts'),
    path('listener/results/', 
         views.ListenerResultsView.as_view(), name='listener-results'),
    path('listeners/change-password/', views.ListenerChangePasswordView.as_view(), name='listener-change-password'),
    path('listeners/profile/', views.ListenerProfileView.as_view(), name='listener-profile'),
    path('check-overdue-assignments/', views.CheckOverdueAssignmentsView.as_view(), name='check_overdue_assignments'),
    path('listener/progress/<int:course_id>/assignments/<int:assignment_id>/attempts/', views.ListenerProgressViewSet.as_view({'get': 'assignment_attempts'}), name='listener-assignment-attempts'),
     path('listener/progress/<int:course_id>/assignments/<int:assignment_id>/attempt/<int:attempt_id>/', 
          views.ListenerProgressViewSet.as_view({'put': 'update_attempt'}), 
    name='listener-update-attempt'),

    path('listener/certificates/download/<int:certificate_id>/', 
    views.CertificateDownloadView.as_view(), 
    name='certificate-download'),

    path('courses/<int:course_id>/materials/', views.CourseMaterialsView.as_view(), name='course-materials'),

    path('listener/certificates/', 
         views.CertificateListView.as_view(), 
         name='certificate-list'),
    
    path('listener/certificates/eligibility/<int:course_id>/', 
         views.CertificateEligibilityView.as_view(), 
         name='certificate-eligibility'),
    
    path('listener/certificates/issue/<int:course_id>/', 
         views.CertificateIssueView.as_view(), 
         name='certificate-issue'),
    
    path('listener/certificates/download/<int:certificate_id>/', 
         views.CertificateDownloadView.as_view(), 
         name='certificate-download'),

    path('profile/', views.UserProfileView.as_view(), name='user-profile'),
    path('auth/login/status/', views.api_check_login_status, name='login-status'),
    path('account/deactivate/', views.DeactivateAccountView.as_view(), name='deactivate-account'),
    path('account/deactivate/info/', views.GetDeactivateInfoView.as_view(), name='deactivate-info'),

    # для обновления сертификата
    path('listener/certificates/<int:certificate_id>/regenerate/', 
        views.CertificateViewSet.as_view({'post': 'regenerate_certificate'}), 
        name='certificate-regenerate'),

    # для получения баллов за курс
    path('listener/courses/<int:course_id>/score/', 
        views.ListenerCourseViewSet.as_view({'get': 'course_score'}), 
        name='course-score'),

    path('auth/send-verification-code/', views.SendVerificationCodeView.as_view(), name='send-verification-code'),
    path('auth/verify-code/', views.VerifyCodeView.as_view(), name='verify-code'),
    path('auth/resend-verification-code/', views.ResendVerificationCodeView.as_view(), name='resend-verification-code'),

     # посты и комментарии
    path('posts/by-course/<int:course_id>/', views.CoursePostViewSet.as_view({'get': 'by_course'}), name='posts-by-course'),
    path('posts/create/', views.CoursePostViewSet.as_view({'post': 'create_post'}), name='post-create'),
    path('posts/<int:pk>/', views.CoursePostViewSet.as_view({'get': 'retrieve'}), name='post-detail'),
    path('posts/<int:pk>/edit/', views.CoursePostViewSet.as_view({'put': 'edit_post', 'patch': 'edit_post'}), name='post-edit'),
    path('posts/<int:pk>/delete/', views.CoursePostViewSet.as_view({'delete': 'delete_post'}), name='post-delete'),
    path('posts/<int:pk>/comment/', views.CoursePostViewSet.as_view({'post': 'add_comment'}), name='post-add-comment'),
    path('posts/<int:pk>/delete-comment/<int:comment_id>/', views.CoursePostViewSet.as_view({'post': 'delete_comment'}), name='post-delete-comment'),
        
]