from django import forms
from .models import Template, Student

class TemplateForm(forms.ModelForm):
    class Meta:
        model = Template
        fields = ['name','file','course','template_type']

class StudentForm(forms.ModelForm):
    class Meta:
        model = Student
        fields = ['hallticket','name','course','email','phone','template']

class CSVImportForm(forms.Form):
    file = forms.FileField(help_text="Upload .csv file (utf-8)")


