from django.urls import path
from . import views

app_name = 'portal'

urlpatterns = [
    path('dashboard/', views.student_dashboard, name='student_dashboard'),
    path('timetable/', views.student_timetable, name='timetable'),
    path('nutrition/', views.nutrition_control, name='nutrition_control'),
    path('switch-context/<int:student_id>/', views.switch_student_context, name='switch_context'),
    path('my-codes/', views.verification_guide, name='my_verification_codes'),
]
