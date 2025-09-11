from django.db import models
from django.utils import timezone

TEMPLATE_TYPES = [('landscape','Landscape'),('portrait','Portrait')]

class Template(models.Model):
    sno = models.AutoField(primary_key=True)
    name = models.CharField(max_length=120)
    file = models.ImageField(upload_to='templates/')
    course = models.CharField(max_length=120)
    template_type = models.CharField(max_length=20, choices=TEMPLATE_TYPES)

    def __str__(self):
        return f"{self.name} ({self.course})"

# In portal/models.py
class Student(models.Model):
    sno = models.AutoField(primary_key=True)
    hallticket = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100)
    course = models.CharField(max_length=50)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True)
    template = models.ForeignKey("Template", on_delete=models.SET_NULL, null=True, blank=True)
    last_certificate = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['sno']

    def __str__(self):
        return f"{self.name} ({self.hallticket})"
  

    class Meta:
        ordering = ['sno']

    def __str__(self):
        return f"{self.name} ({self.hallticket})"


class Certificate(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE)
    template = models.ForeignKey(Template, on_delete=models.SET_NULL, null=True)
    file = models.FileField(upload_to='certificates/')
    created_at = models.DateTimeField(default=timezone.now)

class SendLog(models.Model):
    STATUS = [('SUCCESS','SUCCESS'), ('ERROR','ERROR')]
    student = models.ForeignKey(Student, null=True, blank=True, on_delete=models.SET_NULL)
    recipient_email = models.EmailField()
    status = models.CharField(max_length=10, choices=STATUS)
    error_reason = models.TextField(blank=True)
    sent_at = models.DateTimeField(default=timezone.now)
    resend_count = models.PositiveIntegerField(default=0)
    download_count = models.PositiveIntegerField(default=0)
    attachment = models.FileField(upload_to='sent_attachments/', blank=True)

    def __str__(self):
        return f"{self.recipient_email} - {self.status} - {self.sent_at:%Y-%m-%d %H:%M}"
    


class ReportSuccess(models.Model):
    student_name = models.CharField(max_length=100)
    hallticket = models.CharField(max_length=50)
    course = models.CharField(max_length=100)
    message = models.TextField(default="Processed successfully")
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"✅ {self.student_name} - {self.hallticket}"


class ReportError(models.Model):
    student_name = models.CharField(max_length=100, blank=True, null=True)
    hallticket = models.CharField(max_length=50, blank=True, null=True)
    course = models.CharField(max_length=100, blank=True, null=True)
    error_message = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"❌ {self.student_name or 'Unknown'} - {self.error_message[:30]}"

