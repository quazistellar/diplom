from django.contrib import admin

from .models import *

@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    pass

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    pass

@admin.register(CourseCategory)
class CourseCategoryAdmin(admin.ModelAdmin):
    pass

@admin.register(CourseType)
class CourseTypeAdmin(admin.ModelAdmin):
    pass

@admin.register(AssignmentStatus)
class AssignmentStatusAdmin(admin.ModelAdmin):
    pass

@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    pass

@admin.register(CourseTeacher)
class CourseTeacherAdmin(admin.ModelAdmin):
    pass

@admin.register(Lecture)
class LectureAdmin(admin.ModelAdmin):
    pass

@admin.register(PracticalAssignment)
class PracticalAssignmentAdmin(admin.ModelAdmin):
    pass

@admin.register(UserPracticalAssignment)
class UserPracticalAssignmentAdmin(admin.ModelAdmin):
    pass

@admin.register(UserCourse)
class UserCourseAdmin(admin.ModelAdmin):
    pass

@admin.register(Feedback)
class FeedbackAdmin(admin.ModelAdmin):
    pass

@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    pass

@admin.register(AnswerType)
class AnswerTypeAdmin(admin.ModelAdmin):
    pass

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    pass

@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    pass

@admin.register(ChoiceOption)
class ChoiceOptionAdmin(admin.ModelAdmin):
    pass

@admin.register(MatchingPair)
class MatchingPairAdmin(admin.ModelAdmin):
    pass

@admin.register(UserSelectedChoice)
class UserSelectedChoiceAdmin(admin.ModelAdmin):
    pass

@admin.register(UserMatchingAnswer)
class UserMatchingAnswerAdmin(admin.ModelAdmin):
    pass

@admin.register(TestResult)
class TestResultAdmin(admin.ModelAdmin):
    pass

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    pass

@admin.register(AssignmentSubmissionFile)
class AssignmentSubmissionFileAdmin(admin.ModelAdmin):
    pass

@admin.register(TeacherAssignmentFile)
class TeacherAssignmentFileAdmin(admin.ModelAdmin):
    pass

@admin.register(PasswordResetCode)
class PasswordResetCodeAdmin(admin.ModelAdmin):
    pass

@admin.register(ViewCoursePracticalAssignments)
class ViewCoursePracticalAssignmentsAdmin(admin.ModelAdmin):
    pass

@admin.register(ViewCourseLectures)
class ViewCourseLecturesAdmin(admin.ModelAdmin):
    pass

@admin.register(ViewCourseTests)
class ViewCourseTestsAdmin(admin.ModelAdmin):
    pass

@admin.register(ViewAssignmentSubmissions)
class ViewAssignmentSubmissionsAdmin(admin.ModelAdmin):
    pass
