from django.contrib import admin
from .models import Student, Template, SendLog, Certificate

@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('sno','hallticket','name','course','email','template')
    search_fields = ('hallticket','name','email','course')

@admin.register(Template)
class TemplateAdmin(admin.ModelAdmin):
    list_display = ('sno','name','course','template_type')

@admin.register(SendLog)
class SendLogAdmin(admin.ModelAdmin):
    list_display = ('id','student','recipient_email','status','sent_at','resend_count','download_count')

@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    list_display = ('id','student','template','created_at')
