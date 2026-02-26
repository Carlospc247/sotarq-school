from django.contrib import admin
from django.db import connection
from .models import Student, Guardian, Enrollment

# 🛡️ PROTEÇÃO DE SCHEMA: Só registra se NÃO for o esquema public
if connection.schema_name != 'public':
    @admin.register(Student)
    class StudentAdmin(admin.ModelAdmin):
        list_display = ('full_name', 'registration_number', 'is_active')
        search_fields = ('full_name', 'registration_number')

    @admin.register(Guardian)
    class GuardianAdmin(admin.ModelAdmin):
        list_display = ('full_name', 'phone')

    @admin.register(Enrollment)
    class EnrollmentAdmin(admin.ModelAdmin):
        list_display = ('student', 'status')