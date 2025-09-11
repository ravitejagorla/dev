from django.urls import path
from . import views

app_name = "portal"

urlpatterns = [
    # Students
    path("students/", views.students, name="students"),
    path("students/import/", views.students_import_csv, name="students_import"),
    path("students/export/", views.students_export_csv, name="students_export"),
    path("students/add/", views.student_create, name="student_add"),
    path("students/<int:sno>/edit/", views.student_edit, name="student_edit"),
    path("students/<int:sno>/delete/", views.student_delete, name="student_delete"),

    # Templates
    path("templates/", views.templates_list, name="templates_list"),
    path("templates/add/", views.template_create, name="template_add"),
    path("templates/<int:sno>/edit/", views.template_edit, name="template_edit"),
    path("templates/<int:sno>/delete/", views.template_delete, name="template_delete"),
    path("templates/import/", views.templates_import_csv, name="templates_import"),  # 👈 FIXED
    path("templates/export/", views.templates_export_csv, name="templates_export"),

    # Reports & logs
    path("reports/", views.reports, name="reports"),
    path("logs/<int:log_id>/resend/", views.log_resend, name="log_resend"),
    path("logs/<int:log_id>/download/", views.log_download, name="log_download"),

    # Sending certificates
    path("students/<int:sno>/send/", views.send_single, name="send_single"),
    path("students/bulk_send/", views.bulk_send, name="bulk_send"),
    path("students/bulk_delete/", views.bulk_delete, name="bulk_delete"),

]
