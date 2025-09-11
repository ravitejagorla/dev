import csv, io, time
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.db.models import Q
from django.core.mail import EmailMessage
from django.conf import settings
import json

from .models import Student, Template, SendLog, Certificate
from .forms import TemplateForm, StudentForm, CSVImportForm
from .utils import generate_certificate_image, save_certificate

# In portal/views.py
@login_required
def students(request):
    q = request.GET.get('q','').strip()
    
    qs = Student.objects.all().select_related('template').order_by('sno')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(hallticket__icontains=q) | Q(course__icontains=q))
    
    total_count = qs.count()
    
    paginator = Paginator(qs, 5)
    page = request.GET.get('page')
    page_obj = paginator.get_page(page)

    return render(request, 'portal/students.html', {
        'page_obj': page_obj, 
        'q': q, 
        'csv_form': CSVImportForm(),
        'total_count': total_count,
    })

@login_required
def student_create(request):
    if request.method == 'POST':
        form = StudentForm(request.POST)
        if form.is_valid():
            # auto-attach template by course if not chosen
            obj = form.save(commit=False)
            if not obj.template:
                obj.template = Template.objects.filter(course=obj.course).first()
            obj.save()
            messages.success(request, "Student created.")
            return redirect('portal:students')
    else:
        form = StudentForm()
    return render(request, 'portal/student_form.html', {'form': form, 'title': 'Add Student'})

@login_required
def student_edit(request, sno):
    obj = get_object_or_404(Student, sno=sno)
    if request.method == 'POST':
        form = StudentForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            if not obj.template:
                obj.template = Template.objects.filter(course=obj.course).first()
            obj.save()
            messages.success(request, "Student updated.")
            return redirect('portal:students')
    else:
        form = StudentForm(instance=obj)
    return render(request, 'portal/student_form.html', {'form': form, 'title': 'Edit Student'})

@login_required
def student_delete(request, sno):
    get_object_or_404(Student, sno=sno).delete()
    messages.info(request, "Student deleted.")
    return redirect('portal:students')

@login_required
def students_export_csv(request):
    q = request.GET.get('q','').strip()
    qs = Student.objects.all().order_by('sno')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(hallticket__icontains=q) | Q(course__icontains=q))
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="students.csv"'
    writer = csv.writer(response)
    writer.writerow(['sno','hallticket','name','course','email','phone','template'])
    for s in qs:
        writer.writerow([s.sno, s.hallticket, s.name, s.course, s.email, s.phone, s.template.name if s.template else ''])
    return response

# In portal/views.py
@login_required
def students_import_csv(request):
    if request.method != 'POST':
        return redirect('portal:students')

    form = CSVImportForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Invalid CSV file.")
        return redirect('portal:students')

    f = form.cleaned_data['file']
    data = io.TextIOWrapper(f.file, encoding='utf-8')
    reader = csv.DictReader(data)

    created = 0
    # Get the last student number to continue from there
    last_student = Student.objects.order_by('-sno').first()
    next_sno = last_student.sno + 1 if last_student else 1
    
    for row in reader:
        # normalize keys (lowercase & strip spaces)
        row = {k.strip().lower(): (v or "").strip() for k, v in row.items()}

        hallticket = row.get('hallticket')
        name = row.get('name')
        course = row.get('course')
        email = row.get('email') or f"{hallticket}@example.com"  # fallback
        phone = row.get('phone', '')

        if not hallticket:
            continue

        # Check if student already exists
        if Student.objects.filter(hallticket=hallticket).exists():
            continue

        # Create new student with manual sno
        stu = Student.objects.create(
            sno=next_sno,
            hallticket=hallticket,
            name=name,
            course=course,
            email=email,
            phone=phone,
        )
        stu.template = Template.objects.filter(course=course).first()
        stu.save()
        created += 1
        next_sno += 1

    messages.success(request, f"Imported {created} new students.")
    return redirect('portal:students')

import os
def _make_and_attach_certificate(student):
    # choose template (student.template or by course)
    tpl = student.template or Template.objects.filter(course=student.course).first()
    if not tpl:
        raise ValueError("No template found for student's course.")
    today = date.today().strftime("%d-%m-%Y")
    im = generate_certificate_image(tpl.file.path, student.name, student.course, today)
    path = save_certificate(im, settings.MEDIA_ROOT / 'certificates', f"{student.hallticket}_{int(time.time())}")
    student.last_certificate = path.replace(str(settings.MEDIA_ROOT) + os.sep, '')
    student.template = tpl
    student.save()
    cert = Certificate.objects.create(student=student, template=tpl, file=student.last_certificate)
    return cert

@login_required
def send_single(request, sno):
    student = get_object_or_404(Student, sno=sno)
    try:
        cert = _make_and_attach_certificate(student)
        email = EmailMessage(
            subject="Your Certificate",
            body=f"Dear {student.name},\n\nPlease find your certificate attached.\n\nRegards,\nCertifyPro",
            to=[student.email],
        )
        email.attach_file(cert.file.path)
        email.send()
        log = SendLog.objects.create(student=student, recipient_email=student.email, status='SUCCESS', attachment=cert.file)
        messages.success(request, f"Certificate sent to {student.email}")
    except Exception as e:
        SendLog.objects.create(student=student, recipient_email=student.email, status='ERROR', error_reason=str(e))
        messages.error(request, f"Failed to send: {e}")
    return redirect('portal:students')

@login_required
def bulk_send(request):
    # Handle both POST with ids[] and select_all parameter
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=400)
    
    select_all = request.POST.get('select_all', '') == 'true'
    q = request.POST.get('q', '').strip()
    
    if select_all:
        # Get all students matching the search query
        qs = Student.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(hallticket__icontains=q) | Q(course__icontains=q))
        student_ids = list(qs.values_list('sno', flat=True))
    else:
        # Get selected student IDs
        student_ids = request.POST.getlist('ids[]')
    
    done, errors = 0, 0
    for sid in student_ids:
        try:
            s = Student.objects.get(sno=sid)
            cert = _make_and_attach_certificate(s)
            email = EmailMessage(
                subject="Your Certificate",
                body=f"Dear {s.name},\n\nPlease find your certificate attached.\n\nRegards,\nCertifyPro",
                to=[s.email],
            )
            email.attach_file(cert.file.path)
            email.send()
            SendLog.objects.create(student=s, recipient_email=s.email, status='SUCCESS', attachment=cert.file)
            done += 1
        except Exception as e:
            SendLog.objects.create(student=s, recipient_email=s.email, status='ERROR', error_reason=str(e))
            errors += 1
    
    # Clear selection after sending
    if 'studentSelection' in request.session:
        del request.session['studentSelection']
    
    messages.success(request, f"Sent {done} certificates successfully. {errors} failed.")
    return redirect('portal:students')

@login_required
def reports(request):
    q = request.GET.get('q','').strip()
    success_qs = SendLog.objects.filter(status='SUCCESS')
    error_qs = SendLog.objects.filter(status='ERROR')
    if q:
        success_qs = success_qs.filter(Q(recipient_email__icontains=q) | Q(student__name__icontains=q) | Q(student__phone__icontains=q))
        error_qs = error_qs.filter(Q(recipient_email__icontains=q) | Q(student__name__icontains=q) | Q(student__phone__icontains=q))

    succ_page = Paginator(success_qs.order_by('-sent_at'), 10).get_page(request.GET.get('succ_page'))
    err_page  = Paginator(error_qs.order_by('-sent_at'), 10).get_page(request.GET.get('err_page'))

    return render(request, 'portal/reports.html', {'succ_page': succ_page, 'err_page': err_page, 'q': q})

@login_required
def log_resend(request, log_id):
    log = get_object_or_404(SendLog, pk=log_id)
    student = log.student
    try:
        # if we have an attachment, reuse; else regenerate
        attach_path = log.attachment.path if log.attachment else None
        if not attach_path:
            cert = _make_and_attach_certificate(student)
            attach_path = cert.file.path
        email = EmailMessage(
            subject="Your Certificate (Resent)",
            body=f"Dear {student.name},\n\nResending your certificate.\n\nRegards,\nCertifyPro",
            to=[log.recipient_email],
        )
        email.attach_file(attach_path)
        email.send()
        log.resend_count += 1
        log.status = 'SUCCESS'
        if not log.attachment:
            log.attachment.name = attach_path.replace(str(settings.MEDIA_ROOT) + '/', '')
        log.error_reason = ''
        log.save()
        messages.success(request, "Resent successfully.")
    except Exception as e:
        log.status = 'ERROR'
        log.error_reason = str(e)
        log.save()
        messages.error(request, f"Resend failed: {e}")
    return redirect('portal:reports')

@login_required
def log_download(request, log_id):
    log = get_object_or_404(SendLog, pk=log_id)
    if not log.attachment:
        messages.error(request, "No attachment found.")
        return redirect('portal:reports')
    log.download_count += 1
    log.save()
    with open(log.attachment.path, 'rb') as f:
        data = f.read()
    resp = HttpResponse(data, content_type='application/pdf')
    resp['Content-Disposition'] = f'attachment; filename="{log.student.hallticket}_certificate.pdf"'
    return resp

# ----- Templates area -----
@login_required
def templates_list(request):
    q = request.GET.get('q','').strip()
    qs = Template.objects.all().order_by('sno')
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(course__icontains=q))
    paginator = Paginator(qs, 10)
    page_obj = paginator.get_page(request.GET.get('page'))

    return render(request, 'portal/templates.html', {
        'page_obj': page_obj,
        'q': q,
        'form': TemplateForm(),   # 🔽 add this for modal
    })

@login_required
def template_create(request):
    if request.method == 'POST':
        form = TemplateForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "Template added.")
            return redirect('portal:templates_list')
    else:
        form = TemplateForm()
    return render(request, 'portal/template_form.html', {'form': form, 'title': 'Add Template'})

@login_required
def template_edit(request, sno):
    obj = get_object_or_404(Template, sno=sno)
    if request.method == 'POST':
        form = TemplateForm(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            form.save()
            messages.success(request, "Template updated.")
            return redirect('portal:templates_list')
    else:
        form = TemplateForm(instance=obj)
    return render(request, 'portal/template_form.html', {'form': form, 'title': 'Edit Template'})

@login_required
def template_delete(request, sno):
    get_object_or_404(Template, sno=sno).delete()
    messages.info(request, "Template deleted.")
    return redirect('portal:templates_list')

@login_required
def templates_export_csv(request):
    qs = Template.objects.all().order_by('sno')
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="templates.csv"'
    writer = csv.writer(response)
    writer.writerow(['sno','name','course','template_type','file'])
    for t in qs:
        writer.writerow([t.sno, t.name, t.course, t.template_type, t.file.name])
    return response

@login_required
def templates_import_csv(request):
    if request.method != 'POST':
        return redirect('portal:templates_list')
    form = CSVImportForm(request.POST, request.FILES)
    if not form.is_valid():
        messages.error(request, "Invalid CSV file.")
        return redirect('portal:templates_list')
    data = io.TextIOWrapper(form.cleaned_data['file'].file, encoding='utf-8')
    reader = csv.DictReader(data)
    created = 0
    for row in reader:
        name = row.get('name','').strip()
        course = row.get('course','').strip()
        ttype = row.get('template_type','landscape').strip()
        # file column ignored on CSV import (images must be uploaded via form)
        if name and course:
            Template.objects.get_or_create(name=name, course=course, defaults={'template_type': ttype, 'file': None})
            created += 1
    messages.success(request, f"Imported {created} templates (upload images individually).")
    return redirect('portal:templates_list')


@login_required
def bulk_delete(request):
    if request.method != 'POST':
        return JsonResponse({'ok': False, 'error': 'POST required'}, status=400)
    
    select_all = request.POST.get('select_all', '') == 'true'
    q = request.POST.get('q', '').strip()
    
    if select_all:
        # Get all students matching the search query
        qs = Student.objects.all()
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(email__icontains=q) | Q(hallticket__icontains=q) | Q(course__icontains=q))
        deleted_count = qs.count()
        qs.delete()
    else:
        # Get selected student IDs
        student_ids = request.POST.getlist('ids[]')
        qs = Student.objects.filter(sno__in=student_ids)
        deleted_count = qs.count()
        qs.delete()
    
    # Clear selection after deletion
    if 'studentSelection' in request.session:
        del request.session['studentSelection']
    
    messages.success(request, f"Deleted {deleted_count} students successfully.")
    return redirect('portal:students')